---
name: financial-report-extraction
description: Extract, validate, standardize, and output standard-table Excel files for uploaded financial statement images or PDFs. Supports single-file statements, multi-file statement groups, and PDFs that contain one or multiple statement units. Use when the user mentions 财报提取, 财报 OCR, 批量图片, PDF 财报, 资产负债表, 利润表, 损益表, 现金流量表, 勾稽关系, 标准科目映射, 标准表校验, annual reports, quarterly reports, prospectuses, financial statements, or asks to recognize/extract/validate/standardize financial-report images or PDFs.
---

# 财报提取

## Scope

Use for uploaded financial-statement images/PDFs: `资产负债表`, `利润表`/`损益表`, `现金流量表`. Supported inputs include one or more images, single/multi-page PDFs, and PDFs containing multiple statement units.

Always call platform `ocr` first. Downstream extraction uses only `ocr.vlm_text`; if it is missing, not a string array, or unreadable after joining, stop for clearer upload/manual confirmation. Never infer from image/PDF metadata, filenames, or non-`vlm_text` OCR fields.

## Workflow

1. **Task directory**: before OCR, import helpers by adding this skill's `scripts/` directory to `sys.path`, then use `from task_outputs import create_task_output_dir, save_ocr_results`. Do not import `from scripts.task_outputs` unless the current working directory is the skill root. Call `create_task_output_dir(...)` once, passing platform `username` if available. Store the return object as `task_output`, then set `task_dir = task_output["task_dir"]`. Reuse this string `task_dir` for every JSON/Excel output. Default with username: `workspace/{username}/result/{original_filename_stem}_{yyyyMMdd_HHmmss}/`.

2. **OCR**: call `ocr` for every uploaded file. Immediately append each raw OCR return object to the raw list and save that exact unmodified list to `ocr_results.json` with `save_ocr_results(...)`. No summarizing, redaction, normalization, or placeholders. If the user only asked for OCR, summarize and stop.

3. **Batch/PDF grouping**: for multiple uploads or PDFs with multiple statement units, read `references/batch-image-workflow.md`. Group/split/order by OCR text, not upload order. Ask for user confirmation when multiple groups are inferred. Create `batch_manifest.json` in the existing `task_dir`.

4. **Original JSON**: process confirmed groups serially. Join each group's `vlm_text` segments with newlines, identify statement type from explicit text, then map to `references/target-json-schema.md`. Preserve visible amounts; use `""` only for truly blank/missing cells. If a visible amount cannot be safely assigned, ask for manual confirmation. JSON-only requests return the bare JSON object and stop.

5. **Original reconciliation**: for `资产负债表` and `利润表`, read `references/reconciliation-rules.md`; `现金流量表` skips this step. Reconciliation is zero-tolerance: any non-zero difference, including `0.01`, fails. On failure, run the one-time formula retry in `references/reconciliation-rules.md` only when the likely cause is formula construction error such as wrong operator or duplicated calculation. Do not retry for likely OCR errors or genuinely unbalanced source statements. If the retry still fails or is skipped, read `references/correction-workflow.md`, show the required response, and wait.

6. **Correction loop**: after reconciliation failure only. Auto-fix requires a deterministic, reversible plan and user confirmation. Excel editing uses `references/excel-editing.md`, `scripts/json_to_excel.py`, then `scripts/excel_to_json.py` after the user says the platform edit is saved. Re-upload restarts from OCR. Rerun Step 5 after every correction.

7. **Standard subject mapping**: after original JSON validates, read `references/standardization-workflow.md` and exactly one mapping reference:

- `资产负债表`: `references/standard-subject-mapping-balance-sheet.md`
- `利润表`/`损益表`: `references/standard-subject-mapping-income-statement.md`
- `现金流量表`: `references/standard-subject-mapping-cash-flow.md`

Generate a full subject mapping whose keys exactly match the runtime original subject list. Call `scripts/prepare_standard_mapping_files.py`, then platform `convert_to_standard_table`.

8. **Standard validation**: save the `convert_to_standard_table` return unchanged with `scripts/save_standard_table.py`; pass `expected_rpt_type=rpt_type` when calling `save_standard_table`. The script verifies the required `{"rpt_type": ..., "standard_table": ...}` JSON wrapper and reads the file back. If this local save/shape check fails, retry the same save once with the unchanged conversion return. If it still fails, call `save_repaired_standard_table(...)` once with the same conversion return and the same `rpt_type` to generate a valid wrapper; stop only if this repair save also fails. Then call `validate_standard_table`. On first `validate_standard_table` failure, run the one-time standard-mapping retry in `references/standardization-workflow.md`; if v3 still fails, show the required failure options and wait.

9. **Standard Excel**: after standard validation passes, call platform `standard_table_to_excel` with the latest validated standard-table JSON path; pass `task_dir` as output dir/path if supported. This is the only allowed tool for final standard-table Excel conversion. Do not call the platform `xlsx` skill/tool, spreadsheet generators, or generic Excel writers for this step. If `standard_table_to_excel` is unavailable or fails to return a valid Excel path, stop and report that the required tool is unavailable/invalid instead of substituting another Excel tool. The JSON path is input only. Final reported output must be `.xlsx`/`.xls`; reject `.json`. Use `ensure_excel_file_in_task_dir(...)` for outside paths. Single-group success output must include `标准表校验通过` and `标准表 Excel：{final_standard_table_excel_path}`; batches use `references/batch-image-workflow.md`.

## Session State

Preserve: raw OCR responses, `ocr_results.json`, `statement_vlm_texts`, batch manifest/groups/current index/completed groups, original uploaded filename, mapped original JSON, reconciliation failures/correction plan/formula retry result, editable original Excel path, `task_dir`, `original_validated.json`, `subject_mapping.json`, `standard_table.json`, standard retry artifacts v1/v2/v3, final standard Excel path, and latest standard validation result.

When the user says `继续`, `已保存`, `保存好了`, or `编辑好了`, continue from remembered Excel/session paths; ask for a path only if state and result-directory lookup fail.

## Guardrails

- Do not invent OCR text, figures, dates, units, rows, columns, mappings, or corrections.
- Do not use OCR fields other than `vlm_text`; never write processed OCR to `ocr_results.json`.
- Do not create a second timestamped output dir after Step 1.
- Do not split one image into multiple statement units in this version.
- For PDFs, split only from explicit `vlm_text` boundaries and ask confirmation before processing.
- Do not process multiple groups before confirmation; do not rely on upload order; do not rerun completed groups when a later group pauses/replaces.
- For batch re-upload replacement, require the target report group unless exactly one current group is paused.
- Do not continue after failed reconciliation or failed standard validation.
- Do not wrap JSON-only success output in Markdown.
- Do not use the `xlsx` skill/tool or any generic spreadsheet/Excel writer to produce final standard-table Excel; only `standard_table_to_excel` is valid for that output.
- Do not ask users to download/upload/send back generated Excel when platform editing applies.
