# 标准化流程

仅在原始表 JSON 已校验通过后，或标准表校验失败后使用。

## 共享输出目录

所有 JSON/Excel 产物都复用步骤 1 的 `task_dir`。不要创建第二个带时间戳目录，也不要把正式产物写到临时目录。批量组保留 manifest 中的 `file_prefix`，例如 `group_1_`。

## 科目映射与转换

1. 从 `validated_json["表格数据"][].科目名称` 提取原始科目；保留顺序和原文。只在映射 prompt 输入中去重，不修改 `validated_json`。
2. 按报表类型只读取一个映射参考。
3. 生成一个 JSON object：key 必须完全等于运行时原始科目列表，value 必须是有效标准科目或 `__IGNORE__`。
4. 写文件前校验：无缺失/多余 key；key 保留原文；value 是非空字符串，不能是 `null`、数组、对象、解释、置信度或组合文本。格式失败时重生成一次，仍失败则停止并说明。
5. 调用 `scripts/prepare_standard_mapping_files.py`，传入 `validated_json`、`subject_mapping`、原文件名、既有 `task_dir`、可选 `standard_subjects` 和 `file_prefix`。
6. 调用平台 `convert_to_standard_table`：参数 `original_table_json_file_path` 使用脚本返回的 `original_table_json_file_path`（或同一个文件路径 `original_validated_json_file_path`），`subject_mapping_json_file_path` 使用脚本返回的 `subject_mapping_json_file_path`，`rpt_type` 为报表类型（`资产负债表`=1，`利润表`/`损益表`=2，`现金流量表`=3）。
7. 用 `scripts/save_standard_table.py` 原样保存转换结果；调用 `save_standard_table` 时传入 `expected_rpt_type=rpt_type`。保存出的 `standard_table.json` 必须是合法 JSON，形如 `{"rpt_type": 2, "standard_table": {"主营业务收入": {"本月数": 1475058.16, "本年累计数": 15200134.15}}}`。该脚本会校验外层结构、写入文件、再读回确认文件内容仍等于转换结果。若保存/结构校验失败，用同一个未修改的转换结果重试保存一次；仍失败则调用一次 `save_repaired_standard_table(conversion_output, rpt_type, task_dir, file_prefix)` 生成修正后的 `standard_table.json`。该修复只能补齐/修正 wrapper，不得改写科目、列名或金额。若修复保存也失败，则停止并说明标准表 JSON 无效，不要继续调用 `validate_standard_table`。

## 校验标准表

调用平台校验前，该路径必须已经通过 `scripts/save_standard_table.py` 的保存/读回校验。然后调用 `validate_standard_table(standard_table_json_file_path)`。

通过/失败判断：

- 优先读取明确字段：`校验是否通过`、`is_valid`、`passed`、`success`、`valid`。
- 明确通过/失败文本也可作为判断。
- 从 `异常数据`、`异常项`、`errors`、`issues`、`failed_items`、`details` 提取异常项。
- 返回结构不清楚时，展示顶层 key 供人工确认并停止。

## 展示用户选项前的映射重试

第一次 `validate_standard_table` 失败后，先执行一次本流程，再展示失败选项。首次校验通过时不执行；不要循环。

产物：

- v1 = 第一次失败的未加版本前缀 `subject_mapping.json` / `standard_table.json`
- v2 = 独立重新生成的完整映射/标准表
- v3 = v1 加上不稳定原始科目的定向重映射

步骤：

1. 保留 v1；不要覆盖未加版本前缀文件。
2. 基于同一份已验证原始 JSON、原始科目列表、报表类型和映射参考，重新生成完整 `subject_mapping_v2`。不要复制 v1。
3. 用 `{file_prefix}v2_` 保存并转换 v2，保存为 `standard_table_v2`，同样遵守本地保存/结构校验失败只重试一次、仍无效则修复保存一次的规则。
4. 调用 `scripts/standard_mapping_retry.py:analyze_mapping_retry(standard_table_v1, standard_table_v2, subject_mapping_v1, subject_mapping_v2)`。
5. 如果没有 `standard_table_diffs` 或没有 `remap_original_subjects`，说明未发现映射不稳定，展示标准表失败响应。
6. 只重映射 `remap_original_subjects`。partial JSON 的 key 必须完全等于该列表，value 必须是有效标准科目或 `__IGNORE__`。上下文包含完整科目列表、映射参考、校验失败详情和 v1/v2 差异。
7. 调用 `merge_subject_mapping(subject_mapping_v1, partial_remap, remap_original_subjects)` 得到 v3。
8. 用 `{file_prefix}v3_` 保存并转换 v3，同样遵守本地保存/结构校验失败只重试一次、仍无效则修复保存一次的规则；然后校验 `standard_table_v3`。
9. v3 通过则作为最新标准表 JSON 路径并进入 Excel 输出；v3 仍失败则用 v3 校验详情展示失败响应。

批量前缀同时保留组和版本：`group_1_v2_`、`group_1_v3_`。

## 最终标准表 Excel 输出

仅在 `validate_standard_table` 通过后使用本流程：

1. 调用 `standard_table_to_excel`，传入最新已通过校验的 `standard_table_json_file_path`；平台支持时同时传 `task_dir` 作为输出目录/路径。这是最终输出的唯一转换器；最终标准表 Excel 不得调用平台其他 skill/tool、通用 spreadsheet 生成器或通用 Excel 写入工具。
2. `standard_table_json_file_path` 只是工具入参。不要把 `standard_table.json`、`v2_standard_table.json` 或 `v3_standard_table.json` 标记为 Excel 输出。
3. 最终输出必须位于 `task_dir`，且以 `.xlsx` 或 `.xls` 结尾；任何 `.json` 路径都无效。
4. 若返回的 Excel 不在 `task_dir`，调用 `ensure_excel_file_in_task_dir(source_path, task_dir)` 并使用复制后的路径。
5. 若返回路径缺失、不存在或不是 Excel，平台支持时用 `task_dir` 重跑；否则停止并说明 Excel 输出路径无效。不要回退使用 `xlsx` 或任何其他能生成 Excel 的工具。
6. 会话状态和批量汇总中只保存、展示最终 Excel 路径。

## 失败响应

严格输出：

**标准表校验失败**

| 异常数据 | 失败原因 |
|---|---|
| ... | ... |

**建议：**

1. ...
2. ...

**请选择处理方式：**

A. 查看自动修正方案
B. 生成标准表 Excel 并在平台上查看
C. 重新上传更清晰文件

不要提供忽略/继续选项。

## 修正选项

- 自动修正：对最新标准表或最新 subject mapping 提出确定、可逆的修正；用户确认后重跑转换/校验。
- Excel 查看：仅为终端人工复核调用 `standard_table_to_excel`，因为没有标准表 Excel-to-JSON 工具。标记为查看用 Excel，不是最终输出；只有 `validate_standard_table` 通过后才继续最终输出。
- 重新上传：从 OCR 重新开始。

只有 `validate_standard_table` 通过后，才继续最终 Excel 输出。
