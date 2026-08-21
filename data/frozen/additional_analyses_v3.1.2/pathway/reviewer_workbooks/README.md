# Public completed reviewer workbooks

This directory contains metadata-sanitized, content-equivalent public copies of the completed pathway-validation workbooks supplied for AISKG v3.1.2:

- `Expert_A_completed_public.xlsx` — 115 pathway rows and seven rating dimensions;
- `Expert_B_completed_public.xlsx` — the same 115 pathways and seven rating dimensions; and
- `Third_Expert_completed_public.xlsx` — 92 rating-dimension adjudications.

The public copies were imported and exported with `artifact_tool`, verified cell-for-cell (values and formulas) against the supplied uploads, stripped of `docProps`, and rewritten with fixed ZIP timestamps. The untouched uploads are excluded from GitHub because their document metadata contained a personal account address; they are retained only in the author-side private provenance archive.

The replay validates 805 A/B rating pairs, 22 direct disagreements, 84 cases containing a Borderline or Uncertain source rating, and the exact 92-case union requiring third-expert adjudication. Every third-expert row is checked against the corresponding source labels, comments, path text, and pathway template.

Two submitted Expert A `complete_pathway_correct` values (`XPV-0052` and `XPV-0074`) differ from the deterministic component roll-up. The source values are preserved rather than silently edited; both cases are explicitly adjudicated `No` in the third-expert workbook.
