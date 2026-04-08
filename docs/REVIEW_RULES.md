# Review Rules

These rules are the hard gate for any change produced in this workspace.

## Blockers

Hold the change if any of these are true:

- the change solves the task with a hack instead of a defensible design
- a new library or dependency was added without explicit user approval
- behavior changed but verification is missing or clearly weak
- error handling became broader, vaguer, or less predictable
- code was copied into multiple places instead of extracted once
- the diff mixes the requested task with unrelated cleanup
- public behavior changed without being called out clearly
- dead code, TODO-driven logic, or placeholder control flow was introduced

## Positive qualities

Prefer changes that are:

- small and reviewable
- explicit about assumptions
- easy to test
- aligned with existing architecture
- legible to the next engineer or agent

## Cleanup rule

Styling or naming cleanup is allowed only if it remains tightly scoped and does not obscure the behavior change.
