# 标准化工作流

仅在原始表 JSON 已校验通过后，或标准表校验失败后，使用本参考文档。

## 任务目录

使用步骤 0 创建的任务输出目录：

```text
workspace/{username}/result/{original_filename_stem}_{yyyyMMdd_HHmmss}/
```

该目录由 `scripts/task_outputs.py` 在第一次写入文件前创建一次。整个运行过程中复用已记住的 `task_dir` 来保存所有 JSON 和 Excel 输出。如果无法获得准确的 workspace 根目录，使用当前运行时上下文。不要把生产输出写入临时目录。

## 科目映射

1. 从 `validated_json["表格数据"][].科目名称` 提取运行时原始科目列表。
2. 保留原始顺序和精确文本。
3. 仅在映射 prompt 输入中去除重复科目名称；不要修改 `validated_json`。
4. 根据 `表名` 读取且只读取一个映射参考。
5. 将映射参考中的运行时原始科目占位内容替换为实际科目列表。
6. 输出一个 JSON object；其 key 必须与运行时原始科目列表完全一致，value 为标准科目名称或 `__IGNORE__`。

写入文件前，校验：

- `subject_mapping` 是 JSON object。
- 其 key 集合与去重后的运行时原始科目列表完全一致。
- 没有缺失 key 或额外 key。
- 每个 key 都精确保留原始科目文本。
- 每个 value 都是非空字符串。
- 每个 value 要么是选中的参考标准科目，要么严格等于 `__IGNORE__`。
- value 不能是 `null`、数组、对象、解释、置信度或组合文本。

如果校验失败，重新生成一次。若仍失败，简要说明格式失败原因并停止。

## 准备文件并转换

调用 `scripts/prepare_standard_mapping_files.py`：

```python
prepare_standard_mapping_files(
    validated_json,
    subject_mapping,
    original_filename,
    result_root=None,
    task_dir=task_dir,
    standard_subjects=None,
    file_prefix="",
)
```

对于多报表批量场景，保持同一个 `task_dir`，并传入该组 manifest 中的 `file_prefix`，例如 `group_1_`。

将返回路径直接用于 `convert_to_standard_table`：

- `original_table_json_file_path`: 返回的原始表 JSON 路径
- `subject_mapping_json_file_path`: 返回的科目映射 JSON 路径
- `rpt_type`: `1` 表示 `资产负债表`，`2` 表示 `利润表` / `损益表`，`3` 表示 `现金流量表`

使用 `scripts/save_standard_table.py` 保存返回的标准表 JSON，并传入同一个 `task_dir` 和同一个组 `file_prefix`（如有）。如果 `convert_to_standard_table` 返回 `{"rpt_type": ..., "standard_table": {...}}` 这样的外层对象，只落盘 `standard_table` 的 value。

## 标准表 Excel 输出

当标准表校验通过后调用 `standard_table_to_excel`，或用户选择生成标准表 Excel 查看时：

1. 传入最新已通过校验的 `standard_table_json_file_path`、`rpt_type`；如果平台工具支持输出目录/输出路径参数，同时传入已记住的 `task_dir`。
2. `standard_table_json_file_path` 只能作为工具入参。不要把 `standard_table.json`、`v2_standard_table.json` 或 `v3_standard_table.json` 标记或展示为 Excel 输出。
3. Excel 最终必须位于步骤 0 的任务输出目录下。
4. 工具返回的输出路径必须是以 `.xlsx` 或 `.xls` 结尾的 Excel 文件路径。任何 `.json` 路径在这一步都无效，即使它指向已通过校验的标准表 JSON。
5. 如果工具返回的文件路径不在 `task_dir` 下，调用 `scripts/task_outputs.py` 的 `ensure_excel_file_in_task_dir(source_path, task_dir)`，并使用复制后的 Excel 路径。
6. 如果工具返回路径缺失、文件不存在、或不是 Excel 路径，使用 `task_dir` 重新调用该工具（若支持）；否则停止并说明标准表 Excel 输出路径无效。
7. 将最终位于 `task_dir` 下的 Excel 路径保存到会话状态和批量汇总中。向用户展示输出文件路径时，只展示这个 Excel 路径。

## 校验标准表

调用 `validate_standard_table`，参数为：

