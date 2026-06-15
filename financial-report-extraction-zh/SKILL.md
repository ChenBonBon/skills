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

### 1. 创建任务输出目录

在第一次写入文件之前，使用 `scripts/task_outputs.py` 创建一个全局任务输出目录：

```python
create_task_output_dir(original_filename, result_root=None, timestamp=None)
```

本次运行中所有需要写入的文件都使用返回的 `task_dir`。默认路径为：

```text
workspace/{username}/result/{original_filename_stem}_{yyyyMMdd_HHmmss}/
```

系统时间戳只生成一次，后续步骤复用同一个 `task_dir`；不要在后续步骤创建新的带时间戳目录。

- 单文件上传时，用该文件名在 OCR 前创建 `task_dir`。
- 多文件上传时，如果平台提供批次名，使用批次名创建 `task_dir`；否则使用第一个上传源文件名。不要等分组确认后才创建 `task_dir`，因为原始 OCR 必须在模型有机会总结压缩前就落盘。

### 2. OCR

1. 确认上传内容包含图片或 PDF 文件。
2. 对每个上传文件先调用 `ocr`，再进行后续提取。
3. 只读取每个 OCR 响应中的 `vlm_text`。
4. 每次 OCR 调用返回后，立即把 OCR 工具的原始返回对象追加到原始 OCR 响应列表，并用 `scripts/task_outputs.py` 将该未修改列表保存到 `task_dir` 下的 `ocr_results.json`。
5. 不要总结、脱敏、缩短、规范化、重构 OCR 内容，也不要用 `see original OCR` 等占位内容替换；`ocr_results.json` 只能包含 OCR 工具的原始输出。
6. 在会话状态中保留每个原始 OCR 响应和 `ocr_results.json` 路径。

如果用户只要求 OCR，汇总识别内容后停止。

### 3. 规范化批量 OCR 结果

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

对于多文件上传或包含多张报表的单个 PDF，在用户确认分组后，使用 `scripts/prepare_batch_manifest.py` 创建 `batch_manifest.json`。传入已有的 `task_dir` 作为 `batch_dir`；不要创建单独的批量目录。

### 4. 将报表 `vlm_text` 映射为原始 JSON

按顺序逐个处理已确认的报表组。对每个组，按用户确认的组内原始顺序，用换行符拼接该组的内层 `vlm_text` 数组。

只从拼接后的报表 `vlm_text` 进行映射。不要从图片/PDF、文件名、OCR 元数据或非 `vlm_text` 字段推断信息。

从明确文本中识别报表类型，然后生成匹配的原始表 JSON schema。仅在映射或校验 JSON 形状时读取 `references/target-json-schema.md`。

当 `vlm_text` 中对应科目行存在可见金额文本时，不要把金额字段留空。只有来源单元格确实缺失或为空时才使用 `""`；如果可见金额无法安全归入目标列，要求人工确认。

如果用户明确只要求提取 JSON，只输出裸 JSON object，然后停止。

### 5. 原始表勾稽校验

- 对 `资产负债表` 和 `利润表`，读取 `references/reconciliation-rules.md` 并执行勾稽校验。
- 对 `现金流量表`，本版本跳过勾稽校验，并将映射得到的 JSON 视为已校验。
- 勾稽校验采用零容差：任何非零公式差额，包括 `0.01`、`0.02` 或 `0.03`，都必须判定为失败。不得将差额解释为 OCR 噪声或四舍五入后继续判定通过。

如果勾稽通过，自动继续。若勾稽失败，读取 `references/correction-workflow.md`，展示规定的失败响应，并等待用户选择修正路径。

### 6. 修正循环

仅在勾稽失败后使用。

- 自动修正路径：提出确定性的修正方案，并且只在用户确认后应用。
- Excel 编辑路径：读取 `references/excel-editing.md`，用 `scripts/json_to_excel.py` 生成可编辑 Excel，记住其路径；用户表示平台编辑已保存后，再用 `scripts/excel_to_json.py` 转回 JSON。
- 重新上传路径：从 OCR 重新开始。

每次修正后，重新执行步骤 5。勾稽失败时不得继续。

### 7. 标准科目映射

原始表 JSON 校验通过后，读取 `references/standardization-workflow.md`。

只使用一个映射参考：

- `资产负债表` -> `references/standard-subject-mapping-balance-sheet.md`
- `利润表` / `损益表` -> `references/standard-subject-mapping-income-statement.md`
- `现金流量表` -> `references/standard-subject-mapping-cash-flow.md`

生成 subject mapping JSON，其 key 必须与运行时原始科目列表完全一致。然后带着已有的 `task_dir` 调用 `scripts/prepare_standard_mapping_files.py`，再调用系统工具 `convert_to_standard_table`。

