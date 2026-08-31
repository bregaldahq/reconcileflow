# Adversarial fixtures

Add synthetic regression cases here whenever a bug or surprising edge case is found.

Examples:

- `R$ 1.234,56` vs `1234.56`;
- date ambiguity;
- Unicode whitespace;
- duplicated rows;
- empty identifiers;
- multiple equal candidates;
- split combinations with several valid solutions.

Rule:

> A production bug should leave behind a fixture/test that makes that bug harder to reintroduce.
