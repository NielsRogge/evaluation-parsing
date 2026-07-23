---
name: migrate-hf-benchmark-results
description: Convert published benchmark leaderboards from Hugging Face datasets, papers, blog posts, GitHub READMEs, tables, or similar sources into local, human-reviewable draft changes for Hugging Face model repositories using `.eval_results/*.yaml`. Use when mapping benchmark model names to exact Hub model repos, checking native benchmark task IDs, extracting scores with provenance, handling existing eval files or open PRs, and preparing a per-model PR plan. Never open, upload, or submit the model PRs; stop at a review bundle so a human can verify every target and value first.
---

# Migrate HF Benchmark Results

Prepare an auditable local review bundle that shows exactly which model repositories would receive which `.eval_results/*.yaml` changes. Treat the benchmark as the score authority and the Hub repository match as a separate claim requiring evidence.

## Non-negotiable boundary

- Perform read-only network operations only.
- Never create a Hub PR or discussion, upload a file, push a branch, or call an API with write intent.
- Never use `hf upload --create-pr`, `hf discussions create --pull-request`, `create_commit(..., create_pr=True)`, or an equivalent operation.
- Do not request a write token. Authentication may be used only when needed to read a source the user is authorized to access.
- Stop after presenting the complete review bundle. State that no PRs were opened.
- If the user later approves submission, treat that as a separate task and require an explicit list of approved repositories and their approved file contents. Do not include submission commands in this skill's deliverable.

## 1. Establish the benchmark contract

Identify the canonical benchmark dataset repository and read its root `eval.yaml`. Confirm that it is currently recognized as a Hub benchmark; do not infer this solely from the source calling itself a benchmark.

Record:

- exact dataset ID and optional pinned revision;
- every valid `tasks[].id` relevant to the source scores;
- benchmark/source URL and immutable revision or commit when available;
- metric meaning, direction, unit, aggregation, subsets, and evaluation setting;
- correspondence between source columns and Hub task IDs.

Use task IDs exactly as declared in `eval.yaml`. Do not invent an `overall` or `default` task. If the dataset is not a native Hub benchmark, its task mapping is unclear, or the source metric cannot be represented by the available tasks, stop and report the prerequisite instead of drafting model changes.

Consult the current official format before drafting: <https://huggingface.co/docs/hub/eval-results>. Read [references/review-bundle.md](references/review-bundle.md) before creating artifacts.

## 2. Extract a source ledger

Read the canonical source in full enough to interpret its leaderboard correctly. For each reported model, capture one ledger row per score with:

- source model label exactly as printed;
- task/column and numeric value exactly as printed;
- model version, checkpoint, size, variant, and evaluation setting;
- source URL plus a stable locator such as table, heading, row, page, or line;
- any footnote affecting comparability or eligibility.

Never silently select the best score, average columns, combine runs, convert units, or drop qualifiers. Draft only results explicitly attributable to the exact evaluated artifact. Mark unclear cells `needs_review`; do not guess from typography, chart pixels, OCR ambiguity, or neighboring rows.

For generated or mirrored leaderboards, trace values to the most authoritative upstream source available. Keep both URLs when the benchmark repository provides the native task contract but a paper, blog, or README provides the numbers.

## 3. Resolve exact Hub model repositories

Use the `hf-cli` skill for Hub discovery. Start with exact candidates, then search only when needed:

```bash
hf models info OWNER/MODEL --format json
hf models list --search "SOURCE MODEL LABEL" --limit 20 --format json
```

Confirm that each candidate is a model repo and that its owner, model family, version, size, modality, checkpoint type, and variant match the evaluated row. Use model-card claims, config metadata, official links, and organization ownership as evidence.

Classify every source model as one of:

- `exact`: one defensible Hub repo for the evaluated artifact;
- `ambiguous`: multiple plausible repos or insufficient version evidence;
- `not_on_hub`: no matching model repo found after exact lookup and search;
- `mismatch`: a Hub repo exists only for a different size, version, base/instruct variant, quantization, fine-tune, or checkpoint;
- `not_applicable`: proprietary API/system or another artifact without a corresponding Hub model repo.

