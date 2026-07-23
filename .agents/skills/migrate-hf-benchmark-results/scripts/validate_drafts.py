#!/usr/bin/env python3
# /// script
# dependencies = ["pyyaml>=6.0"]
# ///
"""Read-only structural validation for local .eval_results YAML drafts."""

from __future__ import annotations

import argparse
import datetime as dt
import math
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Review bundle containing drafts/")
    parser.add_argument("--benchmark-id", required=True, help="Exact benchmark dataset ID")
    parser.add_argument(
        "--task-id",
        action="append",
        required=True,
        dest="task_ids",
        help="Allowed task ID; repeat for multiple tasks",
    )
    return parser.parse_args()


def validate_date(value: object) -> bool:
    if isinstance(value, (dt.date, dt.datetime)):
        return True
    if not isinstance(value, str):
        return False
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt.date.fromisoformat(value)
        except ValueError:
            return False
    return True


def validate_file(path: Path, benchmark_id: str, task_ids: set[str]) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # surface parser and I/O errors uniformly
        return [f"cannot parse YAML: {exc}"]

    if not isinstance(data, list) or not data:
        return ["root must be a non-empty YAML list"]

    seen: set[tuple[str, str]] = set()
    for index, result in enumerate(data, start=1):
        prefix = f"entry {index}"
        if not isinstance(result, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue
        dataset = result.get("dataset")
        if not isinstance(dataset, dict):
            errors.append(f"{prefix}: dataset must be a mapping")
            continue
        dataset_id = dataset.get("id")
        task_id = dataset.get("task_id")
        if dataset_id != benchmark_id:
            errors.append(f"{prefix}: dataset.id must equal {benchmark_id!r}")
        if not isinstance(task_id, str) or task_id not in task_ids:
            errors.append(f"{prefix}: task_id {task_id!r} is not in {sorted(task_ids)!r}")
        key = (str(dataset_id), str(task_id))
        if key in seen:
            errors.append(f"{prefix}: duplicate dataset/task pair {key!r}")
        seen.add(key)

        value = result.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{prefix}: value must be numeric")
        elif not math.isfinite(float(value)):
            errors.append(f"{prefix}: value must be finite")

        if "date" in result and not validate_date(result["date"]):
            errors.append(f"{prefix}: date must be ISO-8601")

        source = result.get("source")
        if source is not None:
            if not isinstance(source, dict):
                errors.append(f"{prefix}: source must be a mapping")
            else:
                url = source.get("url")
                parsed = urlparse(url) if isinstance(url, str) else None
                if not parsed or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    errors.append(f"{prefix}: source.url must be an absolute HTTP(S) URL")

    return errors


def main() -> int:
    args = parse_args()
    drafts = args.bundle / "drafts"
    if not drafts.is_dir():
        print(f"ERROR: drafts directory not found: {drafts}")
        return 1

    files = sorted(
        path
        for path in drafts.rglob("*.yaml")
        if path.parent.name == ".eval_results"
    )
    if not files:
        print(f"ERROR: no drafts/**/.eval_results/*.yaml files found under {args.bundle}")
        return 1

    failed = False
    for path in files:
        errors = validate_file(path, args.benchmark_id, set(args.task_ids))
        relative = path.relative_to(args.bundle)
        if errors:
            failed = True
            print(f"FAIL {relative}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {relative}")

    print(f"Checked {len(files)} draft file(s); status={'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
