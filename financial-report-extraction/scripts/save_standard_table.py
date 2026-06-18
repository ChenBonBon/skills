import json
import math
import os
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

try:
    from task_outputs import task_dir_path
except ImportError:
    from .task_outputs import task_dir_path


def _validate_amount(value: Any, path: str) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        raise ValueError(f"{path} must be a number, numeric string, empty string, or null")
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must not be NaN or Infinity")
        return
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return
        try:
            Decimal(stripped.replace(",", ""))
        except InvalidOperation as exc:
            raise ValueError(f"{path} must be numeric when non-empty") from exc
        return
    raise ValueError(f"{path} must be a number, numeric string, empty string, or null")


def _validate_rpt_type(rpt_type: Any) -> None:
    if isinstance(rpt_type, bool) or not isinstance(rpt_type, int) or rpt_type not in {1, 2, 3}:
        raise ValueError("rpt_type must be one of 1, 2, or 3")


def _validate_standard_table_body(standard_table: Any) -> None:
    if not isinstance(standard_table, dict) or not standard_table:
        raise ValueError("standard_table must be a non-empty JSON object")

    for subject, columns in standard_table.items():
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("standard_table subject keys must be non-empty strings")
        subject_path = f"standard_table[{subject!r}]"
        if not isinstance(columns, dict) or not columns:
            raise ValueError(f"{subject_path} must be a non-empty JSON object")
        for column, amount in columns.items():
            if not isinstance(column, str) or not column.strip():
                raise ValueError(f"{subject_path} column keys must be non-empty strings")
            _validate_amount(amount, f"{subject_path}[{column!r}]")


def _write_standard_table_file(
    standard_table_json: Dict[str, Any], task_dir: Any, file_prefix: str
) -> str:
    task_dir = task_dir_path(task_dir)
    if not isinstance(file_prefix, str):
        raise TypeError("file_prefix must be a string")

    os.makedirs(task_dir, exist_ok=True)
    standard_table_path = os.path.join(task_dir, f"{file_prefix}standard_table.json")
    with open(standard_table_path, "w", encoding="utf-8") as f:
        json.dump(
            standard_table_json,
            f,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    saved_json = validate_standard_table_file(standard_table_path)
    if saved_json != standard_table_json:
        raise ValueError("saved standard_table.json differs from standard table JSON object")
    return standard_table_path


def validate_standard_table_object(
    standard_table_json: Dict[str, Any], expected_rpt_type: Any = None
) -> None:
    """
    Validate the saved standard table wrapper expected by downstream tools.

    Required shape:
    {"rpt_type": 2, "standard_table": {"standard_subject": {"period": 123.45}}}
    """
    if not isinstance(standard_table_json, dict):
        raise TypeError("standard_table_json must be a JSON object")
    if "rpt_type" not in standard_table_json:
        raise ValueError("standard_table_json must contain rpt_type")
    if "standard_table" not in standard_table_json:
        raise ValueError("standard_table_json must contain standard_table")

    rpt_type = standard_table_json["rpt_type"]
    _validate_rpt_type(rpt_type)
    if expected_rpt_type is not None:
        _validate_rpt_type(expected_rpt_type)
        if rpt_type != expected_rpt_type:
            raise ValueError("rpt_type does not match expected_rpt_type")

    _validate_standard_table_body(standard_table_json["standard_table"])


def build_repaired_standard_table_object(
    standard_table_json: Dict[str, Any], rpt_type: int
) -> Dict[str, Any]:
    """
    Build a valid standard-table wrapper from deterministic malformed shapes.

    This repairs only wrapper mistakes, such as a missing/invalid rpt_type or a bare
    standard_table body. It never rewrites subject names, columns, or amounts.
    """
    _validate_rpt_type(rpt_type)
    if not isinstance(standard_table_json, dict):
        raise TypeError("standard_table_json must be a JSON object")

    try:
        validate_standard_table_object(standard_table_json, expected_rpt_type=rpt_type)
        return standard_table_json
    except (TypeError, ValueError):
        pass

    if isinstance(standard_table_json.get("standard_table"), dict):
        repaired = {
            "rpt_type": rpt_type,
            "standard_table": standard_table_json["standard_table"],
        }
    else:
        table_body = {
            key: value for key, value in standard_table_json.items() if key != "rpt_type"
        }
        repaired = {"rpt_type": rpt_type, "standard_table": table_body}

    validate_standard_table_object(repaired)
    return repaired


def validate_standard_table_file(
    standard_table_path: str, expected_rpt_type: Any = None
) -> Dict[str, Any]:
    """
    Load standard_table.json and validate that it is JSON with the required wrapper shape.
    """
    if not isinstance(standard_table_path, str):
        raise TypeError("standard_table_path must be a string")
    with open(standard_table_path, "r", encoding="utf-8") as f:
        saved_json = json.load(f)
    validate_standard_table_object(saved_json, expected_rpt_type=expected_rpt_type)
    return saved_json


def save_standard_table(
    standard_table_json: Dict[str, Any],
    task_dir: Any,
    file_prefix: str = "",
    expected_rpt_type: Any = None,
) -> str:
    """
    Save the JSON object returned by convert_to_standard_table unchanged.

    :param standard_table_json: JSON object returned by convert_to_standard_table
    :param task_dir: task output directory, usually workspace/{username}/result/{original_filename_stem}_{timestamp}
    :param file_prefix: optional file prefix for multi-statement batches
    :param expected_rpt_type: optional report type used in convert_to_standard_table
    :return: path to standard_table.json
    """
    validate_standard_table_object(
        standard_table_json, expected_rpt_type=expected_rpt_type
    )
    return _write_standard_table_file(standard_table_json, task_dir, file_prefix)


def save_repaired_standard_table(
    standard_table_json: Dict[str, Any],
    rpt_type: int,
    task_dir: Any,
    file_prefix: str = "",
) -> str:
    """
    Save a corrected standard_table.json after unchanged save attempts fail.

    :param standard_table_json: malformed JSON object returned by convert_to_standard_table
    :param rpt_type: report type used in convert_to_standard_table
    :param task_dir: task output directory
    :param file_prefix: optional file prefix for multi-statement batches
    :return: path to standard_table.json
    """
    repaired = build_repaired_standard_table_object(standard_table_json, rpt_type)
    return _write_standard_table_file(repaired, task_dir, file_prefix)
