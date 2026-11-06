# SKILLS.md — Citadel (Database Master) skill map

> **How to use this file.** At the start of every task, read this list. Load a skill **only if its trigger condition is true** for the current task. You never load all skills at once.

> **Deployment note.** This agent is only dispatched when the project is large enough that the Backend agent alone cannot guarantee database safety.

| Skill | Load it WHEN… | What it gives you |
|---|---|---|
| `database-migrations` | A feature launch changes the schema (new table, new column, index, backfill) | Safe migration execution & review (expand/contract, batching) |
| `performance-optimization` | You must judge whether queries are safe *and* performant under the schema | Query/database performance patterns (indexing, plans, N+1) |
| `security-and-hardening` | You must verify queries are safe against injection / unsafe patterns | Injection & input-handling hardening patterns |