Draft files only for `exact`. Do not redirect a result to a base model, newer release, collection, organization page, Space, GGUF/quantized conversion, or unofficial mirror unless the benchmark explicitly evaluated that exact artifact. Preserve all excluded rows in the review report with reasons and searched candidates.

## 4. Inspect current model state

For each exact repo, inspect the current repository files and open PRs before drafting:

```bash
hf models info OWNER/MODEL --expand siblings,sha --format json
hf discussions list OWNER/MODEL --kind pull_request --status open --format json
hf discussions diff OWNER/MODEL PR_NUMBER --type model
```

Fetch relevant existing `.eval_results/*.yaml` files read-only. Determine whether the proposed `(dataset.id, task_id)` entries are absent, already identical, conflicting, or present in an open PR.

- Preserve unrelated existing entries and formatting where practical.
- Prefer editing the benchmark's existing eval-results file over creating a duplicate file.
- Mark identical results `already_present` and do not draft a no-op.
- Mark conflicting values or duplicate open-PR work `needs_review`; show both versions and do not overwrite silently.
- Record the model repo revision inspected so reviewers can detect staleness.

## 5. Draft model-side YAML

Create one local draft tree per model, mirroring the intended repo-relative path, for example:

```text
drafts/PaddlePaddle--PaddleOCR-VL-1.6/.eval_results/real5-omnidocbench.yaml
```

Use a YAML list. Include only supported fields and only metadata supported by the source:

```yaml
- dataset:
    id: PaddlePaddle/Real5-OmniDocBench
    task_id: overall
  value: 93.19
  source:
    url: https://huggingface.co/datasets/PaddlePaddle/Real5-OmniDocBench
    name: Real5-OmniDocBench leaderboard
  notes: "Official reported result for PaddleOCR-VL-1.6"
```

Apply these rules:

- Keep `value` numeric and preserve the benchmark's published scale.
- Add `dataset.revision` only when a specific dataset revision is part of the result claim.
- Add `date` only when the evaluation date is known; do not substitute publication, commit, or access dates.
- Add `verifyToken` only when supplied for that exact run.
- Set `source.url` to the page that substantiates the number, with an informative `source.name`.
- Use `source.user` only when the attribution is known and relevant.
- Use `notes` sparingly for material setup/variant qualifiers; do not turn it into provenance storage.
- Use a stable lowercase filename derived from the benchmark. Avoid overwriting an unrelated existing file.

Run the bundled read-only validator against the draft tree:

```bash
uv run scripts/validate_drafts.py REVIEW_BUNDLE \
  --benchmark-id OWNER/BENCHMARK \
  --task-id TASK_ID [--task-id TASK_ID ...]
```

Treat validation success as structural checking, not proof that model matching or values are correct.

## 6. Produce the human review bundle

Follow [references/review-bundle.md](references/review-bundle.md). At minimum, create:

- `review.md` with the benchmark contract, source provenance, target decision table, exclusions, conflicts, and reviewer checklist;
- `source-ledger.csv` containing every source row, including unresolved models;
- `drafts/.../.eval_results/*.yaml` containing exact proposed file contents;
- `validation.txt` containing validator output and the command used.

In the final response, summarize counts for source models, exact repo matches, drafts, no-ops, conflicts, ambiguous matches, and models not on the Hub. Link every local artifact. Explicitly say: **No Hugging Face pull requests were opened.**

## Quality gate

Do not mark the migration ready for review unless all of the following hold:

- Every YAML task ID exists in the current benchmark `eval.yaml`.
- Every drafted value has a stable source locator.
- Every drafted repo is an exact match to the evaluated artifact.
- Every source model appears in the ledger, even if excluded.
- Existing results and open PRs were checked.
- Conflicts and uncertainties remain visible rather than being resolved by assumption.
- Draft files pass structural validation.
- No remote write operation occurred.
