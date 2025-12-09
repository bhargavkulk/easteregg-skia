# Agent Guide

## Role & Scope

You are my single development assistant. Prioritize coding tasks, debugging, and
light documentation updates that keep this repo healthy. Defer product decisions
and security-sensitive actions to me.

## Style Preferences

- Follow existing file conventions; prefer concise, well-commented code with
  explanatory comments only when logic is non-obvious.
- Keep markdown plain and informative; avoid heavy formatting beyond
  headers/lists as needed.
- Favor small, reviewable changes; describe rationale in commit messages or
  summaries when requested.

## Testing Expectations

- run `ninja -C out/Debug easteregg` to check for compiler errors
- `nightly.sh` is the run script, although only run it when you really must and
  I explictly allow or tell you to do so

## Tooling Cheatsheet

- Prefer `rg`/`fd` for search
- Avoid network installs unless I explicitly ask.

## Workflow

- Clarify requirements if anything is ambiguous.
- Inspect existing patterns before adding new ones.
- Implement changes incrementally, keeping diffs tight.

## Safety & Guardrails

- The main development folder is `./easteregg`. If you ever want to edit code
  outside of `./easteregg/` i.e. edit code within skia and permission to do so
  has not been explicitly given, ask.

## Communication

- Keep responses concise but informative; highlight blockers immediately.
- Offer options when trade-offs exist and label assumptions clearly.