### 8. 标准表校验

使用 `scripts/save_standard_table.py` 将 `convert_to_standard_table` 的结果保存到已有的 `task_dir`；落盘文件必须只包含 `standard_table` 对象本身，不能包含外层 `rpt_type`/`standard_table` 包装。然后调用 `validate_standard_table`。

如果校验通过，自动继续。若校验失败，读取 `references/standardization-workflow.md`，并先执行一次标准映射重试流程，再展示用户选项。如果重试得到的 `standard_table_v3` 校验通过，则自动继续。如果仍未通过，展示规定的失败响应，并等待用户选择修正路径。

### 9. 输出标准表 Excel

标准表校验通过后，使用最新已通过校验的标准表 JSON 路径调用 `standard_table_to_excel`。如果该工具支持输出目录/输出路径参数，传入已记住的 `task_dir`，确保 Excel 生成到任务输出目录下。标准表 JSON 路径只作为该工具的入参，绝不能作为 Excel 输出路径展示。

工具返回后，校验 Excel 文件路径。最终展示的文件路径必须以 `.xlsx` 或 `.xls` 结尾；`standard_table.json` 这类 `.json` 路径即使已通过校验也不是 Excel，必须判定为无效。如果文件不在 `task_dir` 下，使用 `scripts/task_outputs.py` 的 `ensure_excel_file_in_task_dir(...)` 将其复制到 `task_dir`，然后记住并汇报复制后的 Excel 路径。如果返回路径缺失、不是 Excel 路径或文件不存在，使用 `task_dir`/输出目录参数重新调用 `standard_table_to_excel`（若工具支持）；否则停止并说明标准表 Excel 输出路径无效。

对于单个报表组，成功时输出：

**标准表校验通过**

标准表 Excel：`{final_standard_table_excel_path}`

对于多个报表组，每个组成功后输出带上下文的成功行，记住该组最终标准表 Excel 路径，并继续处理下一组。所有组成功后，输出 `references/batch-image-workflow.md` 中定义的批量汇总。

## 会话状态

本 skill 激活期间，跨轮次保留以下值：

- 原始 OCR 响应和拼接后的 `vlm_text`
- `ocr_results.json` 路径
- `statement_vlm_texts`
- 多文件上传场景下的 batch manifest 路径、批量分组、当前组索引、已完成组
- 映射得到的原始表 JSON
- 原始上传文件名
- 勾稽失败信息和修正方案（如有）
- 已生成的可编辑原始表 Excel 路径（如有）
- 任务输出目录
- `original_validated.json`、`subject_mapping.json` 和 `standard_table.json` 的路径
- 标准映射重试产物：`subject_mapping_v1/v2/v3`、`standard_table_v1/v2/v3`、差异报告、以及最新通过校验的标准表路径
- `standard_table_to_excel` 生成的最终标准表 Excel 路径（`.xlsx`/`.xls`）
- 最新标准表 JSON 和校验结果

当用户说 `继续`、`已保存`、`保存好了` 或 `编辑好了` 时，从已记住的 Excel 路径继续。只有在会话状态和结果目录查找都失败时，才向用户询问路径。

## 全局防护规则

- 不要编造 OCR 文本、财务数字、日期、单位、行、列或映射关系。
- 不要使用 `vlm_text` 之外的 OCR 字段进行提取。
- 不要把处理后的 OCR 数据写入 `ocr_results.json`；该文件只保存 OCR 工具的原始返回。
- 不要保存 `...`、`see original OCR`、`truncated` 或 `omitted` 这类 OCR 占位文本。
- 除非平台工具要求自己的输出路径，否则不要把任务文件写到任务输出目录之外。
- 步骤 1 后不要创建第二个带时间戳的输出目录；复用已记住的 `task_dir`。
- 在用户确认推断出的分组和顺序前，不要处理多个报表组。
- 本版本不要把一张图片拆分成多个报表单元；请用户拆分图片，或确认只处理其中一张报表。
- 对 PDF，仅使用 `vlm_text` 中明确的报表边界拆分多个报表单元，并在处理前请用户确认拆分。
- 不要依赖上传顺序进行批量分组或排序。
- 后续批量组暂停或被替换时，不要重新运行已完成的组。
- 批量场景中如用户重新上传替换文件，除非只有一个已暂停的当前组，否则必须要求用户说明要替换哪个报表组。
- 勾稽校验或标准表校验失败后，不要继续。
- JSON-only 成功输出不要包在 Markdown 中。
- 当平台编辑流程适用时，不要要求用户下载、上传、重新上传或发回生成的 Excel。
