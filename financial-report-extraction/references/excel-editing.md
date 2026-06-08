# Excel Editing

Use this reference only when the user chooses platform Excel editing after reconciliation fails.

## Generate Editable Excel

Call `scripts/json_to_excel.py` with the Step 2 JSON serialized as a string:

```python
json_data_to_excel(
    vlm_text,
    original_filename,
    json_out_dir=task_dir,
    sheet_name="Sheet1",
    abnormal_items=None,
)
```

- `vlm_text`: the mapped original-table JSON serialized with Chinese text preserved.
- `original_filename`: uploaded file name, used to derive the Excel file name.
- `json_out_dir`: the Step 0 task output directory, `workspace/{username}/result/{original_filename_stem}_{yyyyMMdd_HHmmss}/`.
- `sheet_name`: prefer the mapped `表名`.
- `abnormal_items`: reconciliation abnormal rows, preferably as dictionaries.

Always pass the remembered `task_dir`. If `json_out_dir` is omitted, the script creates a new timestamped directory, which should be avoided during the skill workflow.

The workbook should highlight abnormal rows or cells. Do not include raw OCR text, OCR metadata, or internal reconciliation structures.

## User Response After Generation

Tell the user the Excel is ready for online editing in the platform. You may include the generated path/resource id, workbook summary, highlighted rows/cells, and the next platform action.

Do not use wording that asks the user to download, upload, re-upload, or send back the Excel.

Remember the generated Excel path.

## Continue After Save

When the user says `继续`, `已保存`, `保存好了`, `编辑好了`, or otherwise indicates online editing is complete:

1. Use the recorded generated Excel path.
2. If state was lost, infer the current user's result directory and use the most recently modified `.xlsx`.
3. Ask for a path only if both lookup methods fail or are ambiguous.
4. Call `scripts/excel_to_json.py`.
5. Validate the output against `references/target-json-schema.md`.
6. Rerun reconciliation.
