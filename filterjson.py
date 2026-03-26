import json

def filter_analysis_results(input_file, output_file):
    # 定义要排除的 category 值
    excluded_categories = {"case", "deep", "audience", "diffcult", "deployment"}

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误：文件 {input_file} 不存在。")
        return
    except json.JSONDecodeError:
        print(f"错误：文件 {input_file} 不是有效的 JSON 格式。")
        return

    # 确保输入数据是一个列表
    if not isinstance(data, list):
        print("错误：输入文件应包含一个 JSON 数组。")
        return

    filtered_data = []
    for entry in data:
        # 检查是否有 analysis 字段且 is_related 为 True
        if entry.get("analysis", {}).get("is_related") is True:
            category = entry.get("category")
            # 如果 category 不在排除列表中，保留该条目
            if category not in excluded_categories:
                filtered_data.append(entry)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=2, ensure_ascii=False)

    print(f"过滤完成。共保留 {len(filtered_data)} 条记录。")

if __name__ == "__main__":
    filter_analysis_results("analysis_results.json", "filtered_result.json")