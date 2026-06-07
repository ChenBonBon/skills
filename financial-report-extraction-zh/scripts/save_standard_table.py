import json
import os
from typing import Any, Dict


def save_standard_table(standard_table_json: Dict[str, Any], task_dir: str) -> str:
    """
    Save the standard table JSON returned by convert_to_standard_table.

    :param standard_table_json: JSON object returned by convert_to_standard_table
    :param task_dir: task output directory, usually workspace/{username}/result/{original_filename_stem}
    :return: path to standard_table.json
    """
    if not isinstance(standard_table_json, dict):
        raise TypeError("standard_table_json must be a JSON object")
    if not task_dir:
        raise ValueError("task_dir must be non-empty")

    os.makedirs(task_dir, exist_ok=True)
    standard_table_path = os.path.join(task_dir, "standard_table.json")
    with open(standard_table_path, "w", encoding="utf-8") as f:
        json.dump(standard_table_json, f, ensure_ascii=False, separators=(",", ":"))
    return standard_table_path
