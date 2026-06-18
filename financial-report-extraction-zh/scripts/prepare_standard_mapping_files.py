import json
import os
from typing import Any, Dict, Iterable, Optional, Set

try:
    from task_outputs import create_task_output_dir, safe_stem, task_dir_path
except ImportError:
    from .task_outputs import create_task_output_dir, safe_stem, task_dir_path


def _resolve_task_dir(
    original_filename: str,
    result_root: Optional[str] = None,
    task_dir: Optional[str] = None,
    username: Optional[str] = None,
    workspace_root: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> str:
    if task_dir:
        return task_dir_path(task_dir)
    return create_task_output_dir(
        original_filename,
        result_root=result_root,
        username=username,
        workspace_root=workspace_root,
        timestamp=timestamp,
    )["task_dir"]


def _extract_subjects(validated_json: Dict[str, Any]) -> Set[str]:
    table_data = validated_json.get("表格数据")
    if not isinstance(table_data, list):
        raise ValueError("validated_json must contain 表格数据 list")

    subjects = []
    for row in table_data:
        if not isinstance(row, dict):
            raise ValueError("each 表格数据 row must be a JSON object")
        subject = row.get("科目名称")
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("each 表格数据 row must contain a non-empty 科目名称")
        if subject not in subjects:
            subjects.append(subject)
    return set(subjects)


def _validate_subject_mapping(
    validated_json: Dict[str, Any],
    subject_mapping: Dict[str, str],
    standard_subjects: Optional[Iterable[str]] = None,
) -> None:
    expected_keys = _extract_subjects(validated_json)
    actual_keys = set(subject_mapping.keys())
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise ValueError(f"subject_mapping keys mismatch; missing={missing}; extra={extra}")

    allowed_values = set(standard_subjects) if standard_subjects is not None else None
    if allowed_values is not None:
        allowed_values.add("__IGNORE__")

    for key, value in subject_mapping.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("subject_mapping contains an invalid key")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"subject_mapping value for {key!r} must be a non-empty string")
        if allowed_values is not None and value not in allowed_values:
            raise ValueError(f"subject_mapping value for {key!r} is not a standard subject")


def prepare_standard_mapping_files(
    validated_json: Dict[str, Any],
    subject_mapping: Dict[str, str],
    original_filename: str,
    result_root: Optional[str] = None,
    task_dir: Optional[str] = None,
    standard_subjects: Optional[Iterable[str]] = None,
    file_prefix: str = "",
    username: Optional[str] = None,
    workspace_root: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, str]:
    """
    Write Step 7 input JSON files under one task directory.

    :param validated_json: final original-table JSON after validation passes
    :param subject_mapping: mapping JSON object from original subject to standard subject
    :param original_filename: uploaded source file name used to derive the task directory
    :param result_root: workspace result directory, usually workspace/{username}/result
    :param task_dir: explicit task directory override
    :param standard_subjects: optional iterable of allowed standard subject names
    :param file_prefix: optional file prefix for multi-statement batches
    :param username: optional platform username used to derive workspace/{username}/result
    :param workspace_root: optional workspace root used with username
    :param timestamp: optional timestamp shared with the task output directory
    :return: paths for task_dir, original_validated_json_file_path,
        original_table_json_file_path, subject_mapping_json_file_path
    """
    if not isinstance(validated_json, dict):
        raise TypeError("validated_json must be a JSON object")
    if not isinstance(subject_mapping, dict):
        raise TypeError("subject_mapping must be a JSON object")
    if not isinstance(file_prefix, str):
        raise TypeError("file_prefix must be a string")
    _validate_subject_mapping(validated_json, subject_mapping, standard_subjects)

    safe_stem(original_filename)
    resolved_task_dir = _resolve_task_dir(
        original_filename,
        result_root,
        task_dir,
        username=username,
        workspace_root=workspace_root,
        timestamp=timestamp,
    )
    os.makedirs(resolved_task_dir, exist_ok=True)

    original_path = os.path.join(resolved_task_dir, f"{file_prefix}original_validated.json")
    mapping_path = os.path.join(resolved_task_dir, f"{file_prefix}subject_mapping.json")

    with open(original_path, "w", encoding="utf-8") as f:
        json.dump(validated_json, f, ensure_ascii=False, separators=(",", ":"))

    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(subject_mapping, f, ensure_ascii=False, separators=(",", ":"))

    return {
        "task_dir": resolved_task_dir,
        "original_validated_json_file_path": original_path,
        "original_table_json_file_path": original_path,
        "subject_mapping_json_file_path": mapping_path,
    }
