---
name: financial-report-extraction
description: Extract, validate, correct, standardize, validate a standard table, and output a standard-table Excel for a single balance sheet, income statement, or cash-flow statement from an uploaded financial-report image or PDF. First call the system tool named ocr, inspect the actual OCR response, map only the returned vlm_text string array into the required Chinese JSON format, then run reconciliation checks for balance sheets and income statements using references/reconciliation-rules.md. When reconciliation fails, show abnormalities and guide the user to confirm an auto-fix plan, generate an editable Excel with scripts/json_to_excel.py, or re-upload. After validation passes, map original subjects to standard subjects using the matching reference prompt, call convert_to_standard_table, save standard_table.json, call validate_standard_table, then call standard_table_to_excel after standard-table validation passes. Use when the user mentions 财报提取, 财报 OCR, 勾稽关系, 资产负债表, 利润表, 损益表, 现金流量表, 标准科目映射, 标准表校验, annual reports, quarterly reports, prospectuses, financial statements, or asks to recognize/extract/validate/standardize financial-report images or PDFs.
---

# 财报提取

## Scope

Use this skill when the user uploads an image or PDF containing one financial-statement table and wants it recognized and converted to JSON.

Current version supports one table per uploaded file:

- 资产负债表
- 利润表 / 损益表
- 现金流量表

If the OCR result shows multiple target tables in one upload, stop and ask the user to confirm which table to extract.

## Workflow

### Step 1: OCR

1. Confirm the uploaded file exists and is an image or PDF.
2. Call the system tool named `ocr` to recognize the uploaded file.
3. Inspect the actual OCR response shape before extracting anything.
4. Preserve the complete raw OCR response during the task.
5. Continue to Step 2 after OCR succeeds, unless the user explicitly asked only for OCR recognition.

OCR succeeds when:

- the `ocr` tool returns a JSON object,
- the JSON object contains `vlm_text`,
- `vlm_text` is a string array.

If OCR fails, explain the failure and ask the user to upload a clearer image/PDF.

### Step 2: Map `vlm_text` to JSON

1. Read `vlm_text` from the OCR return value.
2. Confirm `vlm_text` is a string array. If not, output a manual-confirmation table.
3. Join the array in original order with newline separators: `"\n".join(vlm_text)`.
4. Extract only from the joined `vlm_text`.
5. Identify the statement type from explicit text:
   - `资产负债表` -> `资产负债表`
   - `利润表` or `损益表` -> `利润表`
   - `现金流量表` -> `现金流量表`
6. Extract `表名`, `编制单位`, `日期`, `单位`, and the main financial table rows.
7. Keep the mapped JSON object in memory for Step 3. Do not write it to a file.
8. If mapping cannot proceed safely, output Markdown tables for manual confirmation.

If the user explicitly asks only for JSON extraction, stop after Step 2 and output only the bare JSON object. Do not wrap it in Markdown code fences and do not add explanatory text.

### Step 3: Reconciliation Check

1. Use the in-memory JSON object produced by Step 2 as the only reconciliation input.
2. Run reconciliation checks only for `资产负债表` and `利润表`.
3. For `资产负债表` and `利润表`, read `references/reconciliation-rules.md` and follow its rules internally.
4. For `现金流量表`, skip reconciliation checks and treat the Step 2 JSON object as validated for Step 5.
5. If reconciliation passes, continue to Step 5 automatically.
6. If reconciliation fails, do not expose the full internal check result. Output exactly four sections in order: failure notice, abnormal-data table, suggestions, and user choices.
7. Failed reconciliation blocks downstream processing until the data is corrected and Step 3 passes.

### Step 4: Correction Loop

Use this step only after Step 3 fails and the user chooses a handling method.

