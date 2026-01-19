"""
Utility functions for interacting with the Hugging Face hub.
"""

import asyncio
import os
from pathlib import Path
from typing import Literal

import yaml
from huggingface_hub import hf_hub_download, create_commit, list_repo_files, HfApi
from huggingface_hub.hf_api import CommitOperationAdd
from huggingface_hub.errors import HfHubHTTPError

RepoType = Literal["model", "dataset"]


async def get_existing_eval_results(
    repo_id: str, repo_type: RepoType = "model"
) -> dict[str, dict]:
    """
    Get existing evaluation results from a repository.
    
    Checks both the main branch and open PRs for existing `.eval_results/*.yaml` files.
    
    Args:
        repo_id: The repository ID (e.g., "nvidia/Nemotron-Orchestrator-8B")
        repo_type: The type of repository ("model", "dataset")
        
    Returns:
        A dictionary mapping benchmark dataset IDs to their existing results info:
        {
            "cais/hle": {
                "source": "main" | "pr",
                "pr_num": <int> | None,  # PR number if source is "pr"
                "value": <float>,
                "file_path": ".eval_results/hle.yaml"
            },
            ...
        }
    """
    existing_results: dict[str, dict] = {}
    
    # Check main branch for existing eval results
    try:
        files = await asyncio.to_thread(
            list_repo_files, repo_id=repo_id, repo_type=repo_type
        )
        eval_files = [f for f in files if f.startswith(".eval_results/") and f.endswith(".yaml")]
        
        for eval_file in eval_files:
            try:
                file_path = await asyncio.to_thread(
                    hf_hub_download,
                    repo_id=repo_id,
                    filename=eval_file,
                    repo_type=repo_type,
                )
                
                def read_yaml():
                    with open(file_path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f)
                
                content = await asyncio.to_thread(read_yaml)
                
                if isinstance(content, list) and content:
                    for result in content:
                        dataset_id = result.get("dataset", {}).get("id")
                        if dataset_id:
                            existing_results[dataset_id] = {
                                "source": "main",
                                "pr_num": None,
                                "value": result.get("value"),
                                "file_path": eval_file,
                            }
            except Exception as e:
                print(f"Warning: Could not read {eval_file} from main branch: {e}")
    except Exception as e:
        print(f"Warning: Could not list files from {repo_id}: {e}")
    
    # Check open PRs for eval results
    try:
        api = HfApi()
        discussions = await asyncio.to_thread(
            lambda: list(api.get_repo_discussions(repo_id=repo_id, repo_type=repo_type))
        )
        
        open_prs = [d for d in discussions if d.is_pull_request and d.status == "open"]
        
        for pr in open_prs:
            try:
                # List files in PR branch
                pr_files = await asyncio.to_thread(
                    list_repo_files,
                    repo_id=repo_id,
                    repo_type=repo_type,
                    revision=f"refs/pr/{pr.num}",
                )
                pr_eval_files = [f for f in pr_files if f.startswith(".eval_results/") and f.endswith(".yaml")]
                
                for eval_file in pr_eval_files:
                    # Skip if already found in main branch
                    benchmark_name = eval_file.replace(".eval_results/", "").replace(".yaml", "")
                    
                    try:
                        file_path = await asyncio.to_thread(
                            hf_hub_download,
                            repo_id=repo_id,
                            filename=eval_file,
                            repo_type=repo_type,
                            revision=f"refs/pr/{pr.num}",
                        )
                        
                        def read_yaml():
                            with open(file_path, "r", encoding="utf-8") as f:
                                return yaml.safe_load(f)
                        
                        content = await asyncio.to_thread(read_yaml)
                        
                        if isinstance(content, list) and content:
                            for result in content:
                                dataset_id = result.get("dataset", {}).get("id")
                                if dataset_id and dataset_id not in existing_results:
                                    existing_results[dataset_id] = {
                                        "source": "pr",
                                        "pr_num": pr.num,
                                        "value": result.get("value"),
                                        "file_path": eval_file,
                                    }
                    except Exception as e:
                        print(f"Warning: Could not read {eval_file} from PR #{pr.num}: {e}")
            except Exception as e:
                print(f"Warning: Could not check PR #{pr.num}: {e}")
    except Exception as e:
        print(f"Warning: Could not list PRs for {repo_id}: {e}")
    
    return existing_results


async def fetch_huggingface_readme(
    repo_id: str, repo_type: RepoType = "model"
) -> str | None:
    """Fetch README content from a Hugging Face repository asynchronously."""
    try:
        filepath = await asyncio.to_thread(
            hf_hub_download,
            repo_id=repo_id,
            filename="README.md",
            repo_type=repo_type,
        )
    except HfHubHTTPError as e:
        status_code = e.response.status_code
        if status_code == 404:
            print(f"README.md not found for {repo_id} ({repo_type}): 404")
        else:
            print(f"HTTP error downloading README for {repo_id} ({repo_type}): {status_code}")
        return None
    except Exception as e:
        print(f"Error downloading README for {repo_id} ({repo_type}): {e}")
        return None

    try:
        def read_file() -> str:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()

        return await asyncio.to_thread(read_file)
    except Exception as e:
        print(f"Error reading README file {filepath} for {repo_id} ({repo_type}): {e}")
        return None


