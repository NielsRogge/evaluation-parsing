# Review bundle specification

Use this layout so a human can review targets and contents without reconstructing the extraction process:

```text
<bundle>/
├── review.md
├── source-ledger.csv
├── validation.txt
└── drafts/
    └── <owner>--<model>/
        └── .eval_results/
            └── <benchmark-slug>.yaml
```

Do not place credentials, tokens, downloaded model weights, or a script capable of submitting PRs in the bundle.

## `review.md`

Write these sections.

### 1. Benchmark contract

Record the dataset ID, inspected revision, `eval.yaml` URL, valid task IDs, source URL/commit, metric scale and direction, and the explicit source-column-to-task mapping.

### 2. Proposed repository changes

Use one row per target model:

| Source model | Hub repo | Match evidence | Inspected SHA | Draft path | Tasks/values | Existing state | Decision |
|---|---|---|---|---|---|---|---|

Set decision to `draft`, `already_present`, or `needs_review`. Link the source locator and local draft from the surrounding prose when a table cell would become unwieldy.

### 3. Excluded and unresolved models

Use one row for every source model without a draft:

| Source model | Classification | Candidates checked | Reason | Source locator |
|---|---|---|---|---|

Use the classifications from `SKILL.md`. A complete exclusion table is essential: reviewers must see the full blast radius, not just successful matches.

### 4. Conflicts and assumptions

List existing differing values, duplicate open PRs, ambiguous source cells, task mapping concerns, or stale revisions. Do not hide these in footnotes.

### 5. Reviewer checklist

Include unchecked boxes for a human to verify:

- [ ] Each Hub repo is the exact evaluated model artifact.
- [ ] Each task/value matches the cited source locator and published scale.
- [ ] Each task ID exists in the benchmark's current `eval.yaml`.
- [ ] Existing model results and open PRs are handled correctly.
- [ ] Source attribution, dates, revisions, and notes are factual.
- [ ] Every draft file contains only the intended change.
- [ ] The approved repository list is explicit before any later submission task.

End with: `No Hugging Face pull requests were opened while preparing this bundle.`

## `source-ledger.csv`

Use these columns:

```text
source_model,source_variant,source_task,source_value,source_unit,source_url,source_locator,qualifiers,hub_repo,match_status,match_evidence,decision
```

Quote CSV fields correctly. Preserve source spelling and precision. Use additional rows for multiple task values rather than encoding several values into one cell.

## Review semantics

- A draft is a proposed full file after the change, not an isolated snippet, when the destination file already exists.
- A draft path is repo-relative beneath its model directory.
- A reviewer must be able to compare any numeric YAML value to one ledger row.
- A model with several task values may use one YAML file containing several list entries.
- The bundle is incomplete if only drafted models are reported.
