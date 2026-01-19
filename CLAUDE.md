# Task

Your task is to extract evaluation results from a Hugging Face model repository based on the model card (README), if any, and provide content for pull requests to be opened on the model repository. These pull requests contain community-provided evaluation results.

# Community-provided evaluation results

A new (beta) feature on the Hugging Face hub (hf.co) is the ability for HF users to submit evaluation results of machine learning models on machine learning datasets which serve as benchmarks. Benchmark datasets host leaderboards, and model repos store evaluation scores that automatically appear on both the model page and the benchmark's leaderboard.

## Benchmark Datasets

Dataset repos on Hugging Face can be defined as **Benchmarks** (e.g., [HLE](https://huggingface.co/datasets/cais/hle), [GPQA](https://huggingface.co/datasets/Idavidrein/gpqa)). These display a "Benchmark" tag and automatically aggregate evaluation results from model repos across the Hub and display a leaderboard of top models.

### Registering a Benchmark

To register your dataset as a benchmark:

1. Create a dataset repo containing your evaluation data
2. Add an `eval.yaml` file to the repo root with your [benchmark configuration](https://inspect.aisi.org.uk/tasks.html#hugging-face)
3. The file is validated at push time
4. (**Beta**) Get in touch so we can add it to the allow-list.

The `eval.yaml` format is based on [Inspect AI](https://inspect.aisi.org.uk/), enabling reproducible evaluations. See the [Evaluating models with Inspect](https://huggingface.co/docs/inference-providers/guides/evaluation-inspect-ai) guide for details on running evaluations.

Examples can be found in these benchmarks: [SimpleQA](https://huggingface.co/datasets/OpenEvals/SimpleQA/blob/main/eval.yaml), [AIME 24](https://huggingface.co/datasets/OpenEvals/aime_24/blob/main/eval.yaml), [MuSR](https://huggingface.co/datasets/OpenEvals/MuSR/blob/main/eval.yaml)

## Model Evaluation Results

Evaluation scores are stored in model repos as YAML files in the `.eval_results/` folder. These results:

- Appear on the model page with links to the benchmark leaderboard
- Are aggregated into the benchmark dataset's leaderboards
- Can be submitted via PRs and marked as "community-provided"

Each result is stored in a separate file in that folder, e.g. `.eval_results/gpqa.yaml`, `.eval_results/mmlu_pro.yaml`, and so on.

### Adding Evaluation Results

To add evaluation results to a model, you can submit a PR to the model repo with a YAML file in the `.eval_results/` folder.

Create a YAML file in `.eval_results/*.yaml` in your model repo:

```yaml
- dataset:
    id: cais/hle                  # Required. Hub dataset ID (must be a Benchmark)
    task_id: default              # Optional, in case there are multiple tasks or leaderboards for this dataset.
  value: 20.90                    # Required. Metric value
  source:                         # Optional. For now this can only be a Hugging Face model URL
    url: https://huggingface.co/zai-org/GLM-4.7  # Required if source provided
    name: Model Card
```

### Supported datasets

Currently, only 4 datasets serve as benchmarks:

| Benchmark | Hub Dataset ID |
|-----------|---------------|
| HLE | [cais/hle](https://huggingface.co/datasets/cais/hle) |
| GPQA | [Idavidrein/gpqa](https://huggingface.co/datasets/Idavidrein/gpqa) |
| MMLU-Pro | [TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro) |
| GSM8K | [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k) |

Hence it only makes sense to extract evaluation results that reference one of these datasets.

## Submitting a pull request

Anyone can submit evaluation results to any model via a Pull Request:

1. Open a pull request using the `huggingface_hub` library.
3. Add a `.eval_results/*.yaml` file with your results.
4. The PR will show as "community-provided" on the model page while open.

For help evaluating a model, see the [Evaluating models with Inspect](https://huggingface.co/docs/inference-providers/guides/evaluation-inspect-ai) guide.

## Output format

Someone else is going to open pull requests, you only need to provide the contents.
Format your result to match the `.eval_results/*.yaml` structure. The JSON output should follow this schema (based on [zai-org/GLM-4.7](https://huggingface.co/zai-org/GLM-4.7)):

```json
{
  "evaluation_results": [
    {
      "dataset": {
        "id": "Idavidrein/gpqa",   // Required. Hub dataset ID (must be one of the supported benchmarks)
        "task_id": "diamond"       // Optional. Task ID for datasets with multiple tasks/leaderboards
      },
      "value": 85.7,               // Required. The metric value
      "source": {                  // Required. Source of the evaluation result
        "url": "https://huggingface.co/zai-org/GLM-4.7",  // Required. URL of the source, which is simply the URL of the model
        "name": "Model Card"       // Required. Name of the source. For now, only Model Card is supported.
      }
    }
  ]
}
```

This corresponds to the YAML format stored in `.eval_results/*.yaml`:

```yaml
- dataset:
    id: Idavidrein/gpqa
    task_id: diamond
  value: 85.7
  source:
    url: https://huggingface.co/zai-org/GLM-4.7
    name: Model Card
```

## Rules

Return an empty list in case you didn't find any evaluation results.
Only return evaluation results for which you are 100% certain that they accurately represent results presented in the model card, of the specific model on one of the supported benchmarks. The benchmark dataset names need to be explicitly mentioned, do not assume equivalent names.
In case the model card contains multiple evaluation results on the same benchmark, return the highest score.