# MJAI — AI-Assisted Japanese Text Correction

**Turning a 6-minute manual proofreading task into a 90-second AI-assisted workflow — without losing the human in the loop.**

MJAI is a full-stack web application that helps professionals correct and polish Japanese text faster, using client-side WebLLM to generate ranked correction proposals that a human reviewer selects, refines, and approves.

---

## The Problem

Manually rewriting text into natural, polite Japanese is slow, repetitive, and expensive to scale. A single correction session — reading the original, comparing it to the target style, and writing out the fix — routinely takes a skilled reviewer several minutes. That ceiling caps how many sessions a business can realistically process per day, and therefore caps revenue.

## The Solution

MJAI inserts an AI proposal step in front of the human reviewer:

1. **Session & history tracking** — every piece of work is organized into sessions, each containing a history of correction tasks.
2. **AI-generated proposals** — for each task, an in-browser WebLLM model analyzes the original vs. target text and returns multiple ranked correction proposals with reasoning.
3. **Human-in-the-loop review** — the reviewer picks, edits, or overrides proposals rather than writing corrections from scratch.
4. **Full auditability** — every session, history entry, and proposal (adopted or not) is persisted, so past work can be reconstructed and reviewed at any time.

The result: the reviewer's job shifts from *drafting* corrections to *judging* AI-drafted ones — a much faster task.

---

## Business Impact: Productivity-Driven Revenue Growth

This isn't a cost-cutting story — it's a throughput story. The same reviewer, doing a modestly longer shift, can process **5× the volume** at the same price per session — worth **+CNY 62,400/year** (**+CNY 5,195/month**) in additional revenue for only a 25% increase in working hours. All figures below are in Chinese Yuan (CNY / 元).

| Metric | AS-IS (manual) | TO-BE (AI-assisted) |
|---|---|---|
| Sessions processed | 20 | 100 |
| Price per session | CNY 5 | CNY 5 |
| Revenue | CNY 100 | CNY 500 |
| Time per session | 6 min | 1.5 min |
| Total time | 2 hours | 2.5 hours |

Scaled up (3 sessions-batches/week, ~4.33 weeks/month, 52 weeks/year) — monthly and annual are the headline numbers, weekly shown for reference:

| Period | AS-IS revenue | TO-BE revenue | Δ Revenue | AS-IS time | TO-BE time | Δ Time |
|---|---|---|---|---|---|---|
| **Monthly** | ≈CNY 1,300 | ≈CNY 6,495 | **≈+CNY 5,195 (5×)** | ≈26 h | ≈32.5 h | +25% |
| **Annual** | CNY 15,600 | CNY 78,000 | **+CNY 62,400 (5×)** | 312 h | 390 h | +25% |
| Weekly (reference) | CNY 300 | CNY 1,500 | +CNY 1,200 (5×) | 6 h | 7.5 h | +1.5 h (+25%) |

**Key insight:** time investment goes up only **25%**, while revenue goes up **5×**. This is a productivity multiplier, not a headcount or labor-cost reduction — the same team serves 5× the client volume at an unchanged unit price, and revenue scales with it.

---

## Engineering Highlights

- **AI-suggestion generation** — architecture direction is client-side WebLLM (in-browser inference via WebGPU/WASM); no server-side model API key required for the intended product path. Selected proposals are still persisted through the backend.
- **Structured, auditable data model** — sessions → correction histories → AI proposals, with full selection tracking, so every AI suggestion and human decision is traceable after the fact.
- **Modern, typed frontend** — Next.js 15 (App Router) + React 19 + TypeScript, styled with Tailwind CSS and shadcn/ui (Radix primitives), covering the full review-and-approve workflow.
- **REST API** — FastAPI backend exposing session, history, proposal, and related endpoints, with a `/health` check for deployment monitoring.
- **Spec-driven development** — feature work is planned and tracked via [OpenSpec](https://github.com/Fission-AI/OpenSpec) proposals before implementation, keeping product intent and code in sync.

---

## Tech Stack

**Backend:** Python · FastAPI · PostgreSQL
**Frontend:** Next.js 15 · React 19 · TypeScript · Tailwind CSS · Radix UI · WebLLM (client-side)
**Infra:** Vercel (frontend) · Render (backend) · Terraform (backend infra-as-code)

## Getting Started

```bash
git clone <repository-url> && cd mjai
cp conf/.env.example conf/.env   # fill in env vars — see AGENTS.md
```

See `AGENTS.md` for environment variables, local/Docker run instructions, and deployment details.

## Deployment

- **Frontend:** Deployed via Vercel git integration. Push to `main` triggers automatic production deployment; PRs get preview deployments.
- **Backend:** Deployed to Render (managed outside Terraform). CI workflow verifies `/health` endpoint after infrastructure changes.

---

## License

MIT

## Contributing

Pull Requests and Issues welcome.
