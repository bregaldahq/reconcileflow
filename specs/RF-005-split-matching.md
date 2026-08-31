# RF-005: Bounded split matching

Plan: pre-index by configured identity fields; create bounded candidate pools; enumerate combinations in stable participant order; stop at configured inspection limit; score by amount/date distance and group size; return ambiguity for equal best groups; claim all participants atomically. Benchmark bounded worst case and assert amount conservation.
