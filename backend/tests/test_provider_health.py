"""
Tests for shared credential availability (`backend/app/llm/provider_health.py`)
and for the chain routing around what it records.

The behavior under test is the one the in-process cooldown could not provide:
knowledge that survives the request that learned it. Vercel gives each request a
fresh process, so a user whose Gemini quota was exhausted paid one 429 per pooled
key on every generation — against the quota that was already exhausted — before
Groq was asked. These tests therefore assert on *which providers were called*,
not only on what the helpers return.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.llm import provider_health
from app.llm.cloudflare_provider import CF_MIN_SLICE_S
from app.llm.gemini_provider import ALLOWED_GEMINI_MODELS, GeminiRateLimitError
from app.llm.groq_provider import ALLOWED_GROQ_MODELS, GROQ_MIN_SLICE_S
from app.llm.key_pool import (
    DEFAULT_COOLDOWN_SECONDS,
    acquire_gemini,
    load_gemini_credentials,
    mark_cooldown,
    pool_availability,
    release_soonest_cooldown,
)
from app.llm.provider_health import (
    MAX_COOLDOWN_S,
    clamp_cooldown_seconds,
    credential_fingerprint,
    observe_refusal,
    parse_duration_hint,
    parse_retry_after,
    seed_cooldowns,
)
from app.llm.suggestions import (
    SUGGESTIONS_WALL_CLOCK_S,
    _later_provider_reserve,
    _plan_providers,
    generate_suggestions,
)

from test_llm_suggestions import VALID_LLM_RESPONSE, FakeClock


def health_row(provider, fingerprint, *, in_seconds=120.0, model="", reason="HTTP 429"):
    return {
        "provider": provider,
        "model": model,
        "credentialFingerprint": fingerprint,
        "recoverAt": datetime.now(timezone.utc) + timedelta(seconds=in_seconds),
        "reason": reason,
    }


class TestFingerprint:
    def test_identifies_a_credential_without_containing_it(self):
        secret = "AIzaSy-super-secret-key"
        fingerprint = credential_fingerprint(f"gemini:{secret}")
        assert secret not in fingerprint
        assert "gemini" not in fingerprint
        assert len(fingerprint) == 16

    def test_is_stable_and_distinguishes_credentials(self):
        a = credential_fingerprint("gemini:key-a")
        assert a == credential_fingerprint("gemini:key-a")
        assert a != credential_fingerprint("gemini:key-b")


class TestRetryHintParsing:
    """A hint is only useful if the provider's actual formats parse."""

    def test_retry_after_seconds(self):
        assert parse_retry_after("30") == 30.0

    def test_retry_after_http_date(self):
        soon = datetime.now(timezone.utc) + timedelta(seconds=45)
        stamp = soon.strftime("%a, %d %b %Y %H:%M:%S GMT")
        parsed = parse_retry_after(stamp)
        assert parsed is not None
        assert 30 <= parsed <= 60

    def test_retry_after_garbage_is_no_hint(self):
        assert parse_retry_after("soon-ish") is None
        assert parse_retry_after("") is None
        assert parse_retry_after(None) is None

    def test_groq_compact_duration_forms(self):
        assert parse_duration_hint("7.66s") == pytest.approx(7.66)
        assert parse_duration_hint("2m59.56s") == pytest.approx(179.56)
        assert parse_duration_hint("180ms") == pytest.approx(0.18)
        assert parse_duration_hint("1h30m") == pytest.approx(5400.0)

    def test_bare_number_is_seconds(self):
        assert parse_duration_hint("12") == 12.0

    def test_unfamiliar_form_is_no_hint(self):
        assert parse_duration_hint("whenever") is None


class TestCooldownClamp:
    def test_short_hint_is_honored(self):
        assert clamp_cooldown_seconds(8.0) == 8.0

    def test_long_hint_is_capped(self):
        # A daily-quota hint would otherwise withhold the provider until
        # tomorrow, including when the hint is wrong or the key was replaced.
        assert clamp_cooldown_seconds(24 * 3600) == MAX_COOLDOWN_S

    def test_missing_hint_falls_back_to_the_default(self):
        assert clamp_cooldown_seconds(None) == DEFAULT_COOLDOWN_SECONDS
        assert clamp_cooldown_seconds(0) == DEFAULT_COOLDOWN_SECONDS