- Auto-fix path: propose a deterministic, explainable, reversible correction plan from the Step 2 JSON. Do not modify data before the user confirms the plan. After confirmation, apply the correction to the Step 2 JSON shape and rerun Step 3.
- Excel editing path: call `scripts/json_to_excel.py` only after the user chooses to generate an editable Excel. Use the Step 2 JSON as the script input and pass the Step 3 abnormal-data items so the generated Excel highlights affected rows or cells. Record the returned Excel path in session state. After the user edits the Excel and says to continue, call `scripts/excel_to_json.py` with that recorded path to convert it back to the same Step 2 JSON shape, then rerun Step 3.
- Re-upload path: ask the user to upload a clearer file and restart from Step 1.

Every correction path must pass Step 3 before the data can continue to later workflow steps.

### Step 5: Standard Subject Mapping

Run this step automatically after the original table JSON is validated:

- For `资产负债表` and `利润表`, run Step 5 only after Step 3 passes.
- For `现金流量表`, run Step 5 after Step 2 succeeds because this version does not run reconciliation checks for cash-flow statements.

Use the final validated original-table JSON as the input. This may be the initial Step 2 JSON, the auto-fixed JSON after the user confirms the fix, or the Excel-edited JSON after it is converted back and passes Step 3.

1. Resolve the task output directory as `workspace/{username}/result/{original_filename_stem}/`. The directory name must use the uploaded original file name without extension so users can recognize the task.
2. Do not write the final validated original-table JSON before validation passes.
3. Extract the runtime original subject list from `validated_json["表格数据"][].科目名称`, preserving original order and exact text. Remove duplicate subject names only for the mapping prompt input; do not modify `validated_json`.
4. Read exactly one standard-subject mapping prompt:
   - `资产负债表` -> `references/standard-subject-mapping-balance-sheet.md`
   - `利润表` or `损益表` -> `references/standard-subject-mapping-income-statement.md`
   - `现金流量表` -> `references/standard-subject-mapping-cash-flow.md`
5. Use the selected reference prompt as mapping rules and standard-subject list. Replace its runtime original-subject placeholder with the actual subject list from `validated_json`. Never use a fixed example original-subject list from a reference file.
6. Produce a subject mapping JSON object whose keys exactly match the runtime original subject list and whose values are standard subject names or `__IGNORE__`.
7. Validate the subject mapping before writing files or calling tools.
8. Call `scripts/prepare_standard_mapping_files.py` with the final validated original-table JSON, the subject mapping JSON object, the original uploaded file name, and the resolved `result` root or task directory. The script writes `original_validated.json` and `subject_mapping.json` in the task output directory.
9. Call the system tool named `convert_to_standard_table` with the paths returned by the script:
   - `original_table_json_file_path`: path to `original_validated.json`
   - `subject_mapping_json_file_path`: path to `subject_mapping.json`
   - `rpt_type`: `1` for `资产负债表`, `2` for `利润表` or `损益表`, `3` for `现金流量表`
10. Keep the JSON returned by `convert_to_standard_table` in memory and call `scripts/save_standard_table.py` to write it to `standard_table.json` in the task output directory.
11. Continue to Step 6 automatically.

Standard subject mapping is expected to complete successfully. If the mapping output is not valid JSON, misses runtime original subjects, contains extra keys, or `convert_to_standard_table` fails, explain the format/tool failure briefly and do not proceed to later workflow steps.

### Step 6: Validate Standard Table

Run this step automatically after Step 5 writes `standard_table.json`.

1. Call the system tool named `validate_standard_table` with:
   - `standard_table_json_file_path`: path to `standard_table.json`
   - `rpt_type`: `1` for `资产负债表`, `2` for `利润表` or `损益表`, `3` for `现金流量表`
2. Inspect the actual return shape before deciding pass/fail.
3. If validation passes, continue to Step 7 automatically.
4. If validation fails, output exactly four sections in order: failure notice, abnormal-data table, suggestions, and user choices.

Validation pass/fail detection:

- Prefer explicit fields such as `校验是否通过`, `is_valid`, `passed`, `success`, or `valid`.
- If no explicit field exists but the returned text clearly says validation passed, treat it as passed.
- If failure is indicated, extract abnormal items from fields such as `异常数据`, `异常项`, `errors`, `issues`, `failed_items`, or `details`.
- If structured abnormal items cannot be extracted, put a concise summary of the returned result into the abnormal-data table. Do not invent missing details.
- If the return shape is not understandable, output a manual-confirmation table with available top-level keys and stop.

