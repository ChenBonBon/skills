# Excel 编辑

仅当用户在勾稽失败后选择平台 Excel 编辑时，使用本参考文档。

## 生成可编辑 Excel

调用 `scripts/json_to_excel.py`，将步骤 2 的 JSON 序列化为字符串：

```python
json_data_to_excel(
    vlm_text,
    original_filename,
    json_out_dir=task_dir,
    sheet_name="Sheet1",
    abnormal_items=None,
)
```

- `vlm_text`：映射得到的原始表 JSON，序列化时保留中文文本。
- `original_filename`：上传文件名，用于派生 Excel 文件名。
- `json_out_dir`：步骤 0 的任务输出目录，即 `workspace/{username}/result/{original_filename_stem}_{yyyyMMdd_HHmmss}/`。
- `sheet_name`：优先使用映射得到的 `表名`。
- `abnormal_items`：勾稽异常行，优先使用字典形式。

始终传入已记住的 `task_dir`。如果省略 `json_out_dir`，脚本会创建新的带时间戳目录；skill 流程中应避免这种情况。

工作簿应高亮异常行或异常单元格。不要包含原始 OCR 文本、OCR 元数据或内部勾稽结构。

## 生成后的用户响应

告诉用户 Excel 已可在平台中在线编辑。可以包含生成路径/resource id、工作簿摘要、高亮行/单元格，以及下一步平台操作。

措辞中不要要求用户下载、上传、重新上传或发回 Excel。

记住生成的 Excel 路径。

## 保存后继续

当用户说 `继续`、`已保存`、`保存好了`、`编辑好了`，或以其他方式表示在线编辑已完成时：

1. 使用记录的已生成 Excel 路径。
2. 如果状态丢失，推断当前用户的结果目录，并使用最近修改的 `.xlsx`。
3. 仅当两种查找方式都失败或结果有歧义时，才询问路径。
4. 调用 `scripts/excel_to_json.py`。
5. 根据 `references/target-json-schema.md` 校验输出。
6. 重新运行勾稽校验。
