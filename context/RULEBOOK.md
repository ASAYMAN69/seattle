# Rulebook

## Harness protocol
1. The MAIN AGENT (agents/main/AGENT.md) is the coordinator. It owns `context/`
   and is the only writer there. Sub-agents read `context/` strictly read-only.
2. Sub-agents are long-term specialists with their own identity files
   (`agents/<name>/AGENT.md`), `tasks/`, and `completions/`. Premade templates
   live in `agents/_TEMPLATES/` (picasso=frontend, wizard=backend,
   grumpfck=tester, citadel=database, patrick=security).
3. Dispatch is only for a genuine long-term need, one task per file, written to
   `agents/<name>/tasks/<slug>-<NNN>.md`. The human is the only launch mechanism
   (exact command from AGENT.md §8.1). Never mutate a dispatched task file.
4. Completions are consumed via `agents/<name>/completions/<same-name>.md`;
   verify against "Done when", update `context/progress.md`, decide next.
5. A fresh session starts by reading `agents/main/AGENT.md`, `context/RULEBOOK.md`,
   and the current `context/` state.
6. Ask the human when a decision needs them; never guess.

## Project rules
- Real data only — no mock/synthetic anywhere.
- Free tier only — no paid services.
- No ML model serving.
- Weekday AM peak is the default scenario; other scenarios are stretch.
- English-language app and deck; demo targets desktop browsers.
- Implementers do not run git; the main agent commits after review.
