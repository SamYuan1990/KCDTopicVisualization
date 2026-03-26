#!/usr/bin/env python3
"""
append_items.py
- 读取 filtered_result.json
- 根据 landscape.yml 中的 item 结构生成新 item
- 将新 item 追加到 result.yml 中对应 category 和 subcategory 的 items 列表末尾
- 添加 second_path 字段，包含 case/deep/audience/diffcult/deployment 的值（不带引号）
"""

import json
import sys
import copy
from ruamel.yaml import YAML

def load_yaml(file_path):
    """加载 YAML 文件，保留注释和格式"""
    yaml = YAML()
    yaml.preserve_quotes = True
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.load(f)
        return data
    except Exception as e:
        print(f"错误: 读取文件 {file_path} 失败: {e}")
        sys.exit(1)

def save_yaml(data, file_path):
    """保存 YAML 文件，保留格式"""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)
        print(f"结果已保存到 {file_path}")
    except Exception as e:
        print(f"错误: 写入文件 {file_path} 失败: {e}")
        sys.exit(1)

def find_subcategory_and_template(landscape_data, category_name, project_name):
    """
    在 landscape_data 中查找 project_name 所在的 subcategory 名称和 item 模板。
    返回 (subcategory_name, item_template)，如果未找到返回 (None, None)。
    """
    landscape_list = landscape_data.get('landscape', [])
    for cat_entry in landscape_list:
        # 提取 category 字典
        cat = None
        if isinstance(cat_entry, dict):
            if 'name' in cat_entry:
                cat = cat_entry
            elif 'category' in cat_entry and isinstance(cat_entry['category'], dict):
                cat = cat_entry['category']
        if not cat:
            continue
        if cat.get('name') != category_name:
            continue

        subcategories = cat.get('subcategories', [])
        for sub_entry in subcategories:
            subcat = None
            if isinstance(sub_entry, dict):
                if 'name' in sub_entry:
                    subcat = sub_entry
                elif 'subcategory' in sub_entry and isinstance(sub_entry['subcategory'], dict):
                    subcat = sub_entry['subcategory']
            if not subcat:
                continue
            items = subcat.get('items', [])
            for item_entry in items:
                item_name = None
                if isinstance(item_entry, dict):
                    if 'name' in item_entry:
                        item_name = item_entry.get('name')
                        item_template = item_entry
                    elif 'item' in item_entry and isinstance(item_entry['item'], dict):
                        item_name = item_entry['item'].get('name')
                        item_template = item_entry
                if item_name == project_name:
                    return (subcat.get('name'), copy.deepcopy(item_template))
    return (None, None)

def ensure_category_subcategory(result_data, category_name, subcategory_name):
    """
    确保 result_data 中存在指定的 category 和 subcategory。
    如果不存在，则创建。
    返回 (category_dict, subcategory_dict)。
    """
    # 确保 landscape 列表存在
    if 'landscape' not in result_data:
        result_data['landscape'] = []
    landscape_list = result_data['landscape']

    # 查找或创建 category
    cat = None
    for cat_entry in landscape_list:
        # 尝试两种可能的结构
        if isinstance(cat_entry, dict):
            if 'name' in cat_entry and cat_entry.get('name') == category_name:
                cat = cat_entry
                break
            elif 'category' in cat_entry and isinstance(cat_entry['category'], dict) and cat_entry['category'].get('name') == category_name:
                cat = cat_entry['category']
                break
    if cat is None:
        # 创建新的 category 结构（直接使用 {'name': ..., 'subcategories': []}）
        new_cat = {'name': category_name, 'subcategories': []}
        landscape_list.append(new_cat)
        cat = new_cat

    # 确保 cat 是字典且包含 subcategories
    if not isinstance(cat, dict):
        print(f"错误: category 不是字典，类型 {type(cat)}")
        return None, None
    if 'subcategories' not in cat:
        cat['subcategories'] = []

    # 查找或创建 subcategory
    subcat = None
    for sub_entry in cat['subcategories']:
        if isinstance(sub_entry, dict):
            if 'name' in sub_entry and sub_entry.get('name') == subcategory_name:
                subcat = sub_entry
                break
            elif 'subcategory' in sub_entry and isinstance(sub_entry['subcategory'], dict) and sub_entry['subcategory'].get('name') == subcategory_name:
                subcat = sub_entry['subcategory']
                break
    if subcat is None:
        new_subcat = {'name': subcategory_name, 'items': []}
        cat['subcategories'].append(new_subcat)
        subcat = new_subcat

    # 确保 subcat 包含 items
    if not isinstance(subcat, dict):
        print(f"错误: subcategory 不是字典，类型 {type(subcat)}")
        return cat, None
    if 'items' not in subcat:
        subcat['items'] = []

    return cat, subcat