For failed standard-table validation, use this user-facing structure:

**标准表校验失败**

Then show the failed data and reasons in a Markdown table:

| 异常数据 | 失败原因 |
|---|---|
| ... | ... |

Then show suggestions below the table:

**建议：**

1. ...
2. ...

Then show concrete user choices:

**请选择处理方式：**

A. 查看自动修正方案
B. 生成标准表 Excel 并在平台上查看
C. 重新上传更清晰文件

Do not offer an ignore/continue option. A standard table that fails validation cannot proceed to later workflow steps.

### Step 7: Output Standard Table Excel

Run this step automatically after Step 6 passes, including after auto-fix followed by a successful Step 6 rerun.

1. Call the system tool named `standard_table_to_excel` with:
   - `standard_table_json_file_path`: path to the validated `standard_table.json`
   - `rpt_type`: `1` for `资产负债表`, `2` for `利润表` or `损益表`, `3` for `现金流量表`
2. The tool should output the correct standard-table Excel under the current task/result directory.
3. If the tool succeeds, output only: `标准表校验通过`
4. If the tool fails, explain that standard-table validation passed but Excel output failed, and stop.

### Standard Table Correction Loop

Use this only after Step 6 fails and the user chooses a handling method.

- Auto-fix path: propose a deterministic, explainable, reversible correction plan for `standard_table.json` or, when the root cause is subject mapping, for `subject_mapping.json` followed by rerunning Step 5. Do not modify data before the user confirms the plan. After confirmation, apply the correction, write the updated JSON file, rerun `validate_standard_table`, and continue to Step 7 only if it passes.
- Standard-table Excel path: call the system tool named `standard_table_to_excel` with `standard_table_json_file_path` and `rpt_type`. This path is a terminal aid for platform viewing/manual review because there is currently no standard-table Excel-to-JSON tool. Do not tell the user to edit, save, and continue from this Excel.
- Re-upload path: ask the user to upload a clearer file and restart from Step 1.

### Subject Mapping Validation

Before writing `subject_mapping.json`, validate that:

- `subject_mapping` is a JSON object, not an array or string.
- Its key set exactly equals the runtime original subject list extracted from `validated_json["表格数据"][].科目名称` after duplicate removal.
- It has no missing keys and no extra keys.
- Every key preserves the original subject text exactly.
- Every value is a non-empty string.
- Every value is either one of the selected reference prompt's standard subject names or exactly `__IGNORE__`.
- Values must not be `null`, arrays, objects, explanations, confidence scores, or combined text.

If validation fails, regenerate the subject mapping JSON once using the same reference prompt and runtime original subject list. If it still fails, explain the format failure briefly and stop; do not call `scripts/prepare_standard_mapping_files.py` or `convert_to_standard_table`.

## Standard Mapping File Script

Use `scripts/prepare_standard_mapping_files.py` in Step 5 after the subject mapping JSON object is produced.

Call:

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

- `validated_json`: final original-table JSON after validation passes.
- `subject_mapping`: the Step 5 mapping JSON object.
- `original_filename`: uploaded source file name.
- `result_root`: current user's `workspace/{username}/result` directory when known.
- `task_dir`: explicit `workspace/{username}/result/{original_filename_stem}/` directory when already resolved.
- `standard_subjects`: optional standard subject list parsed from the selected reference prompt. Pass it when available so the script can validate mapping values.

If neither `result_root` nor `task_dir` is provided, the script writes under `./result/{original_filename_stem}/`.

The script validates that `subject_mapping` keys exactly match `validated_json["表格数据"][].科目名称` after duplicate removal. When `standard_subjects` is provided, it also validates that every value is either a standard subject or `__IGNORE__`.

The script returns:

