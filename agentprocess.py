#!/usr/bin/env python3
"""
analyze_presentations.py
使用 DeepSeek V3.2 对演讲与 CNCF 分类进行相关性分析
"""

import os
import json
import glob
import argparse
import time
import re
from typing import Dict, List, Any
import openai
from ruamel.yaml import YAML

# ========== 配置 ==========
# DeepSeek V3.2 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "your-deepseek-api-key-here")
OPENAI_API_KEY = DEEPSEEK_API_KEY
OPENAI_MODEL = "deepseek-chat"                     # DeepSeek-V3.2 模型
OPENAI_BASE_URL = "https://api.deepseek.com/v1"    # DeepSeek API 端点

# 缓存文件路径（避免重复调用 API）
CACHE_FILE = "analysis_cache.json"

# 提示词模板
PROMPT_TEMPLATE = """你是一位资深云原生技术专家。我将为你提供一个演讲的PPT内容，以及CNCF云原生全景图中的某个特定分类（${category}）的介绍。请你基于这些信息，完成以下任务：

相关性判断：判断该演讲主题是否属于 ${category}。判断依据是该演讲主要涉及的项目或技术，是否在 ${category} 的项目列表中。

深度分析：如果相关，请对该演讲进行多维度分析；如果不相关，则除 is_related 外的字段输出 null。

请严格按照以下JSON格式进行输出，确保结构统一。

{
  "is_related": "布尔值，true表示演讲与分类相关，false表示不相关",
  "major_project": "字符串，如果相关，列出该演讲涉及的主要CNCF项目名称（一个或多个，用逗号分隔）；如果不相关，则为null",
  "description": "字符串，如果相关，由三部分信息拼接而成：1）目标听众；2）与分类的相关性简述（50字以内）；3）多个项目之间的关系简述（如果涉及两个及以上项目，30字左右）。格式示例：'面向开发者和架构师。该演讲主要介绍了Prometheus在FinOps场景下的应用，属于可观测性分类。演讲中，Prometheus作为数据源，与OpenCost和Kubecost共同构建了成本监控体系。'；如果不相关，则为null",
  "case": "布尔值，如果相关，true表示演讲中包含具体的企业级或实战案例，false表示不包含；对应筛选器中的'Have'或'Not'；如果不相关，则为null",
  "deep": "整数，如果相关，取值范围1-5，代表演讲的技术深度。取值含义：1=入门，2=基础，3=中级，4=高级，5=深度；如果不相关，则为null",
  "audience": "字符串，如果相关，取值范围限定为：'运维工程师'、'开发工程师'、'架构师'、'技术管理者'、'混合'。如适合多种角色，请选择最匹配的一项或使用'混合'；如果不相关，则为null",
  "diffcult": "整数，如果相关，取值范围1-5，代表演讲所涉及技术或场景的复杂度。取值含义：1=简单，2=较低，3=中等，4=较高，5=复杂；如果不相关，则为null",
  "deployment": "整数，如果相关，取值范围1-5，代表演讲中技术内容的可实践性。取值含义：1=理论性强，2=较难落地，3=一般，4=易实践，5=即学即用；如果不相关，则为null"
}

以下是演讲内容的PPT：

${ppt_markdown_content}

以下是 ${category} 的分类介绍：

${category_introduce}
"""

def load_yaml(filepath: str) -> Dict:
    """加载 YAML 文件，保留注释和格式"""
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.load(f)

def extract_categories(yaml_data: Dict) -> List[Dict]:
    """从 prepare.yaml 的 landscape 结构中提取每个 category 的信息，
    包括 category name、projects（来自其 subcategories 中带有 projects 字段的）、
    以及 category 本身的 content（如果有）。"""
    categories = []
    if 'landscape' not in yaml_data:
        return categories

    for category_entry in yaml_data['landscape']:
        # 兼容两种结构：直接是 category 对象，或嵌套在 'category' 键下
        if 'category' in category_entry and isinstance(category_entry['category'], dict):
            category = category_entry['category']
        else:
            category = category_entry

        cat_name = category.get('name')
        if not cat_name:
            continue

        # 收集该 category 下所有 subcategory 的 projects（去重）
        all_projects = []
        subcategories = category.get('subcategories', [])
        for sub_entry in subcategories:
            if 'subcategory' in sub_entry and isinstance(sub_entry['subcategory'], dict):
                subcat = sub_entry['subcategory']
            else:
                subcat = sub_entry

            projects = subcat.get('projects', [])
            if projects:
                all_projects.extend(projects)

        # 获取 category 的 content（如果有）
        cat_content = category.get('content', '')

        categories.append({
            'name': cat_name,
            'projects': all_projects,
            'content': cat_content
        })

    return categories

