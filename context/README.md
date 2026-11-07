# context/ — Shared Memory (Why Each File Exists)

This directory is the project's **shared memory**. It is the single source of
truth for *why* the project is what it is. Every agent (and the human) reads it;
only the MAIN AGENT writes it. Sub-agents are strictly read-only here.

Per the harness rulebook (`context/RULEBOOK.md`), every fresh session starts by
reading `agents/main/AGENT.md`, `context/RULEBOOK.md`, and the current `context/`
state before acting. If you are confused about the project, start here.

---

## File-at-a-glance

| File | What it holds | Why it exists |
| --- | --- | --- |
| `project.md` | The core vision: what we're building, for whom, why, and the hard principles. | So anyone joining (human or agent) understands the product's **purpose** in one page — not the code, but the *idea*. Prevents drift toward "build whatever." |
| `features.md` | The inventory of features, grouped by phase, each with a status (DONE / IN PROGRESS / PLANNED / DEFERRED). | The authoritative **feature ledger**. Answers "what exists, what's promised, what was deferred" without reading code. Is the skeleton for `CHECKLIST.md`. |
| `progress.md` | The verified, chronological record of what has actually been built and what is next (including the dispatch log of subagent tasks). | Keeps history honest across sessions. Because it is *verified* (not aspirational), it is the place to check "did that task actually land?" and "what's next?" |
| `decisions.md` | Every consequential choice made — with the reasoning — plus deferred minors we agree not to re-litigate. | **Anti-re-litigation memory.** Prevents re-arguing closed questions (e.g. "why not Streamlit?", "why only Seattle?", "why this GTFS approximation?") and records user rulings that override defaults. |
| `RULEBOOK.md` | Harness protocol + project rules (the "constitution" for how agents operate here). | The operating contract. Tells agents how to behave (read-only on context/, no git, dispatch rules, real-data-only) so the harness runs predictably. |
| `README.md` | This file. | The map of the map: so you know what to read and when, and so the directory isn't a mystery. |

---

## How to use them

- **"What is this project?"** → read `project.md`.
- **"What exists / what's planned?"** → read `features.md`.
- **"Where are we?"** → read `progress.md` (and `CHECKLIST.md` at repo root for the submission-facing view).
- **"Why did we choose this?"** → read `decisions.md`.
- **"How do agents operate here?"** → read `RULEBOOK.md`.

Reading order for a fresh session (per RULEBOOK): `RULEBOOK.md` → `project.md`
→ `features.md` → `decisions.md` → `progress.md`.

---

## Notes on staleness

These files are maintained by the main agent **after** each completed task and
each conversation that changes the shared picture. They can still lag reality by
one step if a change hasn't been reconciled yet. If you see a file contradicting
a newer decision, trust `decisions.md` + the repo, and flag the staleness to the
main agent. (The previously-known staleness — `project.md`/`features.md` still
describing the Streamlit app — was reconciled 2026-11-07 alongside this file.)
