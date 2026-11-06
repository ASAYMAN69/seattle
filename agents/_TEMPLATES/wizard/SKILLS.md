# SKILLS.md — Wizard (Backend) skill map

> **How to use this file.** At the start of every task, read this list. Load a skill **only if its trigger condition is true** for the current task. You never load all skills at once.

| Skill | Load it WHEN… | What it gives you |
|---|---|---|
| `api-and-interface-design` | You are designing or changing an API, module boundary, or public interface | API/interface stability practices (REST/GraphQL contracts, type boundaries) |
| `codebase-design` | You are structuring modules, finding seams, or making code more testable | Deep-module vocabulary for well-bounded units |
| `domain-modeling` | You need to define/shape the domain model, terminology, or a GLOSSARY | Shared domain language and model clarity |
| `source-driven-development` | You need to verify an approach against official docs before implementing | Authoritative, source-cited implementation patterns |
| `database-migrations` | You are changing schema/data (add column, index, backfill) | Safe, reversible, zero-downtime migration patterns |
| `deprecation-and-migration` | You are removing/renaming an old system, API, or feature | Expand/contract migration and sunset workflows |
| `performance-optimization` | You suspect slow queries, N+1s, or latency issues | Profiling-driven optimization across queries/db/code |
| `observability-and-instrumentation` | You are shipping a feature that must be diagnosable in production | Logging, metrics, tracing, alerting patterns |
| `debugging-and-error-recovery` | Tests fail / a build broke / behavior regressed | Systematic root-cause debugging |
| `diagnosing-bugs` | A hard bug or performance regression is reported | Structured diagnosis loop |
| `code-review-and-quality` | You are reviewing code (yours or another's) before it stands | Multi-axis quality assessment |
| `code-simplification` | Code works but is harder to read than it should be | Clarity-preserving refactoring |
| `karpathy-guidelines` | You are writing new code (always relevant as a baseline) | Behavioral guardrails: avoid overcomplication, surgical changes |
| `constraint-driven-development` | The project has a written quality bar you must not lower | Enforces thresholds (coverage, perf, types) |
| `incremental-implementation` | The change spans several files / feels large | Thin, verifiable implementation slices |
| `git-workflow-and-versioning` | You are committing/branching/opening a PR | Clean history, atomic commits, versioning |
| `ci-cd-and-automation` | You are setting up/modifying build & deployment pipelines | Pipeline automation and quality gates |
| `documentation-and-adrs` | You are making an architectural decision that should be recorded | ADR workflow and decision documentation |
