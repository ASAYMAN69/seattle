# SKILLS.md — Grumpfck (Tester) skill map

> **How to use this file.** At the start of every task, read this list. Load a skill **only if its trigger condition is true** for the current task. You never load all skills at once.

| Skill | Load it WHEN… | What it gives you |
|---|---|---|
| `tdd` / `test-driven-development` | You are writing tests for new behavior (or verifying a feature was built test-first) | Red-green-refactor discipline, test design |
| `webapp-testing` | The feature is a web app and you need to interact with it to verify | Playwright interaction toolkit (click, form, screenshot, logs) |
| `browser-testing-with-devtools` | You need to inspect DOM, capture console errors, analyze network, or verify runtime behavior | Real-browser diagnostics via DevTools |
| `debugging-and-error-recovery` | A test fails or behavior doesn't match and you must find the cause | Systematic root-cause debugging |
| `diagnosing-bugs` | You are chasing a hard bug across the app | Structured bug diagnosis loop |
| `code-review-and-quality` | You must judge whether merged code is actually solid before signing off | Multi-axis quality assessment |
| `full-output-enforcement` | You are writing a large test file / suite that risks truncation | Complete, non-placeholder test output |
| `setup-pre-commit` | The repo lacks hooks and you need tests to run automatically on commit | Husky/lint-staged setup |
