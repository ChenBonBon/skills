import json
import os
from typing import Any, Dict, List, Optional

try:
    from task_outputs import create_task_output_dir, safe_stem, task_dir_path
except ImportError:
    from .task_outputs import create_task_output_dir, safe_stem, task_dir_path


def prepare_batch_manifest(
    groups: List[Dict[str, Any]],
    result_root: Optional[str] = None,
    batch_stem: Optional[str] = None,
    batch_dir: Optional[str] = None,
    timestamp: Optional[str] = None,
    username: Optional[str] = None,
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a batch manifest for multi-file financial statement extraction.
    A PDF may appear in multiple groups when it contains multiple statement units.

    Each group must contain:
    - group_index: 1-based integer
    - source_files: ordered list of image/PDF file names
    - statement_type: detected statement type, may be empty before mapping

    :param groups: confirmed statement groups in processing order
    :param result_root: workspace result directory, usually workspace/{username}/result
    :param batch_stem: optional stable batch stem
    :param batch_dir: explicit batch directory override
    :param timestamp: optional timestamp shared with the global task output directory
    :return: manifest dict with batch_dir, manifest_path, and normalized groups
    """
    if not isinstance(groups, list) or not groups:
        raise ValueError("groups must be a non-empty list")

    normalized_groups = []
    for fallback_index, group in enumerate(groups, start=1):
        if not isinstance(group, dict):
            raise TypeError("each group must be a JSON object")
        source_files = group.get("source_files")
        if not isinstance(source_files, list) or not source_files:
            raise ValueError("each group must contain a non-empty source_files list")
        if not all(isinstance(name, str) and name.strip() for name in source_files):
            raise ValueError("source_files must contain non-empty file names")

        group_index = group.get("group_index", fallback_index)
        if not isinstance(group_index, int) or group_index < 1:
            raise ValueError("group_index must be a positive integer")

        statement_type = group.get("statement_type", "")
        if statement_type is None:
            statement_type = ""
        if not isinstance(statement_type, str):
            raise ValueError("statement_type must be a string")

        safe_stem(source_files[0])
        normalized_groups.append(
            {
                "group_index": group_index,
                "source_files": source_files,
                "statement_type": statement_type,
                "task_dir": "",
                "file_prefix": f"group_{group_index}_",
                "status": group.get("status", "pending"),
                "standard_table_excel": group.get("standard_table_excel", ""),
                "failure_stage": group.get("failure_stage", ""),
            }
        )

    if batch_stem is None:
        batch_stem = safe_stem(normalized_groups[0]["source_files"][0])
    if batch_dir is None:
        batch_dir = create_task_output_dir(
            normalized_groups[0]["source_files"][0],
            result_root=result_root,
            timestamp=timestamp,
            username=username,
            workspace_root=workspace_root,
        )["task_dir"]
    else:
        batch_dir = task_dir_path(batch_dir)

    os.makedirs(batch_dir, exist_ok=True)
    for group in normalized_groups:
        group["task_dir"] = batch_dir

    manifest = {
        "batch_dir": batch_dir,
        "batch_stem": batch_stem,
        "current_group_index": normalized_groups[0]["group_index"],
        "groups": normalized_groups,
    }
    manifest_path = os.path.join(batch_dir, "batch_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    manifest["manifest_path"] = manifest_path
    return manifest
