import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional


PLACEHOLDER_MARKERS = (
    "see original ocr",
    "truncated",
    "omitted",
    "placeholder",
)


def safe_stem(filename: str) -> str:
    stem = os.path.splitext(os.path.basename(filename))[0].strip()
    if not stem:
        raise ValueError("filename must contain a non-empty stem")
    return stem


def current_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_task_output_dir(
    original_filename: str,
    result_root: Optional[str] = None,
    timestamp: Optional[str] = None,
    task_dir: Optional[str] = None,
) -> Dict[str, str]:
    """
    Create or reuse the task output directory for one extraction run.

    Default path:
    workspace/{username}/result/{original_filename_stem}_{yyyyMMdd_HHmmss}
    """
    if task_dir:
        os.makedirs(task_dir, exist_ok=True)
        return {
            "task_dir": task_dir,
            "original_filename_stem": safe_stem(original_filename),
            "timestamp": timestamp or "",
        }

    if result_root is None:
        result_root = os.path.join(os.getcwd(), "result")
    if timestamp is None:
        timestamp = current_timestamp()

    original_filename_stem = safe_stem(original_filename)
    resolved_task_dir = os.path.join(
        result_root, f"{original_filename_stem}_{timestamp}"
    )
    os.makedirs(resolved_task_dir, exist_ok=True)
    return {
        "task_dir": resolved_task_dir,
        "original_filename_stem": original_filename_stem,
        "timestamp": timestamp,
    }


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in PLACEHOLDER_MARKERS)
    if isinstance(value, dict):
        return any(_contains_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    return False


def save_ocr_results(
    raw_ocr_responses: List[Any],
    task_dir: str,
    filename: str = "ocr_results.json",
) -> str:
    """
    Save raw OCR responses exactly as returned by the OCR tool.
    """
    if not isinstance(raw_ocr_responses, list):
        raise TypeError("raw_ocr_responses must be a list")
    if not task_dir:
        raise ValueError("task_dir must be non-empty")
    if _contains_placeholder(raw_ocr_responses):
        raise ValueError("raw_ocr_responses appears summarized or redacted")

    os.makedirs(task_dir, exist_ok=True)
    output_path = os.path.join(task_dir, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(raw_ocr_responses, f, ensure_ascii=False, indent=2)
    return output_path


def ensure_file_in_task_dir(
    source_path: str,
    task_dir: str,
    filename: Optional[str] = None,
) -> str:
    """
    Ensure an externally generated file is available under task_dir.

    If source_path is already inside task_dir, return it unchanged.
    Otherwise copy it into task_dir and return the copied path.
    """
    if not source_path:
        raise ValueError("source_path must be non-empty")
    if not task_dir:
        raise ValueError("task_dir must be non-empty")

    source_abs = os.path.abspath(source_path)
    task_abs = os.path.abspath(task_dir)
    if not os.path.isfile(source_abs):
        raise FileNotFoundError(f"source file does not exist: {source_path}")

    os.makedirs(task_abs, exist_ok=True)
    if os.path.commonpath([source_abs, task_abs]) == task_abs:
        return source_abs

    target_name = filename or os.path.basename(source_abs)
    if not target_name:
        raise ValueError("target filename must be non-empty")
    target_path = os.path.join(task_abs, target_name)
    if os.path.abspath(target_path) != source_abs:
        shutil.copy2(source_abs, target_path)
    return target_path
