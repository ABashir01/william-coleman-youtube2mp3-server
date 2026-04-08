# Codex Operating Instructions

This workspace exists to drive a strict plan -> implement -> test -> architecture review loop.

## Required workflow

For any non-trivial task, follow this sequence:

1. Read `docs/WORKFLOW.md`.
2. Convert the user request into explicit acceptance criteria.
3. Write a short execution note in the response before editing.
4. Implement the smallest end-to-end change that could satisfy the request.
5. Run the narrowest useful checks from `docs/TEST_POLICY.md`.
6. Review the result against `docs/REVIEW_RULES.md` and `docs/ARCHITECT_CHECKLIST.md`.
7. If any check or review item fails, fix the issue and repeat the loop.
8. Stop only when the work passes or a real blocker remains.

## Agent posture

- Do not wait for permission for normal work inside the workspace.
- Do not add dependencies unless the user explicitly allows it.
- Do not use destructive git commands.
- Do not broaden scope during cleanup.
- Prefer small diffs with clear reasoning over sweeping rewrites.

## Review gate

Treat architecture review as a gate, not a suggestion pass.

Hold the change if any of the following are true:

- behavior changed without tests or checks
- a shortcut was used where a small coherent abstraction is warranted
- a new dependency was introduced without explicit approval
- logic was duplicated instead of placed at the correct boundary
- the code is harder to reason about after the change
- the implementation relies on guessed assumptions that could have been validated

## Output expectations

Final responses should include:

- what changed
- what was tested or checked
- whether the architecture review passed
- any remaining risks or assumptions
