#!/usr/bin/env python3
"""
微信公众号文章转 Markdown 工具
用法: python fetch_article.py <微信文章URL> [输出文件名]
"""

import sys
import re
import json
import urllib.request
import urllib.error
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path


class WeChatArticleParser(HTMLParser):
    """解析微信文章HTML，提取结构化内容"""

    def __init__(self):
        super().__init__()
        self.in_content = False
        self.in_title = False
        self.in_author = False
        self.content_parts = []
        self.title = ""
        self.author = ""
        self.current_tag = None
        self.current_attrs = {}
        self.list_depth = 0
        self.is_ordered_list = False
        self.list_counter = 0
        self.in_blockquote = False
        self.in_strong = False
        self.in_em = False
        self.ignore_tags = {'script', 'style', 'nav', 'header', 'footer'}
        self.in_ignore = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.current_tag = tag
        self.current_attrs = attrs_dict

        # 检测内容区域
        if tag == 'div':
            class_name = attrs_dict.get('class', '')
            id_name = attrs_dict.get('id', '')
            if 'rich_media_content' in class_name or 'js_content' in id_name:
                self.in_content = True

        # 检测标题
        if tag == 'h1' and 'rich_media_title' in attrs_dict.get('class', ''):
            self.in_title = True

        # 检测作者
        if tag == 'a' and 'rich_media_meta_link' in attrs_dict.get('class', ''):
            self.in_author = True

        # 忽略特定标签
        if tag in self.ignore_tags:
            self.in_ignore = True
            return

        if self.in_ignore or not self.in_content:
            return

        # 处理各种标签
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            self.content_parts.append('\n\n' + '#' * level + ' ')

        elif tag == 'p':
            if self.in_blockquote:
                self.content_parts.append('\n> ')
            else:
                self.content_parts.append('\n\n')

        elif tag == 'br':
            self.content_parts.append('  \n')

        elif tag == 'img':
            src = attrs_dict.get('data-src', '') or attrs_dict.get('src', '')
            alt = attrs_dict.get('alt', '图片')
            if src:
                self.content_parts.append(f'\n\n![{alt}]({src})\n\n')

        elif tag == 'a':
            href = attrs_dict.get('href', '')
            if href and not href.startswith('javascript'):
                self.content_parts.append('[')

        elif tag in ('strong', 'b'):
            self.in_strong = True
            self.content_parts.append('**')

        elif tag in ('em', 'i'):
            self.in_em = True
            self.content_parts.append('*')

        elif tag == 'blockquote':
            self.in_blockquote = True
            self.content_parts.append('\n\n> ')

        elif tag == 'ul':
            self.is_ordered_list = False
            self.list_depth += 1
            self.content_parts.append('\n')

        elif tag == 'ol':
            self.is_ordered_list = True
            self.list_depth += 1
            self.list_counter = 0
            self.content_parts.append('\n')

        elif tag == 'li':
            indent = '  ' * (self.list_depth - 1)
            if self.is_ordered_list:
                self.list_counter += 1
                self.content_parts.append(f'\n{indent}{self.list_counter}. ')
            else:
                self.content_parts.append(f'\n{indent}- ')

        elif tag == 'code':
            self.content_parts.append('`')

        elif tag == 'pre':
            self.content_parts.append('\n\n```\n')

        elif tag == 'hr':
            self.content_parts.append('\n\n---\n\n')

        elif tag == 'table':
            self.content_parts.append('\n\n')

        elif tag == 'tr':
            self.content_parts.append('|')

        elif tag in ('td', 'th'):
            self.content_parts.append(' ')

    def handle_endtag(self, tag):
        if tag in self.ignore_tags:
            self.in_ignore = False
            return

        if tag == 'div' and self.in_content:
            # 可能需要更精确的判断来关闭内容区域

        if self.in_ignore or not self.in_content:
            if tag == 'h1':
                self.in_title = False
            if tag == 'a':
                self.in_author = False
            return

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.content_parts.append('\n')

        elif tag == 'p':
            pass  # 已在开始标签处理

        elif tag == 'a':
            href = self.current_attrs.get('href', '')
            if href and not href.startswith('javascript'):
                self.content_parts.append(f']({href})')

        elif tag in ('strong', 'b'):
            self.in_strong = False
            self.content_parts.append('**')

        elif tag in ('em', 'i'):
            self.in_em = False
            self.content_parts.append('*')

        elif tag == 'blockquote':
            self.in_blockquote = False
            self.content_parts.append('\n')

        elif tag in ('ul', 'ol'):
            self.list_depth -= 1
            self.content_parts.append('\n')

        elif tag == 'li':
            pass

        elif tag == 'code':
            self.content_parts.append('`')

        elif tag == 'pre':
            self.content_parts.append('\n```\n')

        elif tag in ('td', 'th'):
            self.content_parts.append(' |')

        elif tag == 'tr':
            self.content_parts.append('\n')

    def handle_data(self, data):
        if self.in_ignore:
            return

        if self.in_title:
            self.title = data.strip()
            return

        if self.in_author:
            self.author = data.strip()
            return

        if self.in_content:
            # 清理多余空白
            text = data.replace('\xa0', ' ').replace('\u200b', '')
            self.content_parts.append(text)


