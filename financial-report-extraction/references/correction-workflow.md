# Original-Table Correction Workflow

Use this reference only after original-table reconciliation fails.

## Failure Response

Output exactly four sections in order:

**勾稽关系校验失败**

Then show failed data and reasons:

| 异常数据 | 失败原因 |
|---|---|
| ... | ... |

Then show:

**建议：**

1. ...
2. ...

Then show:

**请选择处理方式：**

A. 查看自动修正方案
B. 生成 Excel 并在平台上在线编辑
C. 重新上传更清晰文件

Do not offer an ignore/continue option. Do not output a partial corrected JSON.

## Auto-Fix Plan

Auto-fix may be offered only for deterministic, explainable, reversible issues, such as a unique OCR amount-column misalignment, a uniquely calculable missing total, or consistently misread period headers.

Do not auto-fix genuinely unbalanced statements. Do not fabricate numbers.

When the user asks for an auto-fix plan, output:

| 问题类型 | 涉及科目 | 当前值 | 建议值 | 推导依据 | 影响公式 | 风险等级 |
|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | 低 |

Only low-risk, unique corrections may be included. Apply changes only after the user confirms, then rerun reconciliation.

## Excel Editing Path

Use the Excel editing path only after the user chooses it. Read `references/excel-editing.md` before generating or consuming Excel.

After edited Excel is converted back to JSON, validate that it matches the original-table JSON schema, then rerun reconciliation.
