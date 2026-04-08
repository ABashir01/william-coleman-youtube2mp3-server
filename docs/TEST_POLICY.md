# Test Policy

Every behavior change needs verification.

## Verification order

Run the narrowest useful checks first:

1. focused unit tests for changed logic
2. feature-level or integration tests if the change crosses boundaries
3. broader test suite only when needed

## Rules

- Do not skip tests silently.
- Do not weaken assertions to get green output.
- Do not add heavy testing infrastructure unless explicitly requested.
- If tests cannot run, state exactly why and describe the remaining risk.

## Minimum standard

Before declaring success, provide:

- the commands run
- whether they passed or failed
- what remains unverified
