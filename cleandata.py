#!/usr/bin/env python3
"""
strip_items.py
读取 data.yml，清空每个 subcategory 的 items，输出到 result.yml，
并打印处理日志（含调试信息）。
"""

import sys
from ruamel.yaml import YAML

def clean_subcategory(subcat_dict):
    """清空单个 subcategory 的内容，仅保留 name 和空 items"""
    keys_to_keep = {'name', 'items'}
    for key in list(subcat_dict.keys()):
        if key not in keys_to_keep:
            del subcat_dict[key]
    subcat_dict['items'] = []
    return subcat_dict

def clean_landscape(data):
    """遍历 landscape 结构，清空所有 subcategory 的 items，并打印日志"""
    if 'landscape' not in data:
        print("警告: 文件中没有 'landscape' 字段")
        return data

    print(f"[DEBUG] landscape 是一个列表，长度为 {len(data['landscape'])}")
    for idx, category_entry in enumerate(data['landscape']):
        print(f"\n[DEBUG] 处理第 {idx} 个 landscape 元素")
        print(f"[DEBUG] 该元素的键: {list(category_entry.keys())}")

        # 尝试两种可能的 category 结构
        if 'category' in category_entry and isinstance(category_entry['category'], dict):
            # 如果有 'category' 键且其值为字典，则使用该字典
            category = category_entry['category']
            print("[DEBUG] 使用嵌套 category 结构")
        else:
            # 否则直接将当前元素视为 category
            category = category_entry
            print("[DEBUG] 使用直接 category 结构")

        # 获取 category 名称
        category_name = category.get('name', '未命名')
        print(f"[DEBUG] category 名称: {category_name}")

        # 获取 subcategories
        subcategories = category.get('subcategories', [])
        print(f"[DEBUG] subcategories 列表长度: {len(subcategories)}")

        for sub_idx, subcat_entry in enumerate(subcategories):
            print(f"\n[DEBUG] 第 {sub_idx} 个 subcategory 条目")
            print(f"[DEBUG] 该条目的键: {list(subcat_entry.keys())}")

            # 处理 subcategory 可能嵌套在 'subcategory' 键下
            if 'subcategory' in subcat_entry and isinstance(subcat_entry['subcategory'], dict):
                subcat = subcat_entry['subcategory']
                print("[DEBUG] 使用嵌套 subcategory 结构")
            else:
                subcat = subcat_entry
                print("[DEBUG] 使用直接 subcategory 结构")

            subcat_name = subcat.get('name', '未命名')
            print(f"处理: category='{category_name}', subcategory='{subcat_name}'")

            clean_subcategory(subcat)

    return data

def main():
    input_file = 'data.yml'
    output_file = 'template.yml'

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = yaml.load(f)
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 {input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"读取文件时出错: {e}")
        sys.exit(1)

    # 调试：打印读取的数据类型
    print(f"[DEBUG] 读取的数据类型: {type(data)}")
    if data is None:
        print("[DEBUG] 数据为空，请检查文件内容")
        sys.exit(1)

    # 处理数据
    cleaned = clean_landscape(data)

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(cleaned, f)
        print(f"\n✅ 已处理完成，结果保存至 {output_file}")
    except Exception as e:
        print(f"写入文件时出错: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()