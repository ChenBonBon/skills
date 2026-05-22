# Target Original-Table JSON

Use this reference only when mapping joined `vlm_text` to the original-table JSON or validating that JSON shape.

All output values must be strings. Preserve source date and number formats; do not normalize dates, remove commas, convert parentheses, convert `--` to `0`, or add missing decimals.

## 资产负债表

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

## 利润表 / 损益表

Output the standard table name `利润表`.

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

## 现金流量表

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

- `表名` must be one supported statement type. If not, ask for manual confirmation.
- `编制单位`, `日期`, and `单位` may be empty strings if missing from `vlm_text`.
- Preserve the main table row order from `vlm_text`.
- Keep group rows, heading rows, subtotal rows, and total rows if they are part of the main financial table.
- Use `""` for missing target amount fields.
- Do not output `行次`.
- Drop auxiliary columns and extra columns outside the target schema.
- Exclude signatures, preparer/reviewer fields, page numbers, seals, supplementary notes, and OCR noise.

## Manual Confirmation

Use a Markdown table, not partial JSON, when mapping cannot proceed safely.

Manual confirmation is required when:

- `vlm_text` cannot be joined into readable content.
- statement type cannot be identified from explicit table-name text.
- multiple target tables appear in one upload.
- the main financial table cannot be located.
- `科目名称` cannot be mapped from `vlm_text`.

If only amount columns cannot be matched, still output JSON and set unmatched amount fields to `""`.
