# Architect Checklist

Use this checklist after implementation and after tests.

## Architecture

- Is the change placed at the correct boundary?
- Is a reusable abstraction needed instead of local patch logic?
- Did the change preserve or improve cohesion?
- Did the change avoid unnecessary dependencies?

## Correctness

- Are inputs and assumptions validated?
- Are errors handled in a specific and understandable way?
- Are edge cases covered by tests or clearly addressed?

## Maintainability

- Is the control flow easy to follow?
- Is naming clear and consistent?
- Is the diff narrowly scoped to the task?

## Verdict

If any answer indicates a meaningful design or reliability problem, treat the review as HOLD until repaired.
