---
name: financial-report-extraction
description: Extract, validate, standardize, and output standard-table Excel files for one or more uploaded financial statement images. Supports single-image statements and multi-image statement groups; PDF support is a later workflow. Use when the user mentions 财报提取, 财报 OCR, 批量图片, 资产负债表, 利润表, 损益表, 现金流量表, 勾稽关系, 标准科目映射, 标准表校验, annual reports, quarterly reports, prospectuses, financial statements, or asks to recognize/extract/validate/standardize financial-report images.
---

# 财报提取

## Core Contract

Use this skill for one or more uploaded images containing financial-statement tables:

- 资产负债表
- 利润表 / 损益表
- 现金流量表

Current batch-image version supports one image per statement or multiple images per statement. It does not support one image containing multiple statement units. PDF support is intentionally out of scope for this iteration.

Always call the system tool named `ocr` first. The OCR output structure is stable; downstream extraction uses only `ocr.vlm_text`.

If `vlm_text` is missing, is not a string array, or cannot be joined into readable content, stop and ask the user to re-upload a clearer file or confirm manually. Do not fall back to other OCR fields.

## Workflow

### 1. OCR

1. Confirm the upload contains image files. If the user uploads PDF files, explain that PDF handling is not part of this iteration and ask for image uploads or wait for the PDF workflow.
2. Call `ocr` for every uploaded image before downstream extraction.
3. Read only each OCR response's `vlm_text`.
4. Preserve every raw OCR response in session state.

If the user asked only for OCR, summarize the recognized content and stop.

### 1.5. Normalize Batch OCR Results

If the user uploaded multiple images, read `references/batch-image-workflow.md`.

Group and order images based on OCR text, not upload order. Ask the user to confirm the inferred groups and order. After confirmation, normalize OCR results into:

```json
{
  "statement_vlm_texts": [
    ["报表1第1段", "报表1第2段"],
    ["报表2第1段"]
  ]
}
```

For a single image, `statement_vlm_texts` has one inner array containing that image's `vlm_text`.

For multi-image uploads, create `batch_manifest.json` with `scripts/prepare_batch_manifest.py` after the user confirms groups.

### 2. Map Statement `vlm_text` To Original JSON

Process each confirmed statement group serially. For each group, join its inner `vlm_text` array in original confirmed group order with newline separators.

Map only from the joined statement `vlm_text`. Do not infer from the image, file name, OCR metadata, or non-`vlm_text` fields.

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

For a single statement group, on success output exactly:

**标准表校验通过**

For multiple statement groups, output a contextual success line for each group and continue to the next group. After all groups succeed, output the batch summary defined in `references/batch-image-workflow.md`.

## Session State

Preserve these values across turns while this skill is active:

- raw OCR response and joined `vlm_text`
- `statement_vlm_texts`
- batch manifest path, batch groups, current group index, and completed groups for multi-image uploads
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
- Do not process multiple images before the user confirms inferred statement groups and group order.
- Do not support one image split into multiple statement units in this iteration; ask the user to split the image or confirm one statement to process.
- Do not rely on upload order for batch grouping or group order.
- Do not rerun completed groups when a later batch group pauses or is replaced.
- For re-upload replacement in a batch, require the user to specify which report group is being replaced unless there is exactly one paused current group.
- Do not continue after failed reconciliation or failed standard-table validation.
- Do not wrap successful JSON-only output in Markdown.
- Do not tell the user to download, upload, re-upload, or send back a generated Excel when the platform editing flow applies.
