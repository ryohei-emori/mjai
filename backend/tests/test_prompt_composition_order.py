"""
Backend half of the guarantee behind the prompt editor's assembly disclosure.

The settings dialog shows the operator an ordered list of the pieces that make
up a prompt (`frontend/src/lib/promptComposition.ts`), so they can tell where the
SOURCE / EXEMPLAR / TARGET text they paste lands relative to the rules they are
editing. That is only trustworthy if `build_messages` really assembles in that
order, so this pins it. The frontend half — the same order through the offline
builder — is in
`frontend/src/lib/webllm/__tests__/promptComposition.test.ts`.

Keep the step ids below in sync with `PROMPT_COMPOSITION_STEPS`; the ids are the
contract between the two test suites and the UI.
"""

from app.llm.prompts import OUTPUT_CONTRACT, build_messages

OVERRIDE = "OPERATOR_RULES_MARKER"
SOURCE = "SOURCE_MARKER"
EXEMPLAR = "EXEMPLAR_MARKER"
TARGET = "TARGET_MARKER"

# (step id, a distinctive fragment locating that step in the flattened prompt).
COMPOSITION_MARKERS = [
    ("body", OVERRIDE),
    ("exemplar-rules", "【六】模範回答訳文"),
    ("contract", OUTPUT_CONTRACT),
    ("few-shot", "输出：{\"suggestions\""),
    ("source", SOURCE),
    ("exemplar", EXEMPLAR),
    ("target", TARGET),
]

CONDITIONAL_STEPS = {"exemplar-rules", "exemplar"}


def _flatten(messages: list[dict]) -> str:
    """The prompt as the model receives it: messages in order, concatenated."""
    return "\n".join(m["content"] for m in messages)


def test_pieces_appear_in_the_order_the_editor_discloses():
    prompt = _flatten(
        build_messages(
            SOURCE,
            TARGET,
            exemplar_translation=EXEMPLAR,
            system_prompt_override=OVERRIDE,
        )
    )

    previous_offset = -1
    previous_step = "(start)"
    for step_id, marker in COMPOSITION_MARKERS:
        offset = prompt.find(marker)
        assert offset != -1, f"step {step_id!r} is not in the assembled prompt"
        assert offset > previous_offset, (
            f"step {step_id!r} is assembled before {previous_step!r}, but the "
            "prompt editor tells the operator it comes after"
        )
        previous_offset = offset
        previous_step = step_id


def test_only_the_conditional_pieces_are_withheld_without_an_exemplar():
    prompt = _flatten(
        build_messages(SOURCE, TARGET, system_prompt_override=OVERRIDE)
    )

    for step_id, marker in COMPOSITION_MARKERS:
        if step_id in CONDITIONAL_STEPS:
            assert marker not in prompt, (
                f"step {step_id!r} is disclosed as exemplar-only but was sent "
                "without one"
            )
        else:
            assert marker in prompt, f"step {step_id!r} is missing"


def test_the_contract_survives_an_override():
    """An operator edit may lower quality; it may not break parsing."""
    prompt = _flatten(
        build_messages(SOURCE, TARGET, system_prompt_override="只指出助词错误。")
    )

    assert "只指出助词错误。" in prompt
    assert OUTPUT_CONTRACT in prompt
