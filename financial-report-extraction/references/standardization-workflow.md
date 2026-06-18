# Standardization Workflow

Use after original-table JSON is validated, or after standard-table validation fails.

## Shared Output Directory

Reuse the Step 1 `task_dir` for every JSON/Excel artifact. Never create a second timestamped directory or write production outputs to temp. For batch groups, keep the manifest `file_prefix` such as `group_1_`.

## Subject Mapping And Convert

1. Extract original subjects from `validated_json["表格数据"][].科目名称`; preserve order and exact text. Remove duplicates only for mapping prompt input, not from `validated_json`.
2. Read exactly one mapping reference for the statement type.
3. Generate one JSON object: keys exactly equal the runtime subject list; values are valid standard subjects or `__IGNORE__`.
4. Validate before writing: no missing/extra keys; keys preserve source text; values are non-empty strings, never `null`, arrays, objects, explanations, confidence scores, or combined text. Regenerate once on format failure; stop if still invalid.
5. Call `scripts/prepare_standard_mapping_files.py` with `validated_json`, `subject_mapping`, original filename, existing `task_dir`, optional `standard_subjects`, and `file_prefix`.
6. Call platform `convert_to_standard_table` with `original_table_json_file_path` set to the returned `original_table_json_file_path` (or the returned `original_validated_json_file_path`, which is the same file), `subject_mapping_json_file_path` set to the returned `subject_mapping_json_file_path`, and `rpt_type` (`资产负债表`=1, `利润表`/`损益表`=2, `现金流量表`=3).
7. Save the conversion output unchanged with `scripts/save_standard_table.py`; pass `expected_rpt_type=rpt_type` to `save_standard_table`. The saved `standard_table.json` must be valid JSON shaped like `{"rpt_type": 2, "standard_table": {"主营业务收入": {"本月数": 1475058.16, "本年累计数": 15200134.15}}}`. The script validates the wrapper, writes the file, reads it back, and confirms it still equals the conversion output. If the save/shape check fails, retry this save step once with the same unchanged conversion output. If it still fails, call `save_repaired_standard_table(conversion_output, rpt_type, task_dir, file_prefix)` once to generate a corrected `standard_table.json`; this repair may only add/fix the wrapper and must not rewrite subject names, columns, or amounts. If the repair save also fails, stop and report invalid standard-table JSON; do not call `validate_standard_table` yet.

## Validate Standard Table

Before calling the platform validator, the path must already have passed `scripts/save_standard_table.py` save/readback validation. Then call `validate_standard_table(standard_table_json_file_path)`.

Pass/fail detection:

- Prefer explicit fields: `校验是否通过`, `is_valid`, `passed`, `success`, `valid`.
- Clear pass/fail text is acceptable.
- Extract abnormal items from `异常数据`, `异常项`, `errors`, `issues`, `failed_items`, `details`.
- If return shape is unclear, show top-level keys for manual confirmation and stop.

## Retry Mapping Before User Choice

After the first `validate_standard_table` failure, run this once before showing failure choices. Do not run if first validation passes; do not loop.

Artifacts:

- v1 = first failed unversioned `subject_mapping.json` / `standard_table.json`
- v2 = independently regenerated full mapping/table
- v3 = v1 plus targeted remap of unstable original subjects

Steps:

1. Preserve v1; do not overwrite unversioned files.
2. Regenerate full `subject_mapping_v2` from the same validated original JSON, subject list, report type, and mapping reference. Do not copy v1.
3. Save/convert v2 using prefix `{file_prefix}v2_`; save as `standard_table_v2` with the same one-time local save/shape retry rule, then the same one-time repair save if still invalid.
4. Call `scripts/standard_mapping_retry.py:analyze_mapping_retry(standard_table_v1, standard_table_v2, subject_mapping_v1, subject_mapping_v2)`.
5. If no `standard_table_diffs` or no `remap_original_subjects`, mapping instability was not found; show the standard-table failure response.
6. Remap only `remap_original_subjects`. The partial JSON keys must exactly equal that list; values must be valid standard subjects or `__IGNORE__`. Use the full subject list, mapping reference, validation failure, and v1/v2 diff as context.
7. Call `merge_subject_mapping(subject_mapping_v1, partial_remap, remap_original_subjects)` to build v3.
8. Save/convert v3 using prefix `{file_prefix}v3_` with the same one-time local save/shape retry rule, then the same one-time repair save if still invalid; validate `standard_table_v3`.
9. If v3 passes, make v3 the latest standard-table JSON path and continue to Excel output. If v3 fails, show the failure response using v3 validation details.

For batch prefixes, keep both group and version: `group_1_v2_`, `group_1_v3_`.

## Final Standard-Table Excel Output

Use this only after `validate_standard_table` passes:

1. Call `standard_table_to_excel` with the latest validated `standard_table_json_file_path`, and `task_dir` if the platform tool supports output dir/path. This is the exclusive final-output converter; do not call other platform skill/tool, generic spreadsheet generators, or generic Excel writers for final standard-table Excel.
2. Treat `standard_table_json_file_path` only as tool input. Never label `standard_table.json`, `v2_standard_table.json`, or `v3_standard_table.json` as Excel output.
3. Final output must be under `task_dir` and end with `.xlsx` or `.xls`; any `.json` path is invalid.
4. If the returned Excel is outside `task_dir`, call `ensure_excel_file_in_task_dir(source_path, task_dir)` and use the copied path.
5. If the returned path is missing, non-existent, or non-Excel, rerun with `task_dir` if supported; otherwise stop and report invalid Excel output path. Do not fall back to `xlsx` or any other Excel-producing tool.
6. Store and show only the final Excel path in session state and batch summaries.

## Failure Response

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

No ignore/continue option.

## Correction Choices

- Auto-fix: propose deterministic, reversible corrections for the latest standard table or latest subject mapping; rerun conversion/validation after confirmation.
- Excel viewing: call `standard_table_to_excel` for terminal manual review only because there is no standard-table Excel-to-JSON tool. Label it as review Excel, not final output; continue to final output only after `validate_standard_table` passes.
- Re-upload: restart from OCR.

Continue to final Excel output only after `validate_standard_table` passes.