async def create_eval_results_pr(
    repo_id: str,
    evaluation_results: dict,
    repo_type: str = "model",
    skip_existing: bool = True,
) -> str | None:
    """
    Create a pull request to add evaluation results to a model repository on the Hugging Face Hub.

    The evaluation results are submitted as YAML files in the `.eval_results/` folder.
    Each benchmark result is stored in a separate file (e.g., `.eval_results/gpqa.yaml`).

    Args:
        repo_id (str): The full repository ID (e.g., "username/repo_name")
        evaluation_results (dict): Dictionary containing evaluation results with structure:
            {
                "evaluation_results": [
                    {
                        "dataset": {"id": "...", "task_id": "..."},
                        "value": ...,
                        "source": {"url": "...", "name": "..."}
                    },
                    ...
                ]
            }
        repo_type (str): Either 'model' or 'dataset' or 'space'
        skip_existing (bool): If True, skip benchmarks that already have results 
            (either in main branch or in open PRs). Default: True

    Returns:
        str | None: The URL of the created pull request, or None if no results to submit
    """
    results = evaluation_results.get("evaluation_results", [])
    
    if not results:
        print(f"No evaluation results to submit for {repo_id}")
        return None
    
    # Check for existing evaluation results
    if skip_existing:
        existing_results = await get_existing_eval_results(repo_id, repo_type)
        
        if existing_results:
            print(f"Found existing evaluation results for {repo_id}:")
            for dataset_id, info in existing_results.items():
                source_desc = f"main branch" if info["source"] == "main" else f"open PR #{info['pr_num']}"
                print(f"  - {dataset_id}: {info['value']} ({source_desc})")
        
        # Filter out results for benchmarks that already exist
        original_count = len(results)
        results = [
            r for r in results 
            if r.get("dataset", {}).get("id") not in existing_results
        ]
        
        skipped_count = original_count - len(results)
        if skipped_count > 0:
            print(f"Skipping {skipped_count} benchmark(s) with existing results")
        
        if not results:
            print(f"All evaluation results already exist for {repo_id}, skipping PR creation")
            return None

    # Create temporary directory for YAML files
    sanitized_repo_id = repo_id.replace("/", "_").replace("\\", "_")
    temp_dir = Path(__file__).parent.parent / "outputs" / f"temp_{sanitized_repo_id}"
    await asyncio.to_thread(os.makedirs, temp_dir, exist_ok=True)

    temp_files = []
    operations = []
    benchmark_names = []
    benchmark_ids = []

    try:
        # Create YAML files for each evaluation result
        for result in results:
            dataset_id = result.get("dataset", {}).get("id", "")
            if not dataset_id:
                print(f"Warning: Skipping result with missing dataset ID: {result}")
                continue

            # Use the dataset name (part after /) as the filename
            # e.g., 'Idavidrein/gpqa' -> 'gpqa.yaml'
            dataset_name = dataset_id.split("/")[-1].lower()
            filename = f"{dataset_name}.yaml"
            temp_path = temp_dir / filename
            
            # Convert single result to YAML list format (as expected by .eval_results/*.yaml)
            yaml_content = yaml.dump(
                [result], 
                default_flow_style=False, 
                allow_unicode=True, 
                sort_keys=False
            )
            
            # Write temp file
            def write_yaml():
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)
            
            await asyncio.to_thread(write_yaml)
            temp_files.append(temp_path)
            benchmark_names.append(dataset_name.upper())
            benchmark_ids.append(dataset_id)
            
            # Create commit operation for this file
            operations.append(
                CommitOperationAdd(
                    path_in_repo=f".eval_results/{filename}",
                    path_or_fileobj=str(temp_path),
                )
            )

        if not operations:
            print(f"No valid evaluation results to submit for {repo_id}")
            return None

        # Create PR title and description
        benchmarks_str = ", ".join(benchmark_names)
        title = f"Add community evaluation results for {benchmarks_str}"
        description = (
            f"This PR adds community-provided evaluation results for the following benchmarks:\n\n"
            f"- {chr(10).join(f'**[{name}](https://huggingface.co/datasets/{id})**' for name, id in zip(benchmark_names, benchmark_ids))}\n\n"
            f"These results were extracted from the model card. This is based on the new [evaluation results feature](https://huggingface.co/docs/hub/eval-results)."
            f"*Note: This is an automated PR. Please review the evaluation results before merging.*"
        )

        # Create the commit with PR
        commit_info = await asyncio.to_thread(
            create_commit,
            repo_id=repo_id,
            operations=operations,
            commit_message=title,
            commit_description=description,
            create_pr=True,
            repo_type=repo_type,
        )
        
        pr_url = commit_info.pr_url
        print(f"PR created successfully at {repo_id}: {pr_url}")
        return pr_url

    except Exception as e:
        print(f"Error creating PR for {repo_id}: {e}")
        raise
    finally:
        # Clean up temporary files
        for temp_path in temp_files:
            try:
                await asyncio.to_thread(os.remove, temp_path)
            except OSError:
                pass
        # Remove temp directory if empty
        try:
            await asyncio.to_thread(os.rmdir, temp_dir)
        except OSError:
            pass