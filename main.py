"""
This script is used to extract evaluation results from model cards and open a pull request using the Claude Agent SDK.

Other sources besides model card:
- paper
- Github README
- project page.

Usage:

```bash
uv run --env-file keys.env main.py --repo_id <repo_id> --open_pr
"""

import argparse
import asyncio
import json
from pathlib import Path

import aiofiles
import yaml

from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

# Output directory for evaluation results
OUTPUTS_DIR = Path(__file__).parent / "outputs"

from utils.hf_utils import fetch_huggingface_readme, create_eval_results_pr


async def read_prompt(filename: str) -> str:
    """Read a prompt file from the script directory."""
    filepath = Path(__file__).parent / filename
    async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
        return await f.read()


async def format_user_prompt(repo_id: str) -> str:
    """Format the user prompt with the model card content."""
    model_card_content = await fetch_huggingface_readme(repo_id, repo_type="model")
    if model_card_content is None:
        raise ValueError(f"Model card content not found for repo_id: {repo_id}")
    user_prompt_template = await read_prompt("prompts/user_prompt.md")
    return user_prompt_template.format(repo_id=repo_id, model_card_content=model_card_content)


schema = {
    "type": "object",
    "properties": {
        "evaluation_results": {
            "type": "array",
            "description": "List of evaluation results matching the .eval_results/*.yaml format",
            "items": {
                "type": "object",
                "properties": {
                    "dataset": {
                        "type": "object",
                        "description": "Dataset information",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Required. Hub dataset ID (must be a Benchmark, e.g., 'cais/hle', 'Idavidrein/gpqa', 'TIGER-Lab/MMLU-Pro', 'openai/gsm8k')"
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Optional. Task ID in case there are multiple tasks or leaderboards for this dataset (e.g., 'default', 'diamond' for GPQA)"
                            }
                        },
                        "required": ["id"]
                    },
                    "value": {
                        "type": "number",
                        "description": "Required. The metric value (e.g., accuracy score)"
                    },
                    "source": {
                        "type": "object",
                        "description": "Optional. Source of the evaluation result",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Required if source provided. URL to the source (e.g., Hugging Face model URL)"
                            },
                            "name": {
                                "type": "string",
                                "description": "Optional. Name of the source (e.g., 'Model Card')"
                            }
                        },
                        "required": ["url"]
                    }
                },
                "required": ["dataset", "value"]
            }
        }
    },
    "required": ["evaluation_results"]
}


async def write_output(repo_id: str, evaluation_results: dict):
    """Write evaluation results as YAML files in a folder named after the repo_id.
    
    Each evaluation result is written to a separate YAML file named after the dataset.
    For example, if the dataset ID is 'Idavidrein/gpqa', the file will be 'gpqa.yaml'.
    """
    # Create folder from repo_id (replace / with __)
    folder_name = repo_id.replace("/", "__")
    output_folder = OUTPUTS_DIR / folder_name
    output_folder.mkdir(parents=True, exist_ok=True)
    
    results = evaluation_results.get("evaluation_results", [])
    
    if not results:
        print(f"\nNo evaluation results to write for {repo_id}")
        return
    
    written_files = []
    for result in results:
        # Extract dataset ID to create filename
        dataset_id = result.get("dataset", {}).get("id", "")
        if not dataset_id:
            print(f"Warning: Skipping result with missing dataset ID: {result}")
            continue
        
        # Use the dataset name (part after /) as the filename
        # e.g., 'Idavidrein/gpqa' -> 'gpqa.yaml'
        dataset_name = dataset_id.split("/")[-1].lower()
        filename = f"{dataset_name}.yaml"
        output_path = output_folder / filename
        
        # Convert single result to YAML list format (as expected by .eval_results/*.yaml)
        yaml_content = yaml.dump([result], default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(yaml_content)
        
        written_files.append(output_path)
    
    print(f"\nResults written to {output_folder}/:")
    for filepath in written_files:
        print(f"  - {filepath.name}")


async def open_pull_request(repo_id: str, evaluation_results: dict | None) -> str | None:
    """Open a pull request with evaluation results to the model repository.
    
    Args:
        repo_id: The Hugging Face model repository ID (e.g., "username/model-name")
        evaluation_results: Dictionary containing evaluation results
        
    Returns:
        The URL of the created pull request, or None if no PR was created
    """
    if not evaluation_results:
        print("\nNo evaluation results to submit as PR")
        return None
    
    results = evaluation_results.get("evaluation_results", [])
    if not results:
        print("\nNo evaluation results to submit as PR")
        return None
    
    print(f"\nOpening pull request for {repo_id}...")
    try:
        pr_url = await create_eval_results_pr(
            repo_id=repo_id,
            evaluation_results=evaluation_results,
            repo_type="model",
        )
        return pr_url
    except Exception as e:
        print(f"Failed to create pull request: {e}")
        return None


async def main(repo_id: str, open_pr: bool = False):
    """Main function to extract evaluation results from model cards."""

    # Format the user prompt
    user_prompt = await format_user_prompt(repo_id=repo_id)
    
    settings_path = Path(__file__).parent / ".claude" / "settings.json"
    options = ClaudeAgentOptions(
        system_prompt={"type": "preset", "preset": "claude_code"},
        permission_mode="bypassPermissions",
        settings=str(settings_path),
        setting_sources=["project"],
        output_format={
            "type": "json_schema",
            "schema": schema
        }
    )
    
    message_count = 0
    subagent_names = {}
    evaluation_results = None
    try:
        async for message in query(
            prompt=user_prompt,
            options=options,
        ):
            message_count += 1
            if isinstance(message, AssistantMessage):
                # Determine which agent is making this call
                if message.parent_tool_use_id is None:
                    agent_prefix = "[main]"
                else:
                    subagent_name = subagent_names.get(
                        message.parent_tool_use_id, "subagent"
                    )
                    agent_prefix = f"[{subagent_name}]"

                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"{agent_prefix} Claude: {block.text}")
                    elif isinstance(block, ToolUseBlock):
                        print(f"{agent_prefix} Tool: {block.name}({block.input})")
                        # Track Task tool calls to map subagent names
                        if block.name == "Task" and isinstance(block.input, dict):
                            subagent_type = block.input.get("subagent_type", "subagent")
                            subagent_names[block.id] = subagent_type
                        # Capture structured output
                        if block.name == "StructuredOutput" and isinstance(block.input, dict):
                            evaluation_results = block.input
            elif (
                isinstance(message, ResultMessage)
                and message.total_cost_usd
                and message.total_cost_usd > 0
            ):
                print(f"\nCost: ${message.total_cost_usd:.4f}")
    except Exception as e:
        print(f"Error during agent query: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    print(f"\nAgent query completed. Total messages received: {message_count}")
    
    # Write results to output file
    if evaluation_results:
        await write_output(repo_id, evaluation_results)

    # Open a pull request with the evaluation results
    if open_pr:
        await open_pull_request(repo_id, evaluation_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo_id", type=str, required=True)
    parser.add_argument("--open_pr", action="store_true", required=False)
    args = parser.parse_args()
    asyncio.run(main(args.repo_id, args.open_pr))