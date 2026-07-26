---
name: migrate-hf-benchmark-results
description: Convert published benchmark leaderboards from Hugging Face datasets, papers, blog posts, GitHub READMEs, tables, or similar sources into local, human-reviewable draft changes for Hugging Face model repositories using `.eval_results/*.yaml`. Use when mapping benchmark model names to exact Hub model repos, checking native benchmark task IDs, extracting scores with provenance, preventing duplicate benchmark submissions, handling existing eval files or open PRs, and preparing a per-model PR plan. Never open, upload, or submit the model PRs; stop at a review bundle so a human can verify every target and value first.
---

# Migrate HF Benchmark Results

Prepare an auditable local review bundle that shows exactly which model repositories would receive which `.eval_results/*.yaml` changes. Treat the benchmark as the score authority and the Hub repository match as a separate claim requiring evidence.

## Prerequisite: Hugging Face CLI and skill

Check for both the `hf` command and the `hf-cli` agent skill before starting Hub discovery.

1. If the `hf` command is unavailable, install the Hugging Face CLI by following the current [official CLI installation guide](https://huggingface.co/docs/huggingface_hub/en/guides/cli), then verify it with:

   ```bash
   hf --help
   ```

2. If the `hf-cli` skill is unavailable to the coding agent, install it using the instructions for the active harness in the [Hugging Face skills repository](https://github.com/huggingface/skills/tree/main). For example, current installations may use `hf skills add` for agents that load `.agents/skills`, `hf skills add --claude` or the Claude Code plugin flow, or a copy/symlink into a Codex `.agents/skills` location.

3. Reload the harness if required, confirm that the `hf-cli` skill is discoverable, and read that skill before continuing.

If the environment does not permit installing the CLI or skill, stop and tell the user what is missing. Do not replace exact Hub discovery with guessed repository URLs.

## Non-negotiable boundary

- Perform read-only network operations only.
- Never create a Hub PR or discussion, upload a file, push a branch, or call an API with write intent.
- Never use `hf upload --create-pr`, `hf discussions create --pull-request`, `create_commit(..., create_pr=True)`, or an equivalent operation.
- Do not request a write token. Authentication may be used only when needed to read a source the user is authorized to access.
- Never draft or later submit a new PR for a model repo if the benchmark dataset ID already appears in any `.eval_results/*.yaml` file on its default branch or in any open PR. Treat one existing task on the default branch as an existing result for the whole benchmark.
- An open PR authored by the currently authenticated Hugging Face account may instead be updated in place with missing task entries. Never use this exception for another author's PR, an unwritable PR, conflicting values, or a second matching open PR.
- Stop after presenting the complete review bundle. State that no PRs were opened or updated.
- If the user later approves submission, treat that as a separate task, require an explicit list of approved repositories, approved file contents, and any existing PRs approved for in-place updates. Repeat the duplicate and ownership checks immediately before each write. A human request to open PRs does not override the duplicate-prevention rule. Do not include submission commands in this skill's deliverable.

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
hf auth whoami --format json
```

Fetch every existing `.eval_results/*.yaml` file read-only and search parsed entries for the exact benchmark `dataset.id`; do not rely on filenames or the `eval-results` tag. Inspect the diff of every open PR rather than relying only on its title.

- If the benchmark dataset ID appears anywhere on the default branch, mark the repo `already_present`, link the existing file, and create no draft for that repo.
- If exactly one open PR contains the benchmark dataset ID and its author matches the account reported by `hf auth whoami`, compare its current entries with the source. If all existing values agree and only task entries are missing, mark the repo `update_existing_pr`, link the PR, and draft the complete intended file based on the PR's latest diff. If it already contains every intended entry, mark it `already_in_own_open_pr` and create no draft.
- If the matching open PR belongs to another account, ownership cannot be confirmed, the PR cannot be updated by the authenticated account, or more than one matching PR exists, mark the repo `duplicate_open_pr`, link every matching PR, and create no draft.
- If an owned open PR contains conflicting values, mark the repo `needs_review`; show both versions and do not overwrite silently.
- Never open a second PR when `update_existing_pr` applies. Preserve unrelated changes already present in the owned PR and add only the approved missing task entries.
- If any file or open-PR diff cannot be inspected reliably, mark the repo `needs_review` and exclude it from PR candidates until the check succeeds.
- Record the model revision, open-PR numbers and authors, authenticated account, and check time so reviewers can detect stale checks.

Immediately before any separately authorized submission, repeat this complete check. For `update_existing_pr`, confirm the same authenticated account still owns and can update the same open PR, refresh its latest diff, and apply the approved full-file result to that PR rather than creating another one. If a result has reached the default branch, another matching PR has appeared, ownership or writability changed, or the PR contents now conflict, skip the update and report the new state.

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
- For `update_existing_pr`, base the draft on the latest file content in that PR and include the complete post-update file, not only the missing entries.

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

In the final response, summarize counts for source models, exact repo matches, new-PR drafts, owned-PR update drafts, existing-result skips, duplicate-open-PR skips, unresolved checks, ambiguous matches, and models not on the Hub. Link every local artifact. Explicitly say: **No Hugging Face pull requests were opened or updated.**

## Quality gate

Do not mark the migration ready for review unless all of the following hold:

- Every YAML task ID exists in the current benchmark `eval.yaml`.
- Every drafted value has a stable source locator.
- Every drafted repo is an exact match to the evaluated artifact.
- Every source model appears in the ledger, even if excluded.
- Every `.eval_results/*.yaml` file and every open PR was checked for the benchmark dataset ID.
- No new-PR draft targets a repo that already contains the benchmark on its default branch or in an open PR.
- Every owned-PR update draft identifies exactly one matching open PR, confirms its author matches the authenticated account, and adds only non-conflicting missing tasks to the latest PR contents.
- Conflicts and uncertainties remain visible rather than being resolved by assumption.
- Draft files pass structural validation.
- No remote write operation occurred.