def add_second_path_to_item(item, analysis):
    """
    向 item 添加 second_path 字段，包含 case/deep/audience/diffcult/deployment 的值。
    值不带引号。
    """
    # 定义要添加的字段映射
    fields = ['case', 'deep', 'audience', 'diffcult', 'deployment']
    
    # 收集有值的字段
    second_path_values = []
    for field in fields:
        value = analysis.get(field)
        if value is not None:
            # 处理布尔值
            if isinstance(value, bool):
                value_str = "true" if value else "false"
            else:
                value_str = str(value)
            # 不带引号，直接使用字符串
            second_path_values.append(f"{field} / {value_str}")
    
    # 如果有值，则添加 second_path
    if second_path_values:
        # 如果 item 是 {'item': {...}} 结构
        if 'item' in item and isinstance(item['item'], dict):
            item['item']['second_path'] = second_path_values
        # 如果 item 是直接包含 name 的结构
        elif isinstance(item, dict):
            item['second_path'] = second_path_values
        else:
            # 如果结构意外，创建 item 包装
            new_item = {'item': {'second_path': second_path_values}}
            new_item['item']['name'] = item.get('name', '')
            return new_item
    
    return item

def main():
    # 加载 filtered_result.json
    print(">>> 加载 filtered_result.json")
    try:
        with open('filtered_result.json', 'r', encoding='utf-8') as f:
            filtered_data = json.load(f)
    except Exception as e:
        print(f"错误: 读取 filtered_result.json 失败: {e}")
        sys.exit(1)
    print(f"共加载 {len(filtered_data)} 条记录。")

    # 加载 landscape.yml（仅用于获取 subcategory 名称和 item 模板）
    print("\n>>> 加载 landscape/landscape.yml")
    landscape_data = load_yaml('landscape/landscape.yml')
    print("加载成功。")

    # 加载 result.yml（如果文件不存在，创建空结构）
    print("\n>>> 加载 result.yml")
    try:
        result_data = load_yaml('result.yml')
    except FileNotFoundError:
        result_data = {'landscape': []}
        print("result.yml 不存在，创建新文件。")
    except Exception as e:
        print(f"错误: 加载 result.yml 失败: {e}")
        sys.exit(1)

    print("\n>>> 开始追加")
    for idx, entry in enumerate(filtered_data):
        print(f"\n--- 处理条目 #{idx+1} ---")
        category_name = entry.get('category')
        markdown_file = entry.get('markdown_file')
        analysis = entry.get('analysis', {})
        major_project_str = analysis.get('major_project', '')

        print(f"   category: {category_name}")
        print(f"   markdown_file: {markdown_file}")
        print(f"   major_project: {major_project_str}")
        print(f"   analysis: {analysis}")
        print(f"   analysis values: case={analysis.get('case')}, deep={analysis.get('deep')}, audience={analysis.get('audience')}, diffcult={analysis.get('diffcult')}, deployment={analysis.get('deployment')}")

        if not category_name or not markdown_file:
            print("   跳过: category 或 markdown_file 为空")
            continue

        project_names = [p.strip() for p in major_project_str.split(',') if p.strip()]
        if not project_names:
            print("   跳过: major_project 为空，无法确定 subcategory")
            continue

        matched = False
        for proj in project_names:
            subcategory_name, item_template = find_subcategory_and_template(landscape_data, category_name, proj)
            if subcategory_name and item_template:
                print(f"   在 category '{category_name}' 中找到项目 '{proj}' 位于 subcategory '{subcategory_name}'")
                # 确保 result 中有对应 category 和 subcategory
                cat, subcat = ensure_category_subcategory(result_data, category_name, subcategory_name)
                if cat is None or subcat is None:
                    print(f"   错误: 无法创建 category/subcategory 结构，跳过")
                    continue
                # 使用深拷贝的模板
                new_item = copy.deepcopy(item_template)
                # 修改 name 字段
                if 'item' in new_item and isinstance(new_item['item'], dict):
                    new_item['item']['name'] = markdown_file + ' - ' + proj
                    new_item['item']['description'] = analysis.get('description')
                    # 添加 second_path
                    new_item = add_second_path_to_item(new_item, analysis)
                elif 'name' in new_item:
                    new_item['name'] = markdown_file + ' - ' + proj
                    new_item['description'] = analysis.get('description')
                    # 添加 second_path
                    new_item = add_second_path_to_item(new_item, analysis)
                else:
                    # 如果模板结构意外，创建基本 item
                    new_item = {'name': markdown_file+ ' - ' + proj,'description':analysis.get('description')}
                    new_item = add_second_path_to_item(new_item, analysis)
                # 追加到 items 列表末尾（不是替换）
                subcat['items'].append(new_item)
                print(f"   已追加新 item (name='{markdown_file}') 到 category '{category_name}' / subcategory '{subcategory_name}' 的末尾")
                if analysis.get('case') or analysis.get('deep') or analysis.get('audience') or analysis.get('diffcult') or analysis.get('deployment'):
                    second_path_list = [f"{k} / {v}" for k, v in analysis.items() if k in ['case', 'deep', 'audience', 'diffcult', 'deployment'] and v is not None]
                    print(f"   已添加 second_path 字段: {second_path_list}")
                matched = True
                continue

        if not matched:
            print(f"   未找到项目 '{project_names}' 在 landscape.yml 中，跳过")

    # 保存 result.yml
    print("\n>>> 保存 result.yml")
    save_yaml(result_data, 'result.yml')

    print("\n处理完成。")

if __name__ == '__main__':
    main()