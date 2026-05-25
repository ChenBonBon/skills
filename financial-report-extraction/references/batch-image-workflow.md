# Batch File Workflow

Use this reference only when the user uploads multiple images and/or PDFs.

This version supports:

- `n` files for `n` financial statements.
- `m` files for `n` financial statements where `m > n`, meaning multiple files may form one statement.
- one single-page PDF for one statement.
- one multi-page PDF for one statement.
- one multi-page PDF for multiple statements.
- files may be images or PDFs.

This version does not support one image containing multiple statement units. If OCR indicates one image contains multiple target statements, ask the user to split the image or confirm which one statement to process.

PDFs may contain multiple statement units. Split a PDF into statement groups only from `vlm_text`; do not use page images, OCR metadata, or file names as extraction evidence.

## OCR All Files First

1. Call `ocr` for every uploaded image/PDF before deciding groups.
2. Preserve each raw OCR response in session state.
3. Use only each response's `vlm_text` string array for downstream grouping and extraction.
4. If any file has missing or invalid `vlm_text`, pause and ask the user to re-upload or confirm manually.

## Group And Order Files

After all OCR calls finish, group files into statement units. Each image may belong to only one group. A PDF may produce one group or multiple groups when `vlm_text` clearly contains multiple statement units.

Use OCR text clues to infer both group membership and order within each group:

- explicit table name,
- repeated explicit table names inside one PDF,
- 编制单位,
- 日期 / 期间,
- 单位,
- page or continuation clues,
- table header columns,
- first and last subject names,
- ending subjects such as `资产总计`, `负债和所有者权益总计`, `净利润`, or `现金及现金等价物净增加额`.

Do not rely on upload order. Do not rely only on file name order.

The normalized internal shape is:

```json
{
  "statement_vlm_texts": [
    ["报表1第1段", "报表1第2段"],
    ["报表2第1段"]
  ]
}
```

Each inner array is one complete statement's `vlm_text`. If a group contains multiple files, concatenate their `vlm_text` arrays in the confirmed group order.

PDF handling:

- Single-page PDF for one statement: one group with that PDF's `vlm_text`.
- Multi-page PDF for one statement: one group with that PDF statement's full `vlm_text` in OCR order.
- Multi-page PDF for multiple statements: split the PDF `vlm_text` into one group per statement unit. Use explicit boundaries such as `资产负债表`, `利润表`/`损益表`, `现金流量表`, repeated `编制单位`, repeated `日期`/`单位`, and final-row markers.
- If the split is ambiguous, ask the user to confirm the statement boundaries before processing.

## User Confirmation

Always ask the user to confirm the inferred groups in this first batch-file version.

Show a concise table:

| 组号 | 顺序 | 来源文件 | 识别表名 | 编制单位 | 日期 | 说明 |
|---|---:|---|---|---|---|---|
| 1 | 1 | B.png | 资产负债表 | ... | ... | 表头和资产部分 |
| 1 | 2 | A.png | 资产负债表 | ... | ... | 负债和权益部分 |
| 2 | 1 | C.pdf | 利润表 | ... | ... | PDF 第 1 个报表单元 |
| 3 | 1 | C.pdf | 现金流量表 | ... | ... | PDF 第 2 个报表单元 |

The user may reply:

- `确认`
- `调整顺序：第1组 B.png,A.png`
- `调整分组：第1组 B.png,A.png；第2组 C.png`
- `调整PDF拆分：第1组 C.pdf 资产负债表；第2组 C.pdf 利润表`
- `取消` or `重新上传`

After confirmation, use the confirmed group order to build `statement_vlm_texts`.

## Batch Manifest

For any multi-file upload or single PDF containing multiple statements, create a batch directory:

```text
workspace/{username}/result/{batch_stem}_batch/
```

Create `batch_manifest.json` in that directory with `scripts/prepare_batch_manifest.py`.

Use group task directories:

```text
workspace/{username}/result/{batch_stem}_batch/{group_first_file_stem}_group_1/
workspace/{username}/result/{batch_stem}_batch/{group_first_file_stem}_group_2/
```

`batch_stem` should be stable for the upload batch. Prefer the first file in the confirmed first group. Each `group_first_file_stem` comes from the first file in that confirmed group. When one PDF produces multiple groups, use the same PDF stem plus each group index to keep task directories unique.

## Serial Processing

Process groups serially in confirmed order.

For each group:

1. Join that group's `vlm_text` array with newline separators.
2. Run the existing single-statement workflow from original JSON mapping through standard-table Excel output.
3. If the group succeeds, continue to the next group.
4. If the group needs user action, pause the entire batch at that group.

When pausing, include context:

```text
当前处理：第 2/5 组
来源文件：B.png, A.png
识别表名：资产负债表
```

After the user resolves the issue, resume from the paused group. Do not rerun completed groups.

## Re-Upload Replacement

If a group fails and the user chooses re-upload, the user must specify which report group is being replaced.

In serial mode, default to the current paused group but still say which group will be replaced. In future parallel mode, if multiple groups are failed and the user does not specify a group, ask which group to replace.

Replacing a group does not rerun completed groups.

## Batch Success Output

Single-group mode keeps the existing final success output:

```text
标准表校验通过
```

For multiple groups, after each group succeeds, output a short contextual success line:

```text
第 1/3 组：资产负债表 标准表校验通过
```

After all groups succeed, output a final summary table:

| 组号 | 来源文件 | 表名 | 状态 | 标准表 Excel |
|---|---|---|---|---|
| 1 | B.png,A.png | 资产负债表 | 标准表校验通过 | ... |
| 2 | C.png | 利润表 | 标准表校验通过 | ... |

If the batch pauses on a failed group, do not output the final batch-complete summary.
