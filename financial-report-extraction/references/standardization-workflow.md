# Standardization Workflow

Use this reference only after original-table JSON is validated or after standard-table validation fails.

## Task Directory

Resolve the task output directory as:

```text
workspace/{username}/result/{original_filename_stem}/
```

If the exact workspace root is unavailable, use the current runtime context. Do not write production outputs to a temporary directory.

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
    task_dir=None,
    standard_subjects=None,
)
```

Use returned paths directly for `convert_to_standard_table`:

- `original_table_json_file_path`: returned `original_validated.json`
- `subject_mapping_json_file_path`: returned `subject_mapping.json`
- `rpt_type`: `1` for `资产负债表`, `2` for `利润表` / `损益表`, `3` for `现金流量表`

Save the returned standard-table JSON with `scripts/save_standard_table.py`.

## Validate Standard Table

Call `validate_standard_table` with:

- `standard_table_json_file_path`: path to `standard_table.json`
- `rpt_type`: `1`, `2`, or `3`

Pass/fail detection:

- Prefer explicit fields such as `校验是否通过`, `is_valid`, `passed`, `success`, or `valid`.
- If text clearly says validation passed, treat it as passed.
- Extract abnormal items from fields such as `异常数据`, `异常项`, `errors`, `issues`, `failed_items`, or `details`.
- If the return shape is unclear, show a manual-confirmation table with top-level keys and stop.

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

- Auto-fix path: propose deterministic, reversible corrections for `standard_table.json` or, if mapping is the root cause, `subject_mapping.json` followed by rerunning conversion.
- Standard-table Excel path: call `standard_table_to_excel`; this is terminal viewing/manual review because there is no standard-table Excel-to-JSON tool.
- Re-upload path: restart from OCR.

Continue to final Excel output only after `validate_standard_table` passes.
