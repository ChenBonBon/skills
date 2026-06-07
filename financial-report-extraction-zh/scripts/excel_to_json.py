import json
import re
import openpyxl
from pathlib import Path
from typing import Any, Dict, Optional


def xlsx_to_json(
    xlsx_path: str, json_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    将财务表 xlsx 文件转换为 json 格式，支持利润表和资产负债表。

    Args:
        xlsx_path: xlsx 文件路径
        json_path: 输出 json 文件路径，若为 None 则自动生成

    Returns:
        转换后的字典数据
    """
    input_path = Path(xlsx_path)
    output_path = Path(json_path) if json_path is not None else input_path.with_suffix(".json")

    wb = openpyxl.load_workbook(input_path, data_only=True)
    ws = wb.active
    if ws is None:
        raise ValueError("Excel 文件中未找到工作表")

    result: Dict[str, Any] = {
        "表名": "",
        "编制单位": "",
        "日期": "",
        "单位": "",
        "表格数据": []
    }

    has_monthly = False
    has_yearly = False

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
        row = list(row)
        if row_idx == 1:
            result["表名"] = str(row[0]).strip() if row[0] else ""
            continue

        if row_idx == 2:
            for cell in row:
                if cell:
                    cell_str = str(cell)
                    if cell_str.startswith("编制单位"):
                        result["编制单位"] = re.sub(r"^编制单位[：:]", "", cell_str).strip()
                    elif cell_str.startswith("日期"):
                        result["日期"] = re.sub(r"^日期[：:]", "", cell_str).strip()
                    elif cell_str.startswith("单位"):
                        result["单位"] = re.sub(r"^单位[：:]", "", cell_str).strip()
            continue

        if row_idx == 3:
            header = [str(cell).strip() if cell else "" for cell in row]
            if "本月数" in header or "本月" in "".join(header):
                has_monthly = True
            if "本年累计数" in header or "本年累计" in "".join(header):
                has_yearly = True
            if "年初数" in header or "年初" in "".join(header):
                has_yearly = True  # 复用变量名表示有第二列
            continue

        account_name = row[0] if row else None
        if account_name and str(account_name).strip():
            item = {
                "科目名称": str(account_name).strip()
            }

            if has_monthly and has_yearly:
                monthly_value = row[1] if len(row) > 1 else None
                item["本月数"] = "" if monthly_value is None else str(monthly_value).strip()

                yearly_value = row[2] if len(row) > 2 else None
                item["本年累计数"] = "" if yearly_value is None else str(yearly_value).strip()
            else:
                initial_value = row[1] if len(row) > 1 else None
                item["年初数"] = "" if initial_value is None else str(initial_value).strip()

                final_value = row[2] if len(row) > 2 else None
                item["期末数"] = "" if final_value is None else str(final_value).strip()

            result["表格数据"].append(item)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print(f"转换完成: {output_path}")
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python xlsx_to_json.py <xlsx文件路径> [json输出路径]")
        sys.exit(1)

    xlsx_file = sys.argv[1]
    json_file = sys.argv[2] if len(sys.argv) > 2 else None

    result = xlsx_to_json(xlsx_file, json_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
