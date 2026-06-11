# Standardization Workflow

Use this reference only after original-table JSON is validated or after standard-table validation fails.

## Task Directory

Use the Step 0 task output directory:

```text
workspace/{username}/result/{original_filename_stem}_{yyyyMMdd_HHmmss}/
```

This directory is created once with `scripts/task_outputs.py` before the first file is written. Reuse the remembered `task_dir` for all JSON and Excel outputs in this run. If the exact workspace root is unavailable, use the current runtime context. Do not write production outputs to a temporary directory.

## Subject Mapping

1. Extract the runtime original subject list from `validated_json["表格数据"][].科目名称`.
2. Preserve original order and exact text.
3. Remove duplicate subject names only for mapping prompt input; do not modify `validated_json`.
4. Read exactly one mapping reference based on `表名`.
5. Replace the reference's runtime original-subject placeholder with the actual subject list.
6. Output one JSON object whose keys exactly equal the runtime original subject list and whose values are standard subject names or `__IGNORE__`.

Before writing files, validate that:

- `subject_mapping` is a JSON object.
- Its key set exactly equals the runtime original subject list after duplicate removal.
- It has no missing or extra keys.
- Every key preserves the original subject text exactly.
- Every value is a non-empty string.
- Every value is either a selected reference standard subject or exactly `__IGNORE__`.
- Values are not `null`, arrays, objects, explanations, confidence scores, or combined text.

If validation fails, regenerate once. If it still fails, explain the format failure briefly and stop.

## Prepare Files And Convert

Call `scripts/prepare_standard_mapping_files.py`:

```python
prepare_standard_mapping_files(
    validated_json,
    subject_mapping,
    original_filename,
    result_root=None,
    task_dir=task_dir,
    standard_subjects=None,
    file_prefix="",
)
```

For multi-statement batches, keep the same `task_dir` and pass each group's manifest `file_prefix` such as `group_1_`.

Use returned paths directly for `convert_to_standard_table`:

- `original_table_json_file_path`: returned original-table JSON path
- `subject_mapping_json_file_path`: returned subject-mapping JSON path
- `rpt_type`: `1` for `资产负债表`, `2` for `利润表` / `损益表`, `3` for `现金流量表`

Save the returned standard-table JSON with `scripts/save_standard_table.py` using the same `task_dir` and the same group `file_prefix`, if any. If `convert_to_standard_table` returns an outer object such as `{"rpt_type": ..., "standard_table": {...}}`, persist only the value of `standard_table`.

## Standard-Table Excel Output

When calling `standard_table_to_excel` after validation passes or when the user chooses standard-table Excel viewing:

1. Pass `standard_table_json_file_path`, `rpt_type`, and the remembered `task_dir` as the output directory/path argument if the platform tool supports one.
2. The Excel must end up under the Step 0 task output directory.
3. If the tool returns a file path outside `task_dir`, call `scripts/task_outputs.py` `ensure_file_in_task_dir(source_path, task_dir)` and use the copied path.
4. If the tool returns an invalid or missing path, rerun it with `task_dir` if supported; otherwise stop and report that the standard-table Excel output path is invalid.
5. Store the final in-`task_dir` Excel path in session state and batch summary.

## Validate Standard Table

Call `validate_standard_table` with:

- `standard_table_json_file_path`: path to `standard_table.json`
- `rpt_type`: `1`, `2`, or `3`

Pass/fail detection:

- Prefer explicit fields such as `校验是否通过`, `is_valid`, `passed`, `success`, or `valid`.
- If text clearly says validation passed, treat it as passed.
- Extract abnormal items from fields such as `异常数据`, `异常项`, `errors`, `issues`, `failed_items`, or `details`.
- If the return shape is unclear, show a manual-confirmation table with top-level keys and stop.

## Standard-Mapping Retry Before User Choice

Run this retry flow once per statement group after the first `validate_standard_table` failure, before showing the Standard-Table Failure Response. Do not run it when the first validation passes. Do not loop indefinitely.

Use these artifact meanings:

- `subject_mapping_v1`: the mapping that produced the first failed `standard_table_v1`
- `standard_table_v1`: the first converted standard table
- `subject_mapping_v2`: an independently regenerated full subject mapping
- `standard_table_v2`: the standard table converted from `subject_mapping_v2`
- `subject_mapping_v3`: the final full mapping after remapping only the unstable original subjects
- `standard_table_v3`: the standard table converted from `subject_mapping_v3`

Retry steps:

1. Preserve the first failed mapping/table as `subject_mapping_v1` and `standard_table_v1`. The existing unversioned `subject_mapping.json` and `standard_table.json` are v1; do not overwrite them during retry.
2. Regenerate a full `subject_mapping_v2` from the same validated original-table JSON, runtime original subject list, report type, and mapping reference. Generate it independently; do not copy `subject_mapping_v1`.
3. Save and convert `subject_mapping_v2` with the same `task_dir`; use a versioned file prefix such as `{file_prefix}v2_`.
4. Save the converted result as `standard_table_v2`.
5. Call `scripts/standard_mapping_retry.py` `analyze_mapping_retry(standard_table_v1, standard_table_v2, subject_mapping_v1, subject_mapping_v2)`.
6. If `standard_table_diffs` is empty or `remap_original_subjects` is empty, mapping instability was not found; show the Standard-Table Failure Response based on the latest validation failure.
7. Remap only `remap_original_subjects`. The output must be a partial JSON object whose keys exactly equal `remap_original_subjects` and whose values are valid standard subjects or `__IGNORE__`. Use the full original subject list, the mapping reference, the validation failure details, and the v1/v2 diff report as context.
8. Call `merge_subject_mapping(subject_mapping_v1, partial_remap, remap_original_subjects)` to build `subject_mapping_v3`.
9. Save and convert `subject_mapping_v3` with the same `task_dir`; use a versioned file prefix such as `{file_prefix}v3_`.
10. Save the converted result as `standard_table_v3`, then call `validate_standard_table` on the `standard_table_v3` path.
11. If `standard_table_v3` passes, make v3 the latest standard-table JSON/path and continue to Standard-Table Excel Output.
12. If `standard_table_v3` still fails, show the Standard-Table Failure Response using the v3 validation result.

When a batch group uses a group prefix such as `group_1_`, keep it in all versioned prefixes, for example `group_1_v2_` and `group_1_v3_`.

## Standard-Table Failure Response

Output exactly:

**标准表校验失败**

| 异常数据 | 失败原因 |
|---|---|
| ... | ... |

**建议：**

1. ...
2. ...

**请选择处理方式：**

A. 查看自动修正方案
B. 生成标准表 Excel 并在平台上查看
C. 重新上传更清晰文件

Do not offer an ignore/continue option.

## Standard-Table Correction

- Auto-fix path: propose deterministic, reversible corrections for the latest `standard_table.json` or, if mapping is the root cause, the latest subject mapping followed by rerunning conversion. If the automatic standard-mapping retry already produced v3, base this path on v3.
- Standard-table Excel path: call `standard_table_to_excel` and follow the Standard-Table Excel Output rules above; this is terminal viewing/manual review because there is no standard-table Excel-to-JSON tool.
- Re-upload path: restart from OCR.

Continue to final Excel output only after `validate_standard_table` passes.
