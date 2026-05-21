---
name: financial-report-extraction
description: Extract financial-report content from uploaded images or PDF files by first running the system tool named ocr and inspecting its actual response. Use when the user mentions 财报提取, 财报 OCR, annual reports, quarterly reports, prospectuses, financial statements, or asks to recognize/extract financial-report images or PDFs.
---

# 财报提取

## Scope

This first version only covers the intake and OCR-recognition step for financial-report extraction.

Use this skill when the user uploads or references an image/PDF containing a financial report, announcement, prospectus, annual report, quarterly report, or financial-statement table.

## Workflow

1. Confirm the uploaded file exists and is an image or PDF.
2. Call the system tool named `ocr` to recognize the uploaded file.
3. Inspect the actual OCR response shape before extracting anything.
4. Treat the returned OCR text/table content as the source of truth for later extraction.
5. Preserve the complete raw OCR response for later evidence. When present, keep:
   - task/document identifiers such as `id`
   - source-file fields such as `original_filename`
   - text arrays such as `vlm_text`
   - page-level text, blocks, table fragments, Markdown, HTML, or structured table data
   - the original order of all text/table fragments
6. Report whether OCR succeeded, then summarize what was recognized at a high level.

## OCR Output Handling

The `ocr` tool may return different JSON shapes depending on the input file and OCR backend behavior. Do not assume every response exactly matches one schema.

This is a reference example only:

```json
{
  "vlm_text": [
    "<div align=\"center\">\n\n# 利润表\n\n</div>",
    "编制单位：吴江市舜天化纤有限公司",
    "2018年12月",
    "单位：元",
    "<table border=\"1\"><tr><td>项目</td><td>行次</td><td>本月数</td><td>本年累计数</td></tr></table>"
  ],
  "id": "aeead0d4-d88a-417c-98c2-24159dac344d",
  "original_filename": "Snipaste_2026-05-09_14-51-25.png"
}
```

OCR text may appear in fields such as `vlm_text`, `text`, `pages`, `blocks`, `tables`, or another tool-specific field. `vlm_text`, when present, may contain Markdown, plain text, or HTML table fragments. Do not discard markup, because table HTML can carry row and column structure for later financial-statement extraction.

If the response shape is unfamiliar, first summarize the available top-level keys, then identify which fields contain recognized text or tables.

## Minimal Success Criteria

OCR is successful when:

- the `ocr` tool returns a JSON object,
- at least one field contains recognized text, table content, or structured OCR blocks,
- the response can be tied back to the uploaded source file directly or through conversation context.

## Guardrails

- Do not invent OCR text, financial figures, company names, reporting periods, or table values.
- Do not continue into financial-statement extraction until OCR has completed successfully.
- If OCR fails, explain the failure and ask the user to upload a clearer image/PDF or provide the OCR output manually.
- If the user asks for deeper extraction after OCR, keep the original OCR field name, fragment, page, block, table, or array index attached to each extracted value when available.
