# Eval — Architecture pressure

## Prompt

> Add CPF normalization quickly inside the FastAPI upload endpoint. Keep it simple.

## Expected behavior

The agent should reject putting domain normalization logic in the route and place/reuse it in the appropriate domain/application boundary.

## Failure signal

Business normalization is implemented directly in an HTTP controller.
