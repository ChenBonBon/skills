---
name: financial-report-extraction
description: Extract, validate, standardize, and output a standard-table Excel for one uploaded financial statement image or PDF. Use when the user mentions 财报提取, 财报 OCR, 资产负债表, 利润表, 损益表, 现金流量表, 勾稽关系, 标准科目映射, 标准表校验, annual reports, quarterly reports, prospectuses, financial statements, or asks to recognize/extract/validate/standardize financial-report images or PDFs.
---

# 财报提取

## Core Contract

Use this skill for one uploaded image or PDF containing one financial-statement table:

- 资产负债表
- 利润表 / 损益表
- 现金流量表

Always call the system tool named `ocr` first. The OCR output structure is stable; downstream extraction uses only `ocr.vlm_text`.

If `vlm_text` is missing, is not a string array, or cannot be joined into readable content, stop and ask the user to re-upload a clearer file or confirm manually. Do not fall back to other OCR fields.

## Workflow

### 1. OCR

1. Confirm the upload is an image or PDF.
2. Call `ocr`.
3. Read only `vlm_text`.
4. Join `vlm_text` in original order with newline separators.
5. Preserve the raw OCR response in session state.

If the user asked only for OCR, summarize the recognized content and stop.

### 2. Map `vlm_text` To Original JSON

Map only from the joined `vlm_text`. Do not infer from the image, PDF, file name, OCR metadata, or non-`vlm_text` fields.

Identify the statement type from explicit text, then produce the matching original-table JSON schema. See `references/target-json-schema.md` only when mapping or validating this JSON shape.

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

Generate a subject mapping JSON whose keys exactly match the runtime original subject list. Then call `scripts/prepare_standard_mapping_files.py` and the system tool `convert_to_standard_table`.

### 6. Standard-Table Validation

Save the `convert_to_standard_table` result with `scripts/save_standard_table.py`, then call `validate_standard_table`.

If validation passes, continue automatically. If it fails, read `references/standardization-workflow.md`, show the required failure response, and wait for the user to choose a correction path.

### 7. Output Standard Table Excel

After standard-table validation passes, call `standard_table_to_excel`.

On success, output exactly:

**标准表校验通过**

## Session State

Preserve these values across turns while this skill is active:

- raw OCR response and joined `vlm_text`
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
- Do not process multiple target tables from one upload without asking which table to extract.
- Do not continue after failed reconciliation or failed standard-table validation.
- Do not wrap successful JSON-only output in Markdown.
- Do not tell the user to download, upload, re-upload, or send back a generated Excel when the platform editing flow applies.
