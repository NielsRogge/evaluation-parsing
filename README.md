# Evaluation parsing

This repository contains scripts which can be used to extract evaluation results from Hugging Face models, and automatically open a pull request on the respective repository. This is for the new [Evaluation Results](https://huggingface.co/docs/hub/eval-results) feature released on the hub.

It leverages the [Claude Agents SDK](https://platform.claude.com/docs/en/agent-sdk/overview).

## Installation

The project uses [uv](https://docs.astral.sh/uv/guides/install-python/) to manage Python dependencies. Install the project like so:

```bash
uv add evaluation-parsing
```

Add your HF token (with a write permission) as an environment variable:

```bash
HF_TOKEN=...
```

## Usage

Next, you can let Claude parse the model card of a given repository and potentially open a pull request like so:

```bash
uv run --env-file keys.env main.py --repo_id zai-org/GLM-4.7 --open_pr
```

