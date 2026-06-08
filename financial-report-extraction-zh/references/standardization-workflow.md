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

使用 `scripts/save_standard_table.py` 保存返回的标准表 JSON，并传入同一个 `task_dir` 和同一个组 `file_prefix`（如有）。

## 校验标准表

调用 `validate_standard_table`，参数为：

- `standard_table_json_file_path`: `standard_table.json` 的路径
- `rpt_type`: `1`、`2` 或 `3`

通过/失败判断：

- 优先使用明确字段，例如 `校验是否通过`、`is_valid`、`passed`、`success` 或 `valid`。
- 如果文本清楚表示校验通过，视为通过。
- 从 `异常数据`、`异常项`、`errors`、`issues`、`failed_items` 或 `details` 等字段提取异常项。
- 如果返回形状不清楚，展示包含顶层 key 的人工确认表并停止。

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

- 自动修正路径：对 `standard_table.json` 提出确定、可逆的修正；如果根因是映射，则修正 `subject_mapping.json` 后重新运行转换。
- 标准表 Excel 路径：调用 `standard_table_to_excel`；这是终端查看/人工复核路径，因为没有标准表 Excel 转 JSON 工具。
- 重新上传路径：从 OCR 重新开始。

只有在 `validate_standard_table` 通过后，才继续最终 Excel 输出。
