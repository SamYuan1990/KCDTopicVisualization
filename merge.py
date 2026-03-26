#!/usr/bin/env python3
"""
merge_landscape.py
合并 template.yml 和 guide.yml，输出 prepare.yml
"""

import sys
from ruamel.yaml import YAML

def load_yaml(filepath):
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.load(f)

def dump_yaml(data, filepath):
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)

def merge_landscape(landscape_data, guide_data):
    """将 guide 数据合并到 landscape 数据中"""
    # 构建 guide 索引：category_name -> {content, subcategories_map}
    guide_index = {}
    for cat in guide_data.get('categories', []):
        cat_name = cat.get('category')
        if not cat_name:
            continue
        # 构建子类别索引：subcategory_name -> {projects, keywords, content}
        sub_index = {}
        for sub in cat.get('subcategories', []):
            sub_name = sub.get('subcategory')
            if sub_name:
                sub_index[sub_name] = {
                    'projects': sub.get('projects', []),
                    'keywords': sub.get('keywords', []),
                    'content': sub.get('content', '')
                }
        guide_index[cat_name] = {
            'content': cat.get('content', ''),
            'subcategories': sub_index
        }

    # 遍历 landscape 并合并
    for category_entry in landscape_data.get('landscape', []):
        cat_name = category_entry.get('name')
        if not cat_name:
            continue

        guide_cat = guide_index.get(cat_name)
        if guide_cat:
            # 合并 category 的 content
            if 'content' not in category_entry and guide_cat['content']:
                category_entry['content'] = guide_cat['content']

            # 合并 subcategories
            subcategories = category_entry.get('subcategories', [])
            for sub_entry in subcategories:
                sub_name = sub_entry.get('name')
                if not sub_name:
                    continue
                guide_sub = guide_cat['subcategories'].get(sub_name)
                if guide_sub:
                    # 合并 subcategory 字段
                    if 'projects' not in sub_entry and guide_sub['projects']:
                        sub_entry['projects'] = guide_sub['projects']
                    if 'keywords' not in sub_entry and guide_sub['keywords']:
                        sub_entry['keywords'] = guide_sub['keywords']
                    if 'content' not in sub_entry and guide_sub['content']:
                        sub_entry['content'] = guide_sub['content']
                # 注意：原有 items 字段保持不变（空列表）
        # 如果 guide 中没有对应 category，则跳过

    return landscape_data

def main():
    # 固定输入输出文件
    result_file = 'template.yml'
    guide_file = 'guide.yml'
    output_file = 'prepare.yml'

    try:
        landscape_data = load_yaml(result_file)
        guide_data = load_yaml(guide_file)
    except Exception as e:
        print(f"读取文件失败: {e}")
        sys.exit(1)

    merged = merge_landscape(landscape_data, guide_data)

    try:
        dump_yaml(merged, output_file)
        print(f"✅ 合并完成，结果保存至 {output_file}")
    except Exception as e:
        print(f"写入文件失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()