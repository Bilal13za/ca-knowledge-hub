# Source Verification Policy

**Status:** Phase 1A (v1). This policy is non-negotiable across all phases.

## The rule

Every technical knowledge record must be traceable to its source. **Never
invent**: legal provisions, tax rates, accounting requirements, auditing
requirements, source quotations, page references, effective dates, or
verification status.

## Verification statuses (database enum)

| Status | Meaning | When to use |
|---|---|---|
| `verified` | Checked against the primary source by a human | Rates, provisions, standard requirements you personally confirmed |
| `extracted_unverified` | Machine-extracted from a document, not yet human-checked | Refresh Library output before review |
| `user_note` | Your own notes, interpretations, summaries | Study notes, personal checklists |
| `interpretation` | Professional judgement applied to sources | "In practice this usually means…" (must cite basis) |
| `superseded` | Replaced by a newer version | Old tax rates, amended provisions — kept for history |

The status is **always visible** in the UI next to the record. There is no
"unknown" — if you don't know, it is `extracted_unverified` or `user_note`.

## Workflow

1. **Ingest** → records arrive as `extracted_unverified` with `source_id`
   + `source_page` filled by the extractor.
2. **Verify** → a human checks against the primary source, sets
   `verified`, fills `last_reviewed`, sets `review_due_date`, and appends
   a `verification_records` row (who/when/method).
3. **Change** → never edit in place for important rules: insert a new
   version row, mark the old `superseded` (link `superseded_by`), append
   `revision_history` with reason + source of change.
4. **Review cycle** → the UI surfaces records whose `review_due_date`
   has passed. Tax rules: review yearly. Standards: on amendment.

## What "source" means per domain

- **Tax:** the Act/Ordinance section, SRO/notification number, FBR
  circular — with tax year and effective date. Secondary summaries are
  `extracted_unverified` until checked against the primary text.
- **Audit:** ISA/ISQC wording from the standard itself; firm methodology
  is `user_note` unless published.
- **Financial reporting:** the IFRS/IAS paragraph from the standard.
- **Law:** the Companies Act 2017 section number from the Act text.

If the primary text is not available, the record stays
`extracted_unverified` and says so. An honest gap beats a confident
invention.