```json
{
  "task_dir": "",
  "original_validated_json_file_path": "",
  "subject_mapping_json_file_path": ""
}
```

Use these returned file paths directly as `convert_to_standard_table` inputs.

## Standard Table Save Script

Use `scripts/save_standard_table.py` in Step 5 after `convert_to_standard_table` returns a JSON object.

Call:

```python
save_standard_table(standard_table_json, task_dir)
```

- `standard_table_json`: JSON object returned by `convert_to_standard_table`.
- `task_dir`: task output directory returned by `prepare_standard_mapping_files`.

The script writes `standard_table.json` and returns its path. Use that returned path as `validate_standard_table.standard_table_json_file_path`.

## Session State

Preserve these values across turns whenever this skill is active:

- Step 2 mapped JSON object.
- Step 3 abnormal-data items and failure reasons.
- Original uploaded file name.
- Generated editable Excel path returned by `scripts/json_to_excel.py`.
- The resolved `result` directory used for the current user workspace.
- Task output directory: `workspace/{username}/result/{original_filename_stem}/`.
- `original_validated.json` path.
- `subject_mapping.json` path.
- `standard_table.json` path.
- Standard table JSON returned by `convert_to_standard_table`.
- Latest `validate_standard_table` result.
- Standard-table Excel path or resource returned by `standard_table_to_excel`.

When the user says `继续`, `已保存`, `保存好了`, `编辑好了`, or otherwise indicates the platform Excel editing is complete:

1. Treat it as a request to continue the Excel editing path.
2. Use the recorded generated Excel path. Do not ask the user to provide the file path again.
3. If the recorded path is unavailable because the conversation state was lost, infer the current user's `result` directory from runtime context and use the most recently modified `.xlsx` in that directory.
4. Only ask the user for a file path if both the recorded path and the `result` directory lookup fail or are ambiguous.
5. Convert the Excel with `scripts/excel_to_json.py`, validate that the output matches the Step 2 JSON schema, then rerun Step 3.

## Core Boundary

- User input is only an uploaded image or PDF.
- Always call `ocr` first.
- Use the complete OCR return value only to read `vlm_text`.
- Extract only from `vlm_text` after newline joining.
- Do not use image layout, visual inspection, file name, `id`, `original_filename`, `pages`, `blocks`, `tables`, or any other OCR field as fallback.
- Do not infer table structure from the original image/PDF.
- Do not invent fields, values, dates, units, table rows, column names, or missing OCR content.

The OCR tool is responsible for recognizing layout and producing usable `vlm_text`. This skill is responsible only for mapping `vlm_text` into the target JSON.

## Reconciliation Rules

For Step 3, read `references/reconciliation-rules.md` only when the mapped `表名` is `资产负债表` or `利润表`.

Use the reference file's rules and check-result shape as internal working structure. Do not expose that full structure to the user unless the user explicitly asks for detailed check internals.

When all reconciliation checks pass, continue to Step 5 automatically in the full workflow.

If the user explicitly asks only to run reconciliation checks, the user-facing success output must be exactly:

```text
勾稽关系校验通过
```

Do not run reconciliation checks for `现金流量表` in this version. After successfully mapping a cash-flow statement to JSON, treat it as validated and continue to Step 5.

## Excel Editing Script

Use `scripts/json_to_excel.py` only when the user chooses Excel online editing after reconciliation fails.

Call its function with the Step 2 JSON serialized as a string:

```python
json_data_to_excel(
    vlm_text,
    original_filename,
    json_out_dir=None,
    sheet_name="Sheet1",
    abnormal_items=None,
)
```

- `vlm_text`: the Step 2 JSON object serialized with Chinese text preserved.
- `original_filename`: the uploaded file name, used only to derive the Excel file name.
- `json_out_dir`: the task output directory where the Excel file should be written, normally `workspace/{username}/result/{original_filename_stem}/`. If the exact workspace path is ambiguous, infer it from the runtime context before calling the script; do not write production Excel files to a temporary directory.
- `sheet_name`: prefer the mapped `表名` when available.
- `abnormal_items`: the abnormal-data rows from the failed Step 3 check. Pass a list of dictionaries when available. The script recognizes keys such as `科目名称`, `涉及科目`, `异常数据`, `项目`, `科目`, `结果科目`, `字段`, `列名`, `金额字段`, `异常字段`, `期间`, `失败原因`, `原因`, and `说明`.

