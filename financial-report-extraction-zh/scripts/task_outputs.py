import json
import os
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