def clean_markdown(text):
    """清理和优化Markdown格式"""
    # 移除多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 清理行首行尾空白
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_lines.append(line.rstrip())
    text = '\n'.join(cleaned_lines)
    # 修复引用块格式
    text = re.sub(r'^>(\s*)\n', r'>\n', text, flags=re.MULTILINE)
    return text.strip()


def fetch_wechat_article(url):
    """获取微信文章内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')
            return html
    except urllib.error.URLError as e:
        print(f"网络错误: {e}")
        return None
    except Exception as e:
        print(f"获取文章失败: {e}")
        return None


def parse_article(html):
    """解析HTML并提取文章内容"""
    # 提取标题
    title_match = re.search(r'<h1[^>]*class="[^"]*rich_media_title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL)
    title = ""
    if title_match:
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

    # 提取作者
    author_match = re.search(r'<meta[^>]*name="author"[^>]*content="([^"]*)"', html)
    author = author_match.group(1) if author_match else "未知作者"

    # 提取内容区域
    content_match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*(?:<div[^>]*class="[^"]*rich_media_tool')', html, re.DOTALL)

    if not content_match:
        # 备用匹配
        content_match = re.search(r'<div[^>]*class="[^"]*rich_media_content[^"]*"[^>]*>(.*?)</div>\s*(?:<script|<div[^>]*class="[^"]*rich_media_meta)', html, re.DOTALL)

    if not content_match:
        print("警告: 无法找到文章内容区域，尝试解析全文")
        content_html = html
    else:
        content_html = content_match.group(1)

    # 转换HTML到Markdown
    markdown = html_to_markdown(content_html)

    return title, author, markdown


def html_to_markdown(html):
    """将HTML转换为Markdown"""
    # 预处理
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # 处理图片
    html = re.sub(r'<img[^>]*data-src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>', r'\n\n![\2](\1)\n\n', html)
    html = re.sub(r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>', r'\n\n![\2](\1)\n\n', html)

    # 处理标题
    for i in range(6, 0, -1):
        html = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', rf'\n\n{"#" * i} \1\n', html, flags=re.DOTALL)

    # 处理段落
    html = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\n\1\n', html, flags=re.DOTALL)

    # 处理换行
    html = re.sub(r'<br\s*/?>', r'  \n', html)

    # 处理粗体
    html = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', html, flags=re.DOTALL)

    # 处理斜体
    html = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'*\2*', html, flags=re.DOTALL)

    # 处理链接
    html = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', html, flags=re.DOTALL)

    # 处理引用块
    html = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'\n\n> \1\n', html, flags=re.DOTALL)

    # 处理无序列表
    html = re.sub(r'<ul[^>]*>(.*?)</ul>', r'\n\1\n', html, flags=re.DOTALL)
    html = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', html, flags=re.DOTALL)

    # 处理有序列表
    def replace_ol(match):
        items = re.findall(r'<li[^>]*>(.*?)</li>', match.group(1), re.DOTALL)
        result = '\n'
        for i, item in enumerate(items, 1):
            result += f'{i}. {item.strip()}\n'
        return result

    html = re.sub(r'<ol[^>]*>(.*?)</ol>', replace_ol, html, flags=re.DOTALL)

    # 处理代码块
    html = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n\n```\n\1\n```\n', html, flags=re.DOTALL)
    html = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', html, flags=re.DOTALL)

    # 处理分隔线
    html = re.sub(r'<hr\s*/?>', r'\n\n---\n\n', html)

    # 移除剩余HTML标签
    html = re.sub(r'<[^>]+>', '', html)

    # 清理HTML实体
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&quot;', '"')
    html = html.replace('&#39;', "'")
    html = html.replace('&apos;', "'")
    html = html.replace('\xa0', ' ')
    html = html.replace('\u200b', '')

    # 清理多余空白
    html = clean_markdown(html)

    return html


def generate_markdown_file(url, title, author, content, output_file=None):
    """生成Markdown文件"""
    today = datetime.now().strftime('%Y-%m-%d')

    md_content = f"""# {title}

> **作者**: {author}
> **原文链接**: {url}
> **保存日期**: {today}

---

{content}
"""

    return md_content


def main():
    if len(sys.argv) < 2:
        print("用法: python fetch_article.py <微信文章URL> [输出文件名]")
        print("示例: python fetch_article.py https://mp.weixin.qq.com/s/xxxxx article.md")
        sys.exit(1)

    url = sys.argv[1]

    # 验证URL
    if 'mp.weixin.qq.com' not in url:
        print("警告: 这可能不是微信公众号文章链接")

    # 确定输出文件名
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
        if not output_file.endswith('.md'):
            output_file += '.md'
    else:
        # 使用时间戳作为默认文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'article_{timestamp}.md'

    print(f"正在获取文章: {url}")

    # 获取文章
    html = fetch_wechat_article(url)
    if not html:
        sys.exit(1)

    print("正在解析文章内容...")

    # 解析文章
    title, author, content = parse_article(html)

    if not title:
        title = "未命名文章"

    print(f"标题: {title}")
    print(f"作者: {author}")

    # 生成Markdown
    md_content = generate_markdown_file(url, title, author, content)

    # 保存文件
    output_path = Path(output_file)
    output_path.write_text(md_content, encoding='utf-8')

    print(f"\n文章已保存到: {output_path.absolute()}")
    print(f"文件大小: {len(md_content)} 字符")


if __name__ == '__main__':
    main()
