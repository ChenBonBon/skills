---
name: financial-report-extraction
description: Extract, validate, standardize, and output standard-table Excel files for uploaded financial statement images or PDFs. Supports single-file statements, multi-file statement groups, and PDFs that contain one or multiple statement units. Use when the user mentions 财报提取, 财报 OCR, 批量图片, PDF 财报, 资产负债表, 利润表, 损益表, 现金流量表, 勾稽关系, 标准科目映射, 标准表校验, annual reports, quarterly reports, prospectuses, financial statements, or asks to recognize/extract/validate/standardize financial-report images or PDFs.
---

# 财报提取

## Core Contract

Use this skill for one or more uploaded images or PDFs containing financial-statement tables:

- 资产负债表
- 利润表 / 损益表
- 现金流量表

Current version supports:

- single-page PDF -> one statement
- multi-page PDF -> one statement
- multi-page PDF -> multiple statements
- one image per statement
- multiple images/files per statement

Images are not split into multiple statement units in this iteration. PDFs may be split into multiple statement groups based only on `vlm_text`.

Always call the system tool named `ocr` first. The OCR output structure is stable; downstream extraction uses only `ocr.vlm_text`.

If `vlm_text` is missing, is not a string array, or cannot be joined into readable content, stop and ask the user to re-upload a clearer file or confirm manually. Do not fall back to other OCR fields.

## Workflow

### 0. Create Task Output Directory

Create one global task output directory with `scripts/task_outputs.py` before the first file is written:

```python
create_task_output_dir(original_filename, result_root=None, timestamp=None)
```

Use the returned `task_dir` for every file written during this run. The default path is:

```text
workspace/{username}/result/{original_filename_stem}_{yyyyMMdd_HHmmss}/
```

Use the system timestamp once, then reuse the same `task_dir`; do not create a new timestamped directory in later steps.

- For a single-file upload, create `task_dir` before OCR with that file name.
- For multi-file uploads, create `task_dir` before OCR with the platform batch name if available; otherwise use the first uploaded source file name. Do not wait for grouping confirmation to create `task_dir`, because raw OCR must be persisted before model summarization can occur.

### 1. OCR

1. Confirm the upload contains image or PDF files.
2. Call `ocr` for every uploaded file before downstream extraction.
3. Read only each OCR response's `vlm_text`.
4. Immediately after each OCR call, append the exact OCR tool return object to the raw OCR response list and save that unmodified list to `ocr_results.json` in `task_dir` with `scripts/task_outputs.py`.
5. Do not summarize, redact, shorten, normalize, reconstruct, or replace OCR content with placeholders such as `see original OCR`; `ocr_results.json` must contain the original OCR tool output only.
6. Preserve every raw OCR response and the `ocr_results.json` path in session state.

If the user asked only for OCR, summarize the recognized content and stop.

### 1.5. Normalize Batch OCR Results

If the user uploaded multiple files, or uploaded a PDF whose OCR text contains multiple statement units, read `references/batch-image-workflow.md`.

Group, split, and order statement units based on OCR text, not upload order. Ask the user to confirm the inferred groups and order when there are multiple groups. After confirmation, normalize OCR results into:

```json
{
  "statement_vlm_texts": [
    ["报表1第1段", "报表1第2段"],
    ["报表2第1段"]
  ]
}
```

For a single-image statement, `statement_vlm_texts` has one inner array containing that image's `vlm_text`. For a single PDF that contains one statement, it has one inner array containing that PDF statement's `vlm_text`. For a PDF that contains multiple statements, split the PDF's `vlm_text` into one inner array per statement unit.

For multi-file uploads or multi-statement PDFs, create `batch_manifest.json` with `scripts/prepare_batch_manifest.py` after the user confirms groups. Pass the existing `task_dir` as `batch_dir`; do not create a separate batch directory.

### 2. Map Statement `vlm_text` To Original JSON

Process each confirmed statement group serially. For each group, join its inner `vlm_text` array in original confirmed group order with newline separators.

Map only from the joined statement `vlm_text`. Do not infer from the image/PDF, file name, OCR metadata, or non-`vlm_text` fields.

Identify the statement type from explicit text, then produce the matching original-table JSON schema. See `references/target-json-schema.md` only when mapping or validating this JSON shape.

