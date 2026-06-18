---
name: financial-report-extraction-zh
description: 面向上传的财务报表图片或 PDF，提取、校验、标准化，并输出标准表 Excel。支持单文件报表、多文件报表组，以及包含一个或多个报表单元的 PDF。用户提到财报提取、财报 OCR、批量图片、PDF 财报、资产负债表、利润表、损益表、现金流量表、勾稽关系、标准科目映射、标准表校验、annual reports、quarterly reports、prospectuses、financial statements，或要求识别、提取、校验、标准化财报图片/PDF 时使用。
---

# 财报提取

## 适用范围

用于上传的财务报表图片/PDF：`资产负债表`、`利润表`/`损益表`、`现金流量表`。支持单/多图片、单/多页 PDF、以及包含多个报表单元的 PDF。

始终先调用平台 `ocr`。后续只使用 `ocr.vlm_text`；如果缺失、不是字符串数组或拼接后不可读，停止并要求更清晰文件/人工确认。不要从图片/PDF 元数据、文件名或非 `vlm_text` 字段推断。

## 工作流

1. **任务目录**：OCR 前先把本 skill 的 `scripts/` 目录加入 `sys.path`，再用 `from task_outputs import create_task_output_dir, save_ocr_results` 导入工具。除非当前工作目录就是 skill 根目录，否则不要使用 `from scripts.task_outputs`。调用一次 `create_task_output_dir(...)`，平台提供 `username` 时传入。将返回对象保存为 `task_output`，再设置 `task_dir = task_output["task_dir"]`。本轮所有 JSON/Excel 都复用这个字符串 `task_dir`。有 username 时默认路径：`workspace/{username}/result/{original_filename_stem}_{yyyyMMdd_HHmmss}/`。

2. **OCR**：每个上传文件都调用 `ocr`。每次返回后立刻把原始 OCR 返回对象追加到列表，并用 `save_ocr_results(...)` 原样保存到 `ocr_results.json`。不得总结、脱敏、规范化或写占位内容。用户只要求 OCR 时，汇总识别内容后停止。

3. **批量/PDF 分组**：多文件或多报表 PDF 时读取 `references/batch-image-workflow.md`。按 OCR 文本分组、拆分、排序，不按上传顺序；多组需用户确认。确认后在既有 `task_dir` 创建 `batch_manifest.json`。

4. **原始 JSON**：按确认后的组串行处理。每组用换行拼接 `vlm_text`，从明确文本识别报表类型，再按 `references/target-json-schema.md` 映射。可见金额必须进入对应字段；只有真实空白/缺失才用 `""`。无法安全归列时要求人工确认。用户只要 JSON 时输出裸 JSON 后停止。

5. **原始表勾稽**：`资产负债表` 和 `利润表` 读取 `references/reconciliation-rules.md`；`现金流量表` 跳过。勾稽零容差：任何非零差额，包括 `0.01`，都失败。失败时仅在疑似公式构造错误（如运算符错误、重复计算）时执行 `reconciliation-rules.md` 中的一次性公式重试；疑似 OCR 错误或原始表本身不平时不得重试。若重试仍失败或跳过重试，再读取 `references/correction-workflow.md`，展示规定响应并等待选择。

6. **修正循环**：仅勾稽失败后使用。自动修正必须确定、可逆且经用户确认。Excel 编辑读取 `references/excel-editing.md`，用 `json_to_excel.py` 生成，用户保存后用 `excel_to_json.py` 转回。重新上传从 OCR 开始。每次修正后重跑步骤 5。

7. **标准科目映射**：原始 JSON 通过后读取 `references/standardization-workflow.md`，并只读取一个映射参考：

- `资产负债表`: `references/standard-subject-mapping-balance-sheet.md`
- `利润表`/`损益表`: `references/standard-subject-mapping-income-statement.md`
- `现金流量表`: `references/standard-subject-mapping-cash-flow.md`

生成 key 完全等于运行时原始科目列表的完整 subject mapping。调用 `prepare_standard_mapping_files.py`，再调用平台 `convert_to_standard_table`。

8. **标准表校验**：用 `save_standard_table.py` 原样保存 `convert_to_standard_table` 的返回值。调用 `validate_standard_table`。首次失败时先执行 `standardization-workflow.md` 的一次性标准映射重试；v3 仍失败才展示失败选项并等待。

9. **标准表 Excel**：标准表校验通过后，用最新通过的标准表 JSON 路径调用平台 `standard_table_to_excel`；支持时传入 `task_dir`。这是最终标准表 Excel 转换唯一允许的工具；本步骤不得调用平台 `xlsx` skill/tool、通用 spreadsheet 生成器或通用 Excel 写入工具。如果 `standard_table_to_excel` 不可用，或无法返回有效 Excel 路径，停止并说明必需工具不可用/返回无效，不要用其他 Excel 工具替代。JSON 路径只作入参，最终输出必须是 `.xlsx`/`.xls`，`.json` 一律无效。外部路径用 `ensure_excel_file_in_task_dir(...)` 复制回 `task_dir`。单组成功输出必须包含 `标准表校验通过` 和 `标准表 Excel：{final_standard_table_excel_path}`；批量输出见 `batch-image-workflow.md`。

## 会话状态

保留：原始 OCR 响应、`ocr_results.json`、`statement_vlm_texts`、batch manifest/分组/当前组/已完成组、原始上传文件名、原始 JSON、勾稽失败和修正方案/公式重试结果、可编辑原始表 Excel、`task_dir`、`original_validated.json`、`subject_mapping.json`、`standard_table.json`、标准映射重试 v1/v2/v3、最终标准表 Excel 路径、最新标准表校验结果。

用户说 `继续`、`已保存`、`保存好了` 或 `编辑好了` 时，从已记住的 Excel/会话路径继续；只有会话状态和结果目录查找都失败时才问路径。

## 防护规则

- 不要编造 OCR 文本、财务数字、日期、单位、行、列、映射或修正。
- 不要使用 `vlm_text` 之外的 OCR 字段；不要把处理后的 OCR 写入 `ocr_results.json`。
- 步骤 1 后不要创建第二个带时间戳的输出目录。
- 本版本不把一张图片拆成多个报表单元。
- PDF 只按 `vlm_text` 中明确边界拆分，并在处理前请用户确认。
- 多组确认前不要处理；不要依赖上传顺序；后续组暂停/替换时不要重跑已完成组。
- 批量替换上传时，除非仅有一个暂停组，否则要求用户说明替换哪个报表组。
- 勾稽或标准表校验失败后不得继续。
- JSON-only 成功输出不要包 Markdown。
- 最终标准表 Excel 只能由 `standard_table_to_excel` 生成；不得使用 `xlsx` skill/tool 或任何通用 spreadsheet/Excel 写入工具替代。
- 平台编辑流程适用时，不要要求用户下载、上传、重新上传或发回生成的 Excel。
