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

Set decision to `draft`, `update_existing_pr`, `already_present`, `already_in_own_open_pr`, `duplicate_open_pr`, or `needs_review`. For `update_existing_pr`, link the existing PR, record its author and the authenticated account, and make the local draft the complete intended file based on the PR's latest contents. For skips, link the existing `.eval_results` file or every matching open PR and do not create a draft. Link the source locator and local draft from the surrounding prose when a table cell would become unwieldy.

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
- [ ] Every existing `.eval_results` file and every open PR was searched for the benchmark dataset ID.
- [ ] No new-PR draft targets a repo where that benchmark already appears on the default branch or in an open PR.
- [ ] Every `update_existing_pr` draft targets exactly one writable PR owned by the authenticated account, preserves its unrelated changes, and adds only non-conflicting missing tasks.
- [ ] Source attribution, dates, revisions, and notes are factual.
- [ ] Every draft file contains only the intended change.
- [ ] The approved repository list and any approved existing PR updates are explicit before any later submission task.

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
- Any existing entry for the benchmark dataset ID disqualifies the repository from a new draft, even if it covers only one task or has a different value.
- An open PR containing the benchmark dataset ID disqualifies the repository from a new PR.
- If exactly one matching open PR is owned and writable by the authenticated account, an `update_existing_pr` draft may add missing task entries in place when all existing values agree with the source.
- Another author's PR, multiple matching PRs, an unwritable PR, or conflicting values disqualify in-place updates.
- The bundle is incomplete if only drafted models are reported.