If `json_out_dir` is omitted, the script writes to `./result/{original_filename_stem}/` under the current working directory. The function creates the directory if needed, saves the workbook as `{original_filename_stem}_origin.xlsx`, and returns the generated Excel path.

The generated Excel represents the Step 2 structured table data for user editing. It should highlight abnormal subjects or cells from `abnormal_items`; specific amount cells are highlighted when both subject and field/period are available, otherwise the affected row is highlighted. Do not include raw OCR text, OCR metadata, or internal reconciliation structures in the Excel unless a platform-specific script later requires it.

After the user edits the Excel, use `scripts/excel_to_json.py` to convert it back to JSON. Its output must match the same Step 2 JSON schema before Step 3 is rerun.

### Excel Generation Response

After generating the editable Excel, tell the user the Excel is ready for online editing in the platform. Do not instruct the user to download, upload, re-upload, or manually provide the edited file.

The response may include:

- generated Excel path or resource identifier,
- workbook/sheet summary,
- highlighted abnormal rows or cells,
- a short note that highlighted cells indicate where to edit,
- the next platform action: open the generated Excel in the platform editor, edit the highlighted cells, then save or sync in the platform so `scripts/excel_to_json.py` can convert it back and Step 3 can rerun.

After this response, remember the generated Excel path. If the user later says `继续` or says the online edit has been saved, continue from that path automatically.

The response must not include a download-upload workflow. Avoid wording such as:

- 下载并打开该 Excel 文件
- 保存后重新上传 Excel
- 上传修改后的文件
- 将文件发回给我

## Target JSON

All output values must be strings. Do not normalize dates or numbers.

For `资产负债表`:

```json
{
  "表名": "资产负债表",
  "编制单位": "",
  "日期": "",
  "单位": "",
  "表格数据": [
    {
      "科目名称": "",
      "年初数": "",
      "期末数": ""
    }
  ]
}
```

For `利润表` or `损益表`, output the standard table name `利润表`:

```json
{
  "表名": "利润表",
  "编制单位": "",
  "日期": "",
  "单位": "",
  "表格数据": [
    {
      "科目名称": "",
      "本月数": "",
      "本年累计数": ""
    }
  ]
}
```

For `现金流量表`:

```json
{
  "表名": "现金流量表",
  "编制单位": "",
  "日期": "",
  "单位": "",
  "表格数据": [
    {
      "科目名称": "",
      "本年金额": ""
    }
  ]
}
```

## Mapping Rules

- `表名` must be recognized as one of the supported statement types. If not, ask for manual confirmation.
- `编制单位`, `日期`, and `单位` may be empty strings if missing from `vlm_text`.
- `日期` must preserve the source text format. Do not convert formats such as `2017年12月31日` to `2017-12-31`.
- Preserve numeric strings as text. Do not remove commas, convert parentheses to negatives, convert `--` to `0`, or add missing decimals.
- Only trim leading/trailing whitespace and merge obvious OCR line-break whitespace inside a single value.
- Keep original main-table row order from `vlm_text`.
- Keep group rows, heading rows, subtotal rows, and total rows if they are part of the main financial table. If a kept row has no amount, use `""` for the amount fields.
- Do not output `行次`.
- Drop auxiliary columns and extra columns that are not part of the target schema.
- If a target amount column cannot be matched, set that amount field to `""`.
- If `科目名称` cannot be mapped from `vlm_text`, do not guess from position. Ask for manual confirmation.
- Exclude non-main-table content such as signatures, preparer/reviewer fields, page numbers, seals, supplementary notes, and OCR noise.

## Manual Confirmation