Do not leave amount fields empty when the corresponding subject row has visible amount text in `vlm_text`. Use `""` only for truly missing or blank source cells; if visible amounts cannot be assigned safely, ask for manual confirmation.

If the user explicitly asks only for JSON extraction, output only the bare JSON object and stop.

### 3. Original-Table Reconciliation

- For `资产负债表` and `利润表`, read `references/reconciliation-rules.md` and run reconciliation checks.
- For `现金流量表`, skip reconciliation in this version and treat the mapped JSON as validated.

If reconciliation passes, continue automatically. If it fails, read `references/correction-workflow.md`, show the required failure response, and wait for the user to choose a correction path.

### 4. Correction Loop

Use this only after reconciliation fails.

- Auto-fix path: propose a deterministic correction plan and apply it only after user confirmation.
- Excel editing path: read `references/excel-editing.md`, generate editable Excel with `scripts/json_to_excel.py`, remember its path, then convert it back with `scripts/excel_to_json.py` after the user says the platform edit is saved.
- Re-upload path: restart from OCR.

After any correction, rerun Step 3. Do not continue while reconciliation fails.

### 5. Standard Subject Mapping

After original-table JSON is validated, read `references/standardization-workflow.md`.

Use exactly one mapping reference:

- `资产负债表` -> `references/standard-subject-mapping-balance-sheet.md`
- `利润表` / `损益表` -> `references/standard-subject-mapping-income-statement.md`
- `现金流量表` -> `references/standard-subject-mapping-cash-flow.md`

Generate a subject mapping JSON whose keys exactly match the runtime original subject list. Then call `scripts/prepare_standard_mapping_files.py` with the existing `task_dir`, and call the system tool `convert_to_standard_table`.

### 6. Standard-Table Validation

Save the `convert_to_standard_table` result with `scripts/save_standard_table.py` in the existing `task_dir`, then call `validate_standard_table`.

If validation passes, continue automatically. If it fails, read `references/standardization-workflow.md`, show the required failure response, and wait for the user to choose a correction path.

### 7. Output Standard Table Excel

After standard-table validation passes, call `standard_table_to_excel`.

For a single statement group, on success output exactly:

**标准表校验通过**

For multiple statement groups, output a contextual success line for each group and continue to the next group. After all groups succeed, output the batch summary defined in `references/batch-image-workflow.md`.

## Session State

Preserve these values across turns while this skill is active:

- raw OCR response and joined `vlm_text`
- `ocr_results.json` path
- `statement_vlm_texts`
- batch manifest path, batch groups, current group index, and completed groups for multi-file uploads
- mapped original-table JSON
- original uploaded file name
- reconciliation failures and correction plan, if any
- editable original-table Excel path, if generated
- task output directory
- `original_validated.json`, `subject_mapping.json`, and `standard_table.json` paths
- latest standard-table JSON and validation result

When the user says `继续`, `已保存`, `保存好了`, or `编辑好了`, continue from the remembered Excel path. Only ask for a path if session state and result-directory lookup both fail.

## Global Guardrails

- Do not invent OCR text, financial figures, dates, units, rows, columns, or mappings.
- Do not use OCR fields other than `vlm_text` for extraction.
- Do not write processed OCR data to `ocr_results.json`; it is only for exact OCR tool returns.
- Do not save placeholder OCR text such as `...`, `see original OCR`, `truncated`, or `omitted`.
- Do not write task files outside the task output directory unless a platform tool requires its own output path.
- Do not create a second timestamped output directory after Step 0; reuse the remembered `task_dir`.
- Do not process multiple statement groups before the user confirms inferred groups and order.
- Do not split one image into multiple statement units in this iteration; ask the user to split the image or confirm one statement to process.
- For PDFs, split multiple statement units only from `vlm_text` using explicit statement boundaries, and ask the user to confirm the split before processing.
- Do not rely on upload order for batch grouping or group order.
- Do not rerun completed groups when a later batch group pauses or is replaced.
- For re-upload replacement in a batch, require the user to specify which report group is being replaced unless there is exactly one paused current group.
- Do not continue after failed reconciliation or failed standard-table validation.
- Do not wrap successful JSON-only output in Markdown.
- Do not tell the user to download, upload, re-upload, or send back a generated Excel when the platform editing flow applies.
