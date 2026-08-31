# Ingestion and export specification

CSV accepts UTF-8 with BOM handling and configurable delimiter detection; XLSX reads values from the first configured sheet and rejects macro-enabled files. Headers must be non-empty and unique after trimming. Rows exceeding limits fail with structured validation issues.

The fingerprint is SHA-256 of the original upload bytes. Normalized row IDs derive from fingerprint and one-based data-row number when no source ID is mapped.

The XLSX export contains Summary, Matched, Unmatched, Ambiguous, Duplicates, and Manual Review sheets. It freezes headers, enables filters, sets practical widths, and writes money as numeric cells with fixed decimal formatting. Strings beginning with spreadsheet formula control characters are prefixed with an apostrophe.
