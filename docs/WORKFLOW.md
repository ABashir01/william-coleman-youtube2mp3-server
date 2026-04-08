# Workflow

This workspace uses a RALPH-style loop, expressed as a practical engineering cycle.

## Core loop

1. Read the task carefully.
2. Inspect the relevant code or files before deciding on an approach.
3. State the plan briefly.
4. Implement a minimal complete slice.
5. Run targeted verification.
6. Review against architecture and quality rules.
7. Repair defects or design issues.
8. Repeat until the result passes.

## Decision rules

- Prefer direct solutions over elaborate frameworks.
- Preserve existing patterns unless they are clearly defective.
- If the task is ambiguous but low-risk, make a reasonable assumption and state it.
- If the task has high-impact ambiguity, ask one precise question.

## Loop exit criteria

The loop can end only when all of the following are true:

- the requested behavior is implemented
- the relevant tests or checks were run, or a concrete reason explains why not
- the change passes `docs/REVIEW_RULES.md`
- no unresolved architectural concern remains that would likely force rework
