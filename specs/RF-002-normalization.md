# RF-002: Versioned normalization

Implement `br-v1` money/date/document/text/empty/source-ID normalization. Cover `1.234,56`, `1234.56`, `R$ 1.234,56`, punctuation-heavy identifiers, Unicode/inconsistent whitespace, duplicates, and missing IDs with golden and adversarial fixtures. Output is deterministic under repeated calls.
