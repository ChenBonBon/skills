from typing import Any, Dict, Iterable, List, Optional, Set


def _unwrap_standard_table(standard_table_json: Dict[str, Any]) -> Dict[str, Any]:
    standard_table = standard_table_json.get("standard_table")
    if isinstance(standard_table, dict):
        return standard_table
    return standard_table_json


def diff_standard_tables(
    standard_table_v1: Dict[str, Any], standard_table_v2: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare two converted standard tables and return subjects whose values differ.

    Each input can be either the bare standard table or the full
    convert_to_standard_table return object.
    """
    table_v1 = _unwrap_standard_table(standard_table_v1)
    table_v2 = _unwrap_standard_table(standard_table_v2)
    if not isinstance(table_v1, dict) or not isinstance(table_v2, dict):
        raise TypeError("standard table inputs must be JSON objects")

    diffs = []
    for subject in sorted(set(table_v1) | set(table_v2)):
        value_v1 = table_v1.get(subject)
        value_v2 = table_v2.get(subject)
        if value_v1 != value_v2:
            diffs.append(
                {
                    "standard_subject": subject,
                    "standard_table_v1": value_v1,
                    "standard_table_v2": value_v2,
                }
            )
    return diffs


def select_remap_subjects(
    subject_mapping_v1: Dict[str, str],
    subject_mapping_v2: Dict[str, str],
    standard_table_diffs: List[Dict[str, Any]],
) -> List[str]:
    """
    Select original subjects that should be remapped for v3.

    A subject is selected when its v1/v2 target differs, or when either target
    contributes to a standard-table subject that changed between v1 and v2.
    """
    if set(subject_mapping_v1) != set(subject_mapping_v2):
        missing = sorted(set(subject_mapping_v1) - set(subject_mapping_v2))
        extra = sorted(set(subject_mapping_v2) - set(subject_mapping_v1))
        raise ValueError(f"subject_mapping key mismatch; missing={missing}; extra={extra}")

    changed_standard_subjects: Set[str] = {
        diff["standard_subject"]
        for diff in standard_table_diffs
        if isinstance(diff, dict) and isinstance(diff.get("standard_subject"), str)
    }

    remap_subjects = []
    for original_subject in subject_mapping_v1:
        target_v1 = subject_mapping_v1[original_subject]
        target_v2 = subject_mapping_v2[original_subject]
        if (
            target_v1 != target_v2
            or target_v1 in changed_standard_subjects
            or target_v2 in changed_standard_subjects
        ):
            remap_subjects.append(original_subject)
    return remap_subjects


def analyze_mapping_retry(
    standard_table_v1: Dict[str, Any],
    standard_table_v2: Dict[str, Any],
    subject_mapping_v1: Dict[str, str],
    subject_mapping_v2: Dict[str, str],
) -> Dict[str, Any]:
    """
    Return standard-table diffs and original subjects that need v3 remapping.
    """
    standard_table_diffs = diff_standard_tables(standard_table_v1, standard_table_v2)
    return {
        "standard_table_diffs": standard_table_diffs,
        "remap_original_subjects": select_remap_subjects(
            subject_mapping_v1, subject_mapping_v2, standard_table_diffs
        ),
    }


def merge_subject_mapping(
    base_subject_mapping: Dict[str, str],
    partial_remap: Dict[str, str],
    expected_subjects: Optional[Iterable[str]] = None,
) -> Dict[str, str]:
    """
    Merge a partial remap into the v1 full mapping to produce subject_mapping_v3.
    """
    merged = dict(base_subject_mapping)
    if expected_subjects is not None:
        expected_keys = set(expected_subjects)
        actual_keys = set(partial_remap)
        if actual_keys != expected_keys:
            missing = sorted(expected_keys - actual_keys)
            extra = sorted(actual_keys - expected_keys)
            raise ValueError(f"partial_remap keys mismatch; missing={missing}; extra={extra}")

    unknown_keys = sorted(set(partial_remap) - set(base_subject_mapping))
    if unknown_keys:
        raise ValueError(f"partial_remap contains unknown subjects: {unknown_keys}")

    for original_subject, standard_subject in partial_remap.items():
        if not isinstance(standard_subject, str) or not standard_subject.strip():
            raise ValueError(
                f"partial_remap value for {original_subject!r} must be a non-empty string"
            )
        merged[original_subject] = standard_subject
    return merged
