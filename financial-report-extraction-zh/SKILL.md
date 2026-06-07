---
name: financial-report-extraction-zh
description: 面向上传的财务报表图片或 PDF，提取、校验、标准化，并输出标准表 Excel。支持单文件报表、多文件报表组，以及包含一个或多个报表单元的 PDF。用户提到财报提取、财报 OCR、批量图片、PDF 财报、资产负债表、利润表、损益表、现金流量表、勾稽关系、标准科目映射、标准表校验、annual reports、quarterly reports、prospectuses、financial statements，或要求识别、提取、校验、标准化财报图片/PDF 时使用。
---

# 财报提取

## 核心约定

当用户上传一个或多个包含财务报表表格的图片或 PDF 时，使用本 skill：

- 资产负债表
- 利润表 / 损益表
- 现金流量表

当前版本支持：

- 单页 PDF -> 一张报表
- 多页 PDF -> 一张报表
- 多页 PDF -> 多张报表
- 一张图片对应一张报表
- 多张图片/多个文件组成一张报表

本版本不把一张图片拆分成多个报表单元。PDF 可以仅基于 `vlm_text` 拆分成多个报表组。

始终先调用名为 `ocr` 的系统工具。OCR 输出结构是稳定的；后续提取只使用 `ocr.vlm_text`。

如果 `vlm_text` 缺失、不是字符串数组，或无法拼接成可读内容，停止并请用户重新上传更清晰的文件，或请用户手动确认。不要回退使用其他 OCR 字段。

## 工作流

### 1. OCR

1. 确认上传内容包含图片或 PDF 文件。
2. 对每个上传文件先调用 `ocr`，再进行后续提取。
3. 只读取每个 OCR 响应中的 `vlm_text`。
4. 在会话状态中保留每个原始 OCR 响应。

如果用户只要求 OCR，汇总识别内容后停止。

### 1.5. 规范化批量 OCR 结果

如果用户上传了多个文件，或上传的 PDF 的 OCR 文本包含多个报表单元，读取 `references/batch-image-workflow.md`。

基于 OCR 文本对报表单元进行分组、拆分和排序，不基于上传顺序。存在多个组时，请用户确认推断出的分组和顺序。确认后，将 OCR 结果规范化为：

```json
{
  "statement_vlm_texts": [
    ["报表1第1段", "报表1第2段"],
    ["报表2第1段"]
  ]
}
```

对于单图片报表，`statement_vlm_texts` 只有一个内层数组，该数组包含这张图片的 `vlm_text`。对于只包含一张报表的单个 PDF，只有一个内层数组，该数组包含该 PDF 报表的 `vlm_text`。对于包含多张报表的 PDF，将该 PDF 的 `vlm_text` 拆成多个内层数组，每个数组对应一个报表单元。

对于多文件上传或包含多张报表的单个 PDF，在用户确认分组后，使用 `scripts/prepare_batch_manifest.py` 创建 `batch_manifest.json`。

### 2. 将报表 `vlm_text` 映射为原始 JSON

按顺序逐个处理已确认的报表组。对每个组，按用户确认的组内原始顺序，用换行符拼接该组的内层 `vlm_text` 数组。

只从拼接后的报表 `vlm_text` 进行映射。不要从图片/PDF、文件名、OCR 元数据或非 `vlm_text` 字段推断信息。

从明确文本中识别报表类型，然后生成匹配的原始表 JSON schema。仅在映射或校验 JSON 形状时读取 `references/target-json-schema.md`。

如果用户明确只要求提取 JSON，只输出裸 JSON object，然后停止。

### 3. 原始表勾稽校验

- 对 `资产负债表` 和 `利润表`，读取 `references/reconciliation-rules.md` 并执行勾稽校验。
- 对 `现金流量表`，本版本跳过勾稽校验，并将映射得到的 JSON 视为已校验。

如果勾稽通过，自动继续。若勾稽失败，读取 `references/correction-workflow.md`，展示规定的失败响应，并等待用户选择修正路径。

### 4. 修正循环

仅在勾稽失败后使用。

- 自动修正路径：提出确定性的修正方案，并且只在用户确认后应用。
- Excel 编辑路径：读取 `references/excel-editing.md`，用 `scripts/json_to_excel.py` 生成可编辑 Excel，记住其路径；用户表示平台编辑已保存后，再用 `scripts/excel_to_json.py` 转回 JSON。
- 重新上传路径：从 OCR 重新开始。

每次修正后，重新执行步骤 3。勾稽失败时不得继续。

### 5. 标准科目映射

原始表 JSON 校验通过后，读取 `references/standardization-workflow.md`。

只使用一个映射参考：

- `资产负债表` -> `references/standard-subject-mapping-balance-sheet.md`
- `利润表` / `损益表` -> `references/standard-subject-mapping-income-statement.md`
- `现金流量表` -> `references/standard-subject-mapping-cash-flow.md`

生成 subject mapping JSON，其 key 必须与运行时原始科目列表完全一致。然后调用 `scripts/prepare_standard_mapping_files.py` 和系统工具 `convert_to_standard_table`。

### 6. 标准表校验

使用 `scripts/save_standard_table.py` 保存 `convert_to_standard_table` 的结果，然后调用 `validate_standard_table`。

如果校验通过，自动继续。若校验失败，读取 `references/standardization-workflow.md`，展示规定的失败响应，并等待用户选择修正路径。

### 7. 输出标准表 Excel

标准表校验通过后，调用 `standard_table_to_excel`。

对于单个报表组，成功时只输出：

**标准表校验通过**

对于多个报表组，每个组成功后输出带上下文的成功行，并继续处理下一组。所有组成功后，输出 `references/batch-image-workflow.md` 中定义的批量汇总。

## 会话状态

本 skill 激活期间，跨轮次保留以下值：

- 原始 OCR 响应和拼接后的 `vlm_text`
- `statement_vlm_texts`
- 多文件上传场景下的 batch manifest 路径、批量分组、当前组索引、已完成组
- 映射得到的原始表 JSON
- 原始上传文件名
- 勾稽失败信息和修正方案（如有）
- 已生成的可编辑原始表 Excel 路径（如有）
- 任务输出目录
- `original_validated.json`、`subject_mapping.json` 和 `standard_table.json` 的路径
- 最新标准表 JSON 和校验结果

当用户说 `继续`、`已保存`、`保存好了` 或 `编辑好了` 时，从已记住的 Excel 路径继续。只有在会话状态和结果目录查找都失败时，才向用户询问路径。

## 全局防护规则

- 不要编造 OCR 文本、财务数字、日期、单位、行、列或映射关系。
- 不要使用 `vlm_text` 之外的 OCR 字段进行提取。
- 在用户确认推断出的分组和顺序前，不要处理多个报表组。
- 本版本不要把一张图片拆分成多个报表单元；请用户拆分图片，或确认只处理其中一张报表。
- 对 PDF，仅使用 `vlm_text` 中明确的报表边界拆分多个报表单元，并在处理前请用户确认拆分。
- 不要依赖上传顺序进行批量分组或排序。
- 后续批量组暂停或被替换时，不要重新运行已完成的组。
- 批量场景中如用户重新上传替换文件，除非只有一个已暂停的当前组，否则必须要求用户说明要替换哪个报表组。
- 勾稽校验或标准表校验失败后，不要继续。
- JSON-only 成功输出不要包在 Markdown 中。
- 当平台编辑流程适用时，不要要求用户下载、上传、重新上传或发回生成的 Excel。
