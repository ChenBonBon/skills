import json
import os
from typing import Any, Dict


def _extract_standard_table(convert_result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the standard_table payload from a convert_to_standard_table result."""
    standard_table = convert_result.get("standard_table")
    if isinstance(standard_table, dict):
        return standard_table
    return convert_result


def save_standard_table(
    standard_table_json: Dict[str, Any], task_dir: str, file_prefix: str = ""
) -> str:
    """
    Save the standard table JSON returned by convert_to_standard_table.

    If convert_to_standard_table returns {"rpt_type": ..., "standard_table": {...}},
    only the value of "standard_table" is persisted.

    :param standard_table_json: JSON object returned by convert_to_standard_table, or an already extracted standard table
    :param task_dir: task output directory, usually workspace/{username}/result/{original_filename_stem}_{timestamp}
    :param file_prefix: optional file prefix for multi-statement batches
    :return: path to standard_table.json
    """
    if not isinstance(standard_table_json, dict):
        raise TypeError("standard_table_json must be a JSON object")
    if not task_dir:
        raise ValueError("task_dir must be non-empty")
    if not isinstance(file_prefix, str):
        raise TypeError("file_prefix must be a string")

    os.makedirs(task_dir, exist_ok=True)
    standard_table_path = os.path.join(task_dir, f"{file_prefix}standard_table.json")
    standard_table_payload = _extract_standard_table(standard_table_json)
    with open(standard_table_path, "w", encoding="utf-8") as f:
        json.dump(standard_table_payload, f, ensure_ascii=False, separators=(",", ":"))
    return standard_table_path