Use Markdown tables, not partial JSON, when `vlm_text` cannot be mapped safely.

Manual confirmation is required when:

- `vlm_text` is missing or is not a string array.
- `vlm_text` cannot be joined into readable content.
- the statement type cannot be identified from explicit table-name text.
- multiple target tables appear in one upload.
- the main financial table cannot be located in `vlm_text`.
- `科目名称` cannot be mapped from `vlm_text`.

Example:

| 项目 | 内容 |
|---|---|
| 状态 | 需要人工确认 |
| 原因 | 无法识别明确的表名 |
| 支持的表名 | 资产负债表、利润表、现金流量表 |
| 相关 vlm_text 片段 | ... |
| 需要确认 | 请确认该文件属于哪一种报表 |

If only amount columns cannot be matched, still output JSON and set unmatched target amount fields to `""`.

For failed reconciliation checks, use this user-facing structure:

**勾稽关系校验失败**

Then show the failed data and reasons in a Markdown table:

| 异常数据 | 失败原因 |
|---|---|
| ... | ... |

Then show suggestions below the table:

**建议：**

1. ...
2. ...

Then show concrete user choices:

**请选择处理方式：**

A. ...
B. ...
C. ...

Choices should match the actual failure. Common choices include:

- 查看自动修正方案
- 生成 Excel 并在平台上在线编辑
- 重新上传更清晰文件

Do not offer an ignore/continue option. Data that fails reconciliation cannot proceed to later workflow steps.

## Auto-Fix Plan

Auto-fix may be offered only for deterministic, explainable, reversible issues. Examples include OCR amount-column misalignment with a unique recovery, missing total values that can be uniquely calculated from complete details, or consistently misread period column headers.

Do not auto-fix original statements that are genuinely unbalanced. Do not fabricate numbers to make reconciliation pass.

When the user chooses to view an auto-fix plan, output a confirmation table with:

| 问题类型 | 涉及科目 | 当前值 | 建议值 | 推导依据 | 影响公式 | 风险等级 |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | 低 |

Only low-risk, unique corrections may be included. If no deterministic correction exists, say so and offer Excel editing or re-upload.

After the user confirms the auto-fix plan, apply the changes to the Step 2 JSON shape and rerun Step 3. If the rerun passes, continue to Step 5 automatically; if it fails, show the failed reconciliation structure again.

## Guardrails

- Step 2 JSON output must be a single bare JSON object, not an array, when the user asks only for JSON extraction.
- Step 3 success for `资产负债表` and `利润表` must continue to Step 5 automatically. Do not stop after outputting `勾稽关系校验通过` in the full workflow.
- `现金流量表` must continue to Step 5 automatically after successful Step 2 mapping in the full workflow.
- Step 5 success must continue to Step 6 automatically. Do not stop after standard subject mapping in the full workflow.
- Step 6 success must continue to Step 7 automatically. Do not stop before calling `standard_table_to_excel`.
- Step 7 success output must be exactly `标准表校验通过`.
- Step 6 failure choices must not include ignoring the warning or continuing with failed data.
- Step 3 failure output must start with bold `**勾稽关系校验失败**`, then show an abnormal-data/reason table, then bold `**建议：**`, then bold `**请选择处理方式：**`. Do not output a partial corrected JSON.
- Step 3 failure choices must not include ignoring the warning or continuing with failed data.
- Do not call `scripts/json_to_excel.py` until the user chooses Excel online editing.
- After editable Excel generation, do not tell the user to download, upload, re-upload, or send back the Excel. The platform handles online editing and conversion back to JSON.
- After the user saves online Excel edits and asks to continue, do not ask for the Excel path unless the recorded path is unavailable and result-directory lookup fails.
- Do not add English keys, normalized fields, evidence fields, comments, or Markdown around successful JSON/check-result output.
- Do not continue to JSON mapping if OCR fails.
- Do not repair OCR quality issues. If `vlm_text` is insufficient, either output empty target amount fields as specified or ask for manual confirmation.