- `standard_table_json_file_path`: `standard_table.json` 的路径
- `rpt_type`: `1`、`2` 或 `3`

通过/失败判断：

- 优先使用明确字段，例如 `校验是否通过`、`is_valid`、`passed`、`success` 或 `valid`。
- 如果文本清楚表示校验通过，视为通过。
- 从 `异常数据`、`异常项`、`errors`、`issues`、`failed_items` 或 `details` 等字段提取异常项。
- 如果返回形状不清楚，展示包含顶层 key 的人工确认表并停止。

## 展示用户选项前的标准映射重试

第一次 `validate_standard_table` 失败后，先针对该报表组执行一次本流程，再展示“标准表校验失败”响应。第一次校验通过时不要执行。本流程每个报表组最多执行一次，不要无限循环。

产物含义：

- `subject_mapping_v1`: 生成第一次失败的 `standard_table_v1` 的映射
- `standard_table_v1`: 第一次转换得到的标准表
- `subject_mapping_v2`: 独立重新生成的完整科目映射
- `standard_table_v2`: 由 `subject_mapping_v2` 转换得到的标准表
- `subject_mapping_v3`: 只重映射不稳定原始科目后得到的最终完整映射
- `standard_table_v3`: 由 `subject_mapping_v3` 转换得到的标准表

重试步骤：

1. 将第一次失败的映射和标准表保存为 `subject_mapping_v1` 和 `standard_table_v1`。已有的未加版本前缀 `subject_mapping.json` 和 `standard_table.json` 就是 v1；重试过程中不要覆盖它们。
2. 基于同一个已验证原始表 JSON、运行时原始科目列表、报表类型和映射参考，重新生成完整的 `subject_mapping_v2`。这次映射必须独立生成，不要复制 `subject_mapping_v1`。
3. 在同一个 `task_dir` 下保存并转换 `subject_mapping_v2`；使用带版本的 `file_prefix`，例如 `{file_prefix}v2_`。
4. 将转换结果保存为 `standard_table_v2`。
5. 调用 `scripts/standard_mapping_retry.py` 的 `analyze_mapping_retry(standard_table_v1, standard_table_v2, subject_mapping_v1, subject_mapping_v2)`。
6. 如果 `standard_table_diffs` 为空，或 `remap_original_subjects` 为空，说明未发现映射不稳定问题；基于最新校验失败结果展示“标准表校验失败”响应。
7. 只针对 `remap_original_subjects` 重新映射。输出必须是 partial JSON object，key 必须与 `remap_original_subjects` 完全一致，value 必须是有效标准科目或 `__IGNORE__`。上下文需要包含完整原始科目列表、映射参考、校验失败详情、以及 v1/v2 差异报告。
8. 调用 `merge_subject_mapping(subject_mapping_v1, partial_remap, remap_original_subjects)` 得到 `subject_mapping_v3`。
9. 在同一个 `task_dir` 下保存并转换 `subject_mapping_v3`；使用带版本的 `file_prefix`，例如 `{file_prefix}v3_`。
10. 将转换结果保存为 `standard_table_v3`，然后对 `standard_table_v3` 的文件路径调用 `validate_standard_table`。
11. 如果 `standard_table_v3` 校验通过，将 v3 作为最新标准表 JSON/路径，并继续输出标准表 Excel。v3 JSON 路径只能作为 `standard_table_to_excel` 入参，不要作为最终输出文件展示。
12. 如果 `standard_table_v3` 仍未通过，使用 v3 的校验结果展示“标准表校验失败”响应。

如果批量报表组已有 `group_1_` 这样的组前缀，版本前缀必须保留组前缀，例如 `group_1_v2_` 和 `group_1_v3_`。

## 标准表失败响应

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

## 标准表修正

- 自动修正路径：对最新的 `standard_table.json` 提出确定、可逆的修正；如果根因是映射，则修正最新的 subject mapping 后重新运行转换。如果自动标准映射重试已经产生 v3，则基于 v3 继续处理。
- 标准表 Excel 路径：调用 `standard_table_to_excel`，并遵循上方“标准表 Excel 输出”规则；这是终端查看/人工复核路径，因为没有标准表 Excel 转 JSON 工具。
- 重新上传路径：从 OCR 重新开始。

只有在 `validate_standard_table` 通过后，才继续最终 Excel 输出。