def get_markdown_files(dir_path: str) -> List[str]:
    """获取目录下所有 .md 文件的路径列表"""
    pattern = os.path.join(dir_path, '*.md')
    return glob.glob(pattern)

def read_markdown(filepath: str) -> str:
    """读取 Markdown 文件内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def call_llm(prompt: str) -> Dict:
    """调用 DeepSeek API，返回解析后的 JSON"""
    client = openai.OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
    )
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"}  # 强制返回 JSON
        # 注意：DeepSeek 默认不开启深度思考，无需额外参数
    )
    content = response.choices[0].message.content
    # 尝试解析 JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 如果返回的不是合法 JSON，尝试提取
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            raise ValueError(f"LLM 返回的不是有效 JSON: {content[:200]}")

def load_cache() -> Dict:
    """加载缓存文件"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache: Dict):
    """保存缓存到文件"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(
        description="分析演讲与 CNCF 分类的相关性 (DeepSeek V3.2)"
    )
    parser.add_argument('--yaml', default='prepare.yml',
                        help='YAML 文件路径（默认 prepare.yml）')
    parser.add_argument('--markdown', default='markdown',
                        help='Markdown 目录路径（默认 markdown/）')
    parser.add_argument('--output', default='analysis_results.json',
                        help='输出 JSON 文件路径（默认 analysis_results.json）')
    parser.add_argument('--no-cache', action='store_true',
                        help='不使用缓存，强制重新调用 API')
    args = parser.parse_args()

    # 加载 YAML
    try:
        yaml_data = load_yaml(args.yaml)
    except Exception as e:
        print(f"读取 YAML 文件失败: {e}")
        return

    categories = extract_categories(yaml_data)
    if not categories:
        print("未找到任何 category 信息")
        return

    # 获取所有 Markdown 文件
    markdown_files = get_markdown_files(args.markdown)
    if not markdown_files:
        print(f"在 {args.markdown} 下未找到 .md 文件")
        return

    # 加载缓存
    cache = load_cache() if not args.no_cache else {}

    results = []

    for md_file in markdown_files:
        filename = os.path.basename(md_file)
        print(f"处理文件: {filename}")
        ppt_content = read_markdown(md_file)

        for cat in categories:
            cat_name = cat['name']
            key = f"{filename}||{cat_name}"
            if key in cache and not args.no_cache:
                print(f"  使用缓存: {cat_name}")
                results.append({
                    "markdown_file": filename,
                    "category": cat_name,
                    "analysis": cache[key]
                })
                continue

            # 构建 category 介绍文本
            projects_str = "\n".join([f"- {p}" for p in cat['projects']])
            category_introduce = f"分类名称：{cat_name}\n\n项目列表：\n{projects_str}\n\n分类介绍：\n{cat['content']}"

            # 构建 prompt
            prompt = PROMPT_TEMPLATE.replace("${category}", cat_name) \
                                     .replace("${ppt_markdown_content}", ppt_content) \
                                     .replace("${category_introduce}", category_introduce)

            # 调用 LLM
            try:
                analysis = call_llm(prompt)
                # 确保 is_related 字段存在
                analysis.setdefault("is_related", False)
                # 缓存结果
                cache[key] = analysis
                save_cache(cache)
                results.append({
                    "markdown_file": filename,
                    "category": cat_name,
                    "analysis": analysis
                })
                print(f"  分析完成: {cat_name}")
                time.sleep(0.5)  # 避免 API 限流
            except Exception as e:
                print(f"  分析 {cat_name} 失败: {e}")
                # 可保留占位
                results.append({
                    "markdown_file": filename,
                    "category": cat_name,
                    "analysis": {"is_related": False, "error": str(e)}
                })

    # 保存最终结果
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"结果已保存至 {args.output}")

if __name__ == '__main__':
    main()