class TestSeeding:
    def test_a_recorded_refusal_prevents_selecting_that_credential(
        self, monkeypatch
    ):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a,key-b")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        creds = load_gemini_credentials()

        seeded = seed_cooldowns(
            [health_row("gemini", credential_fingerprint(creds[0].id), model="m1")]
        )

        assert seeded == 1
        picked = {acquire_gemini(cooldown_scope="m1").id for _ in range(4)}
        assert picked == {creds[1].id}

    def test_an_expired_record_does_not_withhold_anything(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cred = load_gemini_credentials()[0]

        seeded = seed_cooldowns(
            [health_row("gemini", credential_fingerprint(cred.id), in_seconds=-5)]
        )

        assert seeded == 0
        assert acquire_gemini() is not None

    def test_a_refusal_is_scoped_to_the_model_it_applied_to(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cred = load_gemini_credentials()[0]

        seed_cooldowns(
            [
                health_row(
                    "gemini",
                    credential_fingerprint(cred.id),
                    model="gemini-3.7-flash",
                )
            ]
        )

        assert acquire_gemini(cooldown_scope="gemini-3.7-flash") is None
        assert acquire_gemini(cooldown_scope="gemini-3.6-flash") is not None

    def test_a_row_for_a_key_this_deployment_no_longer_has_is_ignored(
        self, monkeypatch
    ):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        assert seed_cooldowns([health_row("gemini", "0123456789abcdef")]) == 0
        assert acquire_gemini() is not None

    def test_a_seeded_cooldown_is_capped_like_a_fresh_one(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cred = load_gemini_credentials()[0]

        seed_cooldowns(
            [
                health_row(
                    "gemini",
                    credential_fingerprint(cred.id),
                    in_seconds=24 * 3600,
                )
            ]
        )

        availability = pool_availability([cred])
        assert availability.recover_in_s <= MAX_COOLDOWN_S

    def test_seeded_state_is_marked_as_learned_earlier(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cred = load_gemini_credentials()[0]

        seed_cooldowns([health_row("gemini", credential_fingerprint(cred.id))])

        assert pool_availability([cred]).carried_over is True
        mark_cooldown(cred.id, 60)
        assert pool_availability([cred]).carried_over is False


class TestPoolAvailability:
    def test_an_unconfigured_pool_is_not_reported_as_cooled(self):
        state = pool_availability([])
        assert state.configured is False
        assert state.all_cooled is False

    def test_one_free_scope_keeps_the_pool_usable(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cred = load_gemini_credentials()[0]
        mark_cooldown(cred.id, 60, scope="m1")

        # A 429 on one rotation model is not the provider's answer.
        assert pool_availability([cred], ["m1", "m2"]).all_cooled is False

    def test_every_scope_cooled_reports_the_soonest_recovery(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cred = load_gemini_credentials()[0]
        mark_cooldown(cred.id, 300, scope="m1")
        mark_cooldown(cred.id, 30, scope="m2")

        state = pool_availability([cred], ["m1", "m2"])
        assert state.all_cooled is True
        assert 25 <= state.recover_in_s <= 30

    def test_releasing_frees_the_soonest_and_only_the_soonest(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a,key-b")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        first, second = load_gemini_credentials()
        mark_cooldown(first.id, 300)
        mark_cooldown(second.id, 20)

        released = release_soonest_cooldown([first, second])

        assert released == second.id
        assert pool_availability([first]).all_cooled is True
        assert pool_availability([second]).all_cooled is False

    def test_releasing_nothing_cooled_is_a_no_op(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert release_soonest_cooldown(load_gemini_credentials()) is None


class TestChainPlan:
    """Which providers a pass will call, before it calls any of them."""

    def _cool_all(self, creds, scopes, seconds=120.0):
        for cred in creds:
            for scope in scopes:
                mark_cooldown(cred.id, seconds, scope=scope, carried_over=True)

    def test_an_exhausted_primary_is_planned_out(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a")
        monkeypatch.setenv("GROQ_API_KEY", "groq-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        self._cool_all(load_gemini_credentials(), ALLOWED_GEMINI_MODELS)

        plan = _plan_providers()

        assert plan["gemini"].usable is False
        assert "already in cooldown" in plan["gemini"].unavailable_reason
        assert "expected usable in" in plan["gemini"].unavailable_reason
        assert plan["groq"].usable is True

    def test_an_unset_credential_is_not_described_as_rate_limited(
        self, monkeypatch
    ):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "groq-a")

        plan = _plan_providers()

        assert plan["gemini"].configured is False
        assert plan["gemini"].unavailable_reason is None

    def test_everything_cooled_still_leaves_one_provider_to_call(
        self, monkeypatch
    ):
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a")
        monkeypatch.setenv("GROQ_API_KEY", "groq-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        # Groq recovers sooner, so it is the plausible one to spend the attempt on.
        self._cool_all(load_gemini_credentials(), ALLOWED_GEMINI_MODELS, 600.0)
        from app.llm.key_pool import load_groq_credentials

        self._cool_all(load_groq_credentials(), ALLOWED_GROQ_MODELS, 20.0)

        plan = _plan_providers()

        assert plan["groq"].usable is True
        assert plan["gemini"].usable is False

    def test_a_planned_out_provider_holds_back_no_time_for_itself(
        self, monkeypatch
    ):
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a")
        monkeypatch.setenv("GROQ_API_KEY", "groq-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_IDS", raising=False)
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        from app.llm.key_pool import load_groq_credentials

        self._cool_all(load_groq_credentials(), ALLOWED_GROQ_MODELS)

        plan = _plan_providers()

        # Gemini would otherwise give up GROQ_MIN_SLICE_S to a call that is not
        # going to happen, shrinking the only attempt this request will make.
        assert _later_provider_reserve(after="gemini", plan=plan) == 0.0
        assert _later_provider_reserve(after="gemini") == GROQ_MIN_SLICE_S


@pytest.mark.asyncio
class TestChainRoutesAroundRecordedLimits:
    def _env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a")
        monkeypatch.setenv("GROQ_API_KEY", "groq-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_IDS", raising=False)

    async def test_a_recorded_limit_means_the_primary_is_not_called_at_all(
        self, monkeypatch
    ):
        self._env(monkeypatch)
        cred = load_gemini_credentials()[0]
        seed_cooldowns(
            [
                health_row("gemini", credential_fingerprint(cred.id), model=model)
                for model in ALLOWED_GEMINI_MODELS
            ]
        )

        with patch(
            "app.llm.suggestions.call_gemini_with_rotation", new_callable=AsyncMock
        ) as gemini:
            with patch(
                "app.llm.suggestions.call_groq_with_rotation",
                new=AsyncMock(return_value=VALID_LLM_RESPONSE),
            ):
                result = await generate_suggestions("原文", "訳文")

        gemini.assert_not_called()
        assert len(result["suggestions"]) == 1

    async def test_preference_order_is_kept_when_both_are_usable(
        self, monkeypatch
    ):
        self._env(monkeypatch)

        with patch(
            "app.llm.suggestions.call_gemini_with_rotation",
            new=AsyncMock(return_value=VALID_LLM_RESPONSE),
        ):
            with patch(
                "app.llm.suggestions.call_groq_with_rotation", new_callable=AsyncMock
            ) as groq:
                result = await generate_suggestions("原文", "訳文")

        # Groq is faster, and is still not promoted: order encodes critique
        # quality, and availability must not silently trade it for latency.
        groq.assert_not_called()
        assert result["llmProvider"] == "gemini"

    async def test_a_partially_cooled_pool_is_still_called(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a,gem-b")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_API_KEYS", raising=False)
        first = load_gemini_credentials()[0]
        seed_cooldowns(
            [
                health_row("gemini", credential_fingerprint(first.id), model=model)
                for model in ALLOWED_GEMINI_MODELS
            ]
        )

        with patch(
            "app.llm.suggestions.call_gemini_with_rotation",
            new=AsyncMock(return_value=VALID_LLM_RESPONSE),
        ) as gemini:
            await generate_suggestions("原文", "訳文")

        gemini.assert_called_once()

    async def test_everything_recorded_unavailable_still_makes_one_attempt(
        self, monkeypatch
    ):
        """Our own cache must never be the sole reason nothing was tried."""
        self._env(monkeypatch)
        from app.llm.key_pool import load_groq_credentials

        rows = [
            health_row(
                "gemini",
                credential_fingerprint(load_gemini_credentials()[0].id),
                model=model,
                in_seconds=600,
            )
            for model in ALLOWED_GEMINI_MODELS
        ] + [
            health_row(
                "groq",
                credential_fingerprint(load_groq_credentials()[0].id),
                model=model,
                in_seconds=30,
            )
            for model in ALLOWED_GROQ_MODELS
        ]
        seed_cooldowns(rows)

        with patch(
            "app.llm.suggestions.call_groq_with_rotation",
            new=AsyncMock(return_value=VALID_LLM_RESPONSE),
        ) as groq:
            result = await generate_suggestions("原文", "訳文")

        groq.assert_called_once()
        assert len(result["suggestions"]) == 1

    async def test_the_breakdown_separates_a_learned_limit_from_an_unset_key(
        self, monkeypatch
    ):
        from app.llm.groq_provider import GroqRateLimitError
        from app.llm.suggestions import SuggestionsError

        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a")
        monkeypatch.setenv("GROQ_API_KEY", "groq-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_IDS", raising=False)
        cred = load_gemini_credentials()[0]
        seed_cooldowns(
            [
                health_row("gemini", credential_fingerprint(cred.id), model=model)
                for model in ALLOWED_GEMINI_MODELS
            ]
        )

        with patch(
            "app.llm.suggestions.call_groq_with_rotation",
            new=AsyncMock(side_effect=GroqRateLimitError("boom", status_code=429)),
        ):
            with pytest.raises(SuggestionsError) as exc_info:
                await generate_suggestions("原文", "訳文")

        error = exc_info.value
        assert "already in cooldown" in (error.gemini_error or "")
        assert "not configured" in (error.cf_error or "")


class TestObservationsAreRecordedForLaterRequests:
    def test_a_refusal_is_buffered_with_an_absolute_recovery_instant(self):
        observe_refusal("groq", "groq:key-a", 45.0, model="m1", reason="HTTP 429")

        records = provider_health._record_tuples(provider_health._pending)
        assert len(records) == 1
        provider, model, fingerprint, recover_at, reason = records[0]
        assert (provider, model, reason) == ("groq", "m1", "HTTP 429")
        assert fingerprint == credential_fingerprint("groq:key-a")
        assert 40 <= (recover_at - datetime.now(timezone.utc)).total_seconds() <= 46

    def test_the_buffer_cannot_grow_without_bound(self):
        for i in range(provider_health.MAX_PENDING_OBSERVATIONS + 10):
            observe_refusal("groq", f"groq:key-{i}", 30.0)
        assert (
            len(provider_health._pending)
            == provider_health.MAX_PENDING_OBSERVATIONS
        )

    def test_nothing_observed_means_no_write_at_all(self):
        with patch(
            "app.db_helper.upsert_provider_health", new_callable=AsyncMock
        ) as write:
            written = asyncio.run(provider_health.flush_observations(None))
        write.assert_not_called()
        assert written == 0

    def test_observations_are_written_once_for_the_whole_request(self):
        observe_refusal("gemini", "gemini:key-a", 30.0, model="m1")
        observe_refusal("gemini", "gemini:key-b", 30.0, model="m1")

        with patch(
            "app.db_helper.upsert_provider_health", new_callable=AsyncMock
        ) as write:
            written = asyncio.run(provider_health.flush_observations(None))

        write.assert_called_once()
        assert len(write.call_args.args[0]) == 2
        assert written == 2
        assert provider_health._pending == []

    def test_a_nearly_spent_budget_skips_the_write(self):
        observe_refusal("gemini", "gemini:key-a", 30.0, model="m1")
        clock = FakeClock()

        with patch("time.monotonic", clock):
            with patch(
                "app.db_helper.upsert_provider_health", new_callable=AsyncMock
            ) as write:
                written = asyncio.run(
                    provider_health.flush_observations(clock() + 1.0)
                )

        write.assert_not_called()
        assert written == 0
        # Kept, not dropped: a warm process can still store them next time, and a
        # recovery instant already in the past is filtered out on read.
        assert len(provider_health._pending) == 1

    def test_a_failing_write_is_not_a_failing_request(self):
        observe_refusal("gemini", "gemini:key-a", 30.0, model="m1")

        with patch(
            "app.db_helper.upsert_provider_health",
            new=AsyncMock(side_effect=RuntimeError("no such table")),
        ):
            assert asyncio.run(provider_health.flush_observations(None)) == 0

    def test_a_slow_write_does_not_hang_the_request(self, monkeypatch):
        observe_refusal("gemini", "gemini:key-a", 30.0, model="m1")
        monkeypatch.setattr(provider_health, "FLUSH_TIMEOUT_S", 0.01)

        async def never(_records):
            await asyncio.sleep(10)

        with patch("app.db_helper.upsert_provider_health", new=never):
            assert asyncio.run(provider_health.flush_observations(None)) == 0


class TestSharedStateReadIsCheapAndSafe:
    def test_prompt_and_availability_share_one_connection(self):
        """The generation path must not pay a second connect for availability."""
        from app import db_helper

        opened = []

        class _Conn:
            async def fetchrow(self, *_a, **_k):
                return None

            async def fetch(self, *_a, **_k):
                return []

        class _Ctx:
            async def __aenter__(self):
                opened.append(1)
                return _Conn()

            async def __aexit__(self, *exc):
                return False

        with patch.object(db_helper, "get_db", lambda: _Ctx()):
            asyncio.run(db_helper.fetch_setting_and_provider_health("k"))

        assert len(opened) == 1

    def test_a_missing_health_table_still_returns_the_prompt(self):
        import asyncpg

        from app import db_helper

        class _Conn:
            async def fetchrow(self, *_a, **_k):
                return {"settingValue": "规则正文"}

            async def fetch(self, *_a, **_k):
                raise asyncpg.exceptions.UndefinedTableError("no provider_health")

        class _Ctx:
            async def __aenter__(self):
                return _Conn()

            async def __aexit__(self, *exc):
                return False

        with patch.object(db_helper, "get_db", lambda: _Ctx()):
            setting, health = asyncio.run(
                db_helper.fetch_setting_and_provider_health("k")
            )

        assert setting["settingValue"] == "规则正文"
        assert health == []

    def test_a_missing_settings_table_still_returns_availability(self):
        import asyncpg

        from app import db_helper

        class _Conn:
            async def fetchrow(self, *_a, **_k):
                raise asyncpg.exceptions.UndefinedTableError("no app_settings")

            async def fetch(self, *_a, **_k):
                return [{"provider": "groq"}]

        class _Ctx:
            async def __aenter__(self):
                return _Conn()

            async def __aexit__(self, *exc):
                return False

        with patch.object(db_helper, "get_db", lambda: _Ctx()):
            setting, health = asyncio.run(
                db_helper.fetch_setting_and_provider_health("k")
            )

        assert setting is None
        assert health == [{"provider": "groq"}]

    def test_an_unreachable_database_degrades_to_defaults(self):
        from app import db_helper

        async def boom(_key):
            raise RuntimeError("connection refused")

        with patch.object(db_helper, "fetch_setting_and_provider_health", boom):
            assert asyncio.run(provider_health.load_shared_state("k")) == (None, [])

    def test_generation_still_works_with_no_shared_knowledge(self, monkeypatch):
        """The whole feature absent must equal the behavior before it existed."""
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_API_KEYS", raising=False)

        assert seed_cooldowns([]) == 0
        with patch(
            "app.llm.suggestions.call_gemini_with_rotation",
            new=AsyncMock(return_value=VALID_LLM_RESPONSE),
        ):
            result = asyncio.run(generate_suggestions("原文", "訳文"))
        assert len(result["suggestions"]) == 1


class TestProviderRecordsWhatItWasTold:
    @pytest.mark.asyncio
    async def test_a_gemini_429_records_the_hint_it_carried(self, monkeypatch):
        from app.llm import gemini_provider

        monkeypatch.setenv("GEMINI_API_KEY", "gem-a")
        monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
        monkeypatch.setenv("GEMINI_MODEL", "gemini-3.7-flash")

        async def refuse(api_key, messages, model, timeout):
            raise GeminiRateLimitError("429", status_code=429, retry_after=12.0)

        with patch.object(gemini_provider, "_call_gemini_once", new=refuse):
            with pytest.raises(GeminiRateLimitError):
                await gemini_provider.call_gemini([{"role": "user", "content": "x"}])

        records = provider_health._record_tuples(provider_health._pending)
        assert len(records) == 1
        provider, model, _fingerprint, recover_at, reason = records[0]
        assert (provider, model, reason) == ("gemini", "gemini-3.7-flash", "HTTP 429")
        remaining = (recover_at - datetime.now(timezone.utc)).total_seconds()
        assert 8 <= remaining <= 13
        # And the same duration applies in-process, so this request's next
        # attempt agrees with what later requests will read.
        cred = load_gemini_credentials()[0]
        state = pool_availability([cred], ["gemini-3.7-flash"])
        assert state.all_cooled is True
        assert state.recover_in_s <= 12.0

    def test_a_groq_reset_header_becomes_the_cooldown(self):
        from app.llm.groq_provider import _retry_hint_seconds

        class _Resp:
            headers = {"x-ratelimit-reset-requests": "2m59.56s"}

        assert _retry_hint_seconds(_Resp()) == pytest.approx(179.56)

    def test_gemini_reads_retry_info_out_of_the_error_body(self):
        from app.llm.gemini_provider import _retry_hint_seconds

        class _Resp:
            headers = {}

            def json(self):
                return {
                    "error": {
                        "code": 429,
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": "37s",
                            }
                        ],
                    }
                }

        assert _retry_hint_seconds(_Resp()) == pytest.approx(37.0)

    def test_an_unreadable_body_is_simply_no_hint(self):
        from app.llm.gemini_provider import _retry_hint_seconds

        class _Resp:
            headers = {}

            def json(self):
                raise ValueError("not json")

        assert _retry_hint_seconds(_Resp()) is None


class TestEndpointWiring:
    """
    The endpoint is where the feature is switched on: if it does not read the
    snapshot, seed from it, and write back, everything above is inert.
    """

    @pytest.fixture
    def client(self, monkeypatch):
        import time as time_module

        import jwt
        from fastapi.testclient import TestClient

        secret = "test-secret-value"
        email = "owner@example.com"
        monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
        monkeypatch.setenv("ALLOWED_USER_EMAIL", email)
        monkeypatch.setenv("ALLOWED_USER_EMAILS", email)
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "groq-a")
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_IDS", raising=False)

        now = int(time_module.time())
        token = jwt.encode(
            {"email": email, "aud": "authenticated", "iat": now, "exp": now + 3600},
            secret,
            algorithm="HS256",
        )
        from app.main import app

        return TestClient(app), {"Authorization": f"Bearer {token}"}

    def test_a_recorded_limit_reaches_the_chain_and_new_ones_are_written(
        self, client
    ):
        test_client, headers = client
        gemini_cred = load_gemini_credentials()[0]
        rows = [
            health_row(
                "gemini", credential_fingerprint(gemini_cred.id), model=model
            )
            for model in ALLOWED_GEMINI_MODELS
        ]

        async def shared_read(_key):
            return None, rows

        async def groq_refuses_then_the_pool_is_spent(messages, **_kwargs):
            from app.llm.groq_provider import GroqRateLimitError

            observe_refusal("groq", "groq:groq-a", 30.0, model="m1", reason="HTTP 429")
            raise GroqRateLimitError("429", status_code=429)

        with patch(
            "app.db_helper.fetch_setting_and_provider_health", new=shared_read
        ):
            with patch(
                "app.llm.suggestions.call_gemini_with_rotation",
                new_callable=AsyncMock,
            ) as gemini:
                with patch(
                    "app.llm.suggestions.call_groq_with_rotation",
                    new=groq_refuses_then_the_pool_is_spent,
                ):
                    with patch(
                        "app.db_helper.upsert_provider_health", new_callable=AsyncMock
                    ) as write:
                        response = test_client.post(
                            "/suggestions",
                            headers=headers,
                            json={"originalText": "原文", "targetText": "訳文"},
                        )

        # Gemini was recorded as exhausted, so this request did not spend a call
        # rediscovering that; Groq's fresh refusal is stored for the next one.
        gemini.assert_not_called()
        assert response.status_code == 503
        assert "already in cooldown" in (response.json()["gemini_error"] or "")
        write.assert_called_once()
        assert write.call_args.args[0][0][0] == "groq"

    def test_a_healthy_generation_writes_nothing(self, client):
        test_client, headers = client

        async def shared_read(_key):
            return None, []

        with patch(
            "app.db_helper.fetch_setting_and_provider_health", new=shared_read
        ):
            with patch(
                "app.llm.suggestions.call_gemini_with_rotation",
                new=AsyncMock(return_value=VALID_LLM_RESPONSE),
            ):
                with patch(
                    "app.db_helper.upsert_provider_health", new_callable=AsyncMock
                ) as write:
                    response = test_client.post(
                        "/suggestions",
                        headers=headers,
                        json={"originalText": "原文", "targetText": "訳文"},
                    )

        assert response.status_code == 200
        write.assert_not_called()

    def test_an_unreadable_store_does_not_stop_generation(self, client):
        test_client, headers = client

        async def boom(_key):
            raise RuntimeError("connection refused")

        with patch("app.db_helper.fetch_setting_and_provider_health", new=boom):
            with patch(
                "app.llm.suggestions.call_gemini_with_rotation",
                new=AsyncMock(return_value=VALID_LLM_RESPONSE),
            ):
                response = test_client.post(
                    "/suggestions",
                    headers=headers,
                    json={"originalText": "原文", "targetText": "訳文"},
                )

        assert response.status_code == 200
        assert len(response.json()["suggestions"]) == 1


class TestBudgetInteraction:
    """Availability must not disturb the wall-clock guarantees already in place."""

    def test_the_reserve_still_covers_a_usable_later_provider(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "groq-a")
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc")
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        plan = _plan_providers()

        assert _later_provider_reserve(after="gemini", plan=plan) == (
            GROQ_MIN_SLICE_S + CF_MIN_SLICE_S
        )
        assert _later_provider_reserve(after="cloudflare", plan=plan) == 0.0

    def test_skipping_the_primary_leaves_the_secondary_the_whole_budget(
        self, monkeypatch
    ):
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a")
        monkeypatch.setenv("GROQ_API_KEY", "groq-a")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_IDS", raising=False)
        cred = load_gemini_credentials()[0]
        seed_cooldowns(
            [
                health_row("gemini", credential_fingerprint(cred.id), model=model)
                for model in ALLOWED_GEMINI_MODELS
            ]
        )
        clock = FakeClock()
        granted = []

        async def groq(messages, deadline_monotonic=None):
            granted.append(deadline_monotonic)
            return VALID_LLM_RESPONSE

        with patch("app.llm.suggestions.call_groq_with_rotation", new=groq):
            with patch("time.monotonic", clock):
                deadline = clock() + SUGGESTIONS_WALL_CLOCK_S
                asyncio.run(
                    generate_suggestions(
                        "原文", "訳文", deadline_monotonic=deadline
                    )
                )

        # Nothing was spent on the skipped primary, and Groq's phase is the whole
        # request deadline because no configured provider follows it.
        assert granted == [deadline]
