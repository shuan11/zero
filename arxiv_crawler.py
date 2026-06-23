#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArXiv 论文爬虫 - 搜索最新AI Agent相关论文
==========================================
使用 urllib 访问 arxiv.org API，解析XML结果，提取关键字段。
灵感来源：academic-research 项目的多智能体研究架构。

用法：python arxiv_crawler.py
输出：arxiv_papers.json（包含5篇最新论文）
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime


# ============ 配置 ============
# arxiv API 查询参数
SEARCH_QUERY = "all:AI+agent"  # 搜索关键词：AI agent
MAX_RESULTS = 5                # 每次获取5篇最新论文
SORT_BY = "submittedDate"      # 按提交日期排序
SORT_ORDER = "descending"      # 降序（最新在前）

# 输出文件路径（与脚本同目录）
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "arxiv_papers.json")

# arxiv API 命名空间
ATOM_NS = "http://www.w3.org/2005/Atom"


def build_api_url():
    """
    构建 arxiv API 请求URL
    API文档: https://info.arxiv.org/help/api/
    """
    base_url = "http://export.arxiv.org/api/query?"
    params = {
        "search_query": SEARCH_QUERY,
        "start": 0,
        "max_results": MAX_RESULTS,
        "sortBy": SORT_BY,
        "sortOrder": SORT_ORDER,
    }
    url = base_url + urllib.parse.urlencode(params)
    return url


def fetch_papers(url):
    """
    使用 urllib 请求 arxiv API 获取论文数据（XML格式）
    """
    print(f"[信息] 正在请求 arxiv API ...")
    print(f"[信息] URL: {url}")

    # 设置合理的 User-Agent，避免被拒绝（HTTP头只支持ASCII）
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ZhenYuanCluster-ArXivCrawler/1.0 (academic research)",
            "Accept": "application/atom+xml",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            # 读取XML响应
            xml_data = response.read().decode("utf-8")
            print(f"[信息] 成功获取响应，大小: {len(xml_data)} 字节")
            return xml_data
    except urllib.error.HTTPError as e:
        print(f"[错误] HTTP错误: {e.code} - {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"[错误] URL错误: {e.reason}")
        return None
    except Exception as e:
        print(f"[错误] 未知错误: {e}")
        return None


def parse_xml(xml_data):
    """
    解析 arxiv API 返回的 XML 数据
    提取每篇论文的: title, summary, authors, published, link, categories
    """
    print("[信息] 正在解析XML数据 ...")

    # 注册命名空间前缀，避免解析问题
    ET.register_namespace("", ATOM_NS)

    root = ET.fromstring(xml_data)
    papers = []

    # 查找所有 <entry> 元素（每篇论文一个entry）
    entries = root.findall(f"{{{ATOM_NS}}}entry")
    print(f"[信息] 找到 {len(entries)} 篇论文")

    for entry in entries:
        paper = {}

        # 提取标题（去掉多余空白和换行）
        title_elem = entry.find(f"{{{ATOM_NS}}}title")
        paper["title"] = (
            " ".join(title_elem.text.strip().split()) if title_elem is not None else "未知标题"
        )

        # 提取摘要
        summary_elem = entry.find(f"{{{ATOM_NS}}}summary")
        paper["summary"] = (
            " ".join(summary_elem.text.strip().split())
            if summary_elem is not None
            else "无摘要"
        )

        # 提取所有作者
        author_elems = entry.findall(f"{{{ATOM_NS}}}author")
        paper["authors"] = []
        for author in author_elems:
            name_elem = author.find(f"{{{ATOM_NS}}}name")
            if name_elem is not None:
                paper["authors"].append(name_elem.text.strip())

        # 提取发布时间
        published_elem = entry.find(f"{{{ATOM_NS}}}published")
        paper["published"] = (
            published_elem.text.strip() if published_elem is not None else "未知"
        )

        # 提取更新时间
        updated_elem = entry.find(f"{{{ATOM_NS}}}updated")
        paper["updated"] = (
            updated_elem.text.strip() if updated_elem is not None else "未知"
        )

        # 提取论文链接（arxiv页面）
        link_elem = entry.find(f"{{{ATOM_NS}}}link[@type='text/html']")
        if link_elem is None:
            link_elem = entry.find(f"{{{ATOM_NS}}}link")
        paper["url"] = (
            link_elem.get("href", "") if link_elem is not None else ""
        )

        # 提取分类标签
        category_elems = entry.findall("{http://arxiv.org/schemas/atom}primary_category")
        if not category_elems:
            category_elems = entry.findall(f"{{{ATOM_NS}}}category")
        paper["categories"] = []
        for cat in category_elems:
            term = cat.get("term", "")
            if term:
                paper["categories"].append(term)

        # 提取arxiv ID（从 id 字段提取）
        id_elem = entry.find(f"{{{ATOM_NS}}}id")
        if id_elem is not None:
            paper["arxiv_id"] = id_elem.text.strip().split("/abs/")[-1]
        else:
            paper["arxiv_id"] = ""

        papers.append(paper)

    return papers


def save_to_json(papers, filepath):
    """
    将论文数据保存为JSON文件
    包含抓取时间戳等元数据
    """
    output = {
        "metadata": {
            "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "search_query": SEARCH_QUERY,
            "total_papers": len(papers),
            "sort_by": SORT_BY,
            "sort_order": SORT_ORDER,
            "source": "arxiv.org API",
            "description": "由真元集群 ArXiv 爬虫自动抓取的最新 AI Agent 论文",
        },
        "papers": papers,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[信息] 已保存到: {filepath}")


def print_summary(papers):
    """
    打印论文摘要信息到终端
    """
    print("\n" + "=" * 60)
    print(f"  抓取完成 - 共 {len(papers)} 篇 AI Agent 论文")
    print("=" * 60)

    for i, paper in enumerate(papers, 1):
        print(f"\n--- 论文 {i} ---")
        print(f"  标题: {paper['title']}")
        print(f"  作者: {', '.join(paper['authors'][:3])}")
        if len(paper["authors"]) > 3:
            print(f"         ... 等 {len(paper['authors'])} 位作者")
        print(f"  发布: {paper['published'][:10]}")
        print(f"  分类: {', '.join(paper['categories'][:2])}")
        print(f"  链接: {paper['url']}")
        # 摘要截断显示
        summary_short = paper["summary"][:120] + "..." if len(paper["summary"]) > 120 else paper["summary"]
        print(f"  摘要: {summary_short}")


def main():
    """
    主函数：构建URL -> 请求API -> 解析XML -> 保存JSON
    """
    print("=" * 60)
    print("  真元集群 ArXiv 论文爬虫 v1.0")
    print("  搜索关键词: AI Agent")
    print(f"  获取数量: {MAX_RESULTS} 篇")
    print("=" * 60)

    # 第一步：构建API请求URL
    url = build_api_url()

    # 第二步：获取XML数据
    xml_data = fetch_papers(url)
    if xml_data is None:
        print("[错误] 获取数据失败，退出")
        return 1

    # 第三步：解析XML，提取论文信息
    papers = parse_xml(xml_data)
    if not papers:
        print("[警告] 未解析到任何论文")
        return 1

    # 第四步：保存到JSON文件
    save_to_json(papers, OUTPUT_FILE)

    # 第五步：打印摘要
    print_summary(papers)

    print(f"\n[完成] 数据已写入: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    exit(main())
