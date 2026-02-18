#!/usr/bin/env python3
"""
网页文章保存工具 - 图形界面版
支持：
1. 微信公众号文章
2. 通用网页文章（Notion博客等）
3. 保存为Markdown（纯文本）
4. 保存为HTML（保留原始样式）
5. 保存为EPUB（电子书格式）
6. 图片本地下载
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import re
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
import webbrowser
import os
import time
import hashlib
import zipfile
import io
import uuid
import subprocess
import shutil
import tempfile
from PIL import Image


class ImageDownloader:
    """图片下载器"""

    def __init__(self, log_callback=None, referer=None):
        self.log_callback = log_callback
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': referer or 'https://www.google.com/',
        }

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def get_image_extension(self, url, content_type=None):
        """获取图片扩展名"""
        if content_type:
            type_map = {
                'image/jpeg': '.jpg',
                'image/jpg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'image/bmp': '.bmp',
                'image/svg+xml': '.svg',
                'image/avif': '.avif',
            }
            if content_type in type_map:
                return type_map[content_type]

        ext_match = re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|svg|avif)(\?|$)', url, re.I)
        if ext_match:
            return '.' + ext_match.group(1).lower()

        return '.jpg'

    def download_image(self, url, save_path):
        """下载单张图片"""
        try:
            # 根据URL类型调整headers
            headers = self.headers.copy()
            if 'notion.com' in url or '/_next/image' in url:
                headers['Accept'] = 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
                headers['sec-fetch-dest'] = 'image'
                headers['sec-fetch-mode'] = 'no-cors'
                headers['sec-fetch-site'] = 'same-origin'

            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                content_type = response.headers.get('Content-Type', '')
                data = response.read()

                # 获取扩展名
                ext = self.get_image_extension(url, content_type)

                if save_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.avif']:
                    save_path = save_path.with_suffix(ext)

                save_path.write_bytes(data)
                return True, save_path
        except Exception as e:
            self.log(f"下载图片失败: {str(e)[:50]}")
            return False, None

    def download_images(self, image_urls, images_dir, progress_callback=None):
        """批量下载图片"""
        if not image_urls:
            return {}

        images_dir = Path(images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)

        url_mapping = {}
        total = len(image_urls)

        for i, url in enumerate(image_urls, 1):
            if progress_callback:
                progress_callback(i, total, url)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{timestamp}_{i}"
            save_path = images_dir / filename

            success, final_path = self.download_image(url, save_path)
            if success:
                # Use forward slash for cross-platform compatibility
                relative_path = Path('images') / final_path.name
                url_mapping[url] = relative_path.as_posix()  # Always use forward slashes
                self.log(f"下载图片 {i}/{total}: {final_path.name}")
            else:
                url_mapping[url] = url

            time.sleep(0.1)

        return url_mapping


class EpubConverter:
    """EPUB电子书转换器 - 支持Pandoc和手动生成两种方式"""

    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self._pandoc_path = None

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        print(message)

    def _find_pandoc(self):
        """查找Pandoc可执行文件路径"""
        if self._pandoc_path:
            return self._pandoc_path

        # 首先尝试系统PATH
        pandoc = shutil.which('pandoc')
        if pandoc:
            self._pandoc_path = pandoc
            return pandoc

        # 尝试Windows常见安装位置
        common_paths = [
            r'C:\Program Files\Pandoc\pandoc.exe',
            r'C:\Program Files (x86)\Pandoc\pandoc.exe',
            os.path.expanduser(r'~\AppData\Local\Pandoc\pandoc.exe'),
        ]

        for path in common_paths:
            if os.path.exists(path):
                self._pandoc_path = path
                return path

        return None

    def has_pandoc(self):
        """检查Pandoc是否可用"""
        return self._find_pandoc() is not None

    def _markdown_to_html(self, md_content, title):
        """将Markdown内容转换为HTML"""
        # 处理标题
        html = md_content
        for i in range(6, 0, -1):
            html = re.sub(rf'^{"#" * i}\s+(.+)$', rf'<h{i}>\1</h{i}>', html, flags=re.MULTILINE)

        # 处理图片 - 保存原始路径，稍后处理
        html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1"/>', html)

        # 处理链接
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

        # 处理粗体
        html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)

        # 处理斜体
        html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)

        # 处理引用块
        html = re.sub(r'^>\s*(.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

        # 处理代码块
        html = re.sub(r'```(\w*)\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # 处理水平线
        html = re.sub(r'^---$', r'<hr/>', html, flags=re.MULTILINE)

        # 处理列表
        html = re.sub(r'^-\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html)

        # 处理段落（将连续的非标签行包装为p标签）
        lines = html.split('\n')
        result_lines = []
        in_paragraph = False
        paragraph_content = []

        for line in lines:
            stripped = line.strip()
            # 检查是否是HTML标签行或空行
            is_html_tag = stripped.startswith('<') and (stripped.endswith('>') or stripped.startswith('</'))
            is_empty = not stripped

            if is_html_tag or is_empty:
                # 如果正在段落中，结束段落
                if in_paragraph and paragraph_content:
                    result_lines.append('<p>' + ' '.join(paragraph_content) + '</p>')
                    paragraph_content = []
                    in_paragraph = False
                result_lines.append(line)
            else:
                # 普通文本，添加到段落
                in_paragraph = True
                paragraph_content.append(stripped)

        # 处理最后的段落
        if paragraph_content:
            result_lines.append('<p>' + ' '.join(paragraph_content) + '</p>')

        html = '\n'.join(result_lines)

        # 清理多余空行
        html = re.sub(r'\n{3,}', '\n\n', html)

        return html

    def _create_content_opf(self, title, author, book_id, images):
        """创建content.opf文件"""
        manifest_items = '\n'.join([
            f'    <item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>',
            f'    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            f'    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        ])

        # 添加图片项
        for i, img_info in enumerate(images):
            img_id = f"img{i}"
            img_path = img_info['epub_path']
            media_type = img_info.get('media_type', self._get_media_type(img_path))
            manifest_items += f'\n    <item id="{img_id}" href="{img_path}" media-type="{media_type}"/>'

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>zh-CN</dc:language>
    <dc:identifier id="BookId">urn:uuid:{book_id}</dc:identifier>
    <meta property="dcterms:modified">{datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}</meta>
  </metadata>
  <manifest>
{manifest_items}
  </manifest>
  <spine toc="ncx">
    <itemref idref="content"/>
  </spine>
</package>'''

    def _create_nav_xhtml(self, title):
        """创建nav.xhtml导航文件"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Table of Contents</title>
</head>
<body>
  <nav epub:type="toc">
    <h1>Table of Contents</h1>
    <ol>
      <li><a href="content.xhtml">{title}</a></li>
    </ol>
  </nav>
</body>
</html>'''

    def _create_toc_ncx(self, title, book_id):
        """创建toc.ncx文件 (EPUB 2.0兼容)"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:{book_id}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{title}</text>
  </docTitle>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel>
        <text>{title}</text>
      </navLabel>
      <content src="content.xhtml"/>
    </navPoint>
  </navMap>
</ncx>'''

    def _create_content_xhtml(self, title, author, source_url, date, html_content):
        """创建content.xhtml内容文件"""
        # 包装内容 - 简化版本，避免重复
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title}</title>
  <style type="text/css">
    body {{
      font-family: Georgia, "Times New Roman", serif;
      line-height: 1.6;
      margin: 1em;
      padding: 0;
    }}
    h1 {{
      font-size: 1.5em;
      margin-top: 0.5em;
      margin-bottom: 0.5em;
      text-align: center;
    }}
    h2 {{
      font-size: 1.3em;
      margin-top: 1em;
      border-bottom: 1px solid #ccc;
    }}
    h3 {{ font-size: 1.1em; margin-top: 0.8em; }}
    p {{ margin: 0.5em 0; text-align: justify; }}
    blockquote {{
      margin: 0.5em 2em;
      padding: 0.5em;
      border-left: 3px solid #ccc;
      background: #f9f9f9;
    }}
    img {{
      max-width: 100%;
      height: auto;
      display: block;
      margin: 1em auto;
    }}
    hr {{
      border: none;
      border-top: 1px solid #ccc;
      margin: 1em 0;
    }}
    ul, ol {{ padding-left: 1.5em; }}
    li {{ margin: 0.3em 0; }}
    a {{ color: #0066cc; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p style="text-align: center; color: #666; font-size: 0.9em;">
    Author: {author} | Source: <a href="{source_url}">{source_url}</a> | Date: {date}
  </p>
  <hr/>
  {html_content}
</body>
</html>'''

    def _create_container_xml(self):
        """创建container.xml"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''

    def _get_media_type(self, filename):
        """根据文件扩展名获取MIME类型"""
        ext = Path(filename).suffix.lower()
        types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.avif': 'image/avif',
            '.bmp': 'image/bmp',
        }
        return types.get(ext, 'application/octet-stream')

    def _convert_image_to_png(self, img_path):
        """将图片转换为PNG格式（用于EPUB兼容性）"""
        try:
            with Image.open(img_path) as img:
                # 转换为RGB模式（如果需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    # 保持透明度
                    img = img.convert('RGBA')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # 保存到内存中的PNG
                buffer = io.BytesIO()
                if img.mode == 'RGBA':
                    img.save(buffer, format='PNG')
                else:
                    img.save(buffer, format='PNG')
                buffer.seek(0)
                return buffer.read()
        except Exception as e:
            self.log(f"  图片转换失败 {img_path}: {str(e)}")
            return None

    def _strip_markdown_header(self, md_content):
        """移除Markdown内容的元数据头部"""
        lines = md_content.split('\n')
        result_lines = []
        in_header = True
        found_first_hrule = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 在header区域内
            if in_header:
                # 跳过标题行 (# Title)
                if stripped.startswith('# '):
                    continue
                # 跳过元数据引用块 (> **xxx**: yyy)
                if stripped.startswith('>') and ('**作者**' in stripped or '**原文链接**' in stripped or '**保存日期**' in stripped):
                    continue
                # 跳过空行在header区域
                if not stripped:
                    continue
                # 第一个分隔线后开始正文
                if stripped == '---':
                    found_first_hrule = True
                    in_header = False
                    continue
                # 如果既不是标题、引用块、空行也不是分隔线，说明header结束了
                if stripped:
                    in_header = False
                    result_lines.append(line)
            else:
                result_lines.append(line)

        return '\n'.join(result_lines)

    def _convert_with_pandoc(self, md_content, title, author, source_url, output_path, images_dir=None):
        """
        使用Pandoc将Markdown转换为EPUB
        步骤: MD -> HTML -> EPUB (两步转换确保图片正确处理)
        """
        pandoc = self._find_pandoc()
        if not pandoc:
            return False, "Pandoc not found"

        try:
            # 创建临时目录 - 使用绝对路径
            temp_dir = Path(tempfile.mkdtemp()).absolute()

            # 准备图片目录（如果有的话）
            media_dir = temp_dir / 'media'
            media_dir.mkdir(exist_ok=True)

            # 处理MD内容 - 移除头部元数据
            md_clean = self._strip_markdown_header(md_content)

            # 复制本地图片到临时目录并更新路径
            image_refs = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', md_clean)
            img_counter = 0

            if images_dir and image_refs:
                images_dir = Path(images_dir).absolute()
                for img_ref in image_refs:
                    if img_ref.startswith('images/'):
                        src_path = images_dir.parent / img_ref
                    elif not img_ref.startswith('http'):
                        src_path = images_dir / img_ref
                    else:
                        continue

                    if src_path.exists():
                        # 所有图片都转换为PNG以确保最大兼容性
                        img_counter += 1
                        new_name = f"img_{img_counter}.png"
                        dst_path = media_dir / new_name

                        png_data = self._convert_image_to_png(src_path)
                        if png_data:
                            dst_path.write_bytes(png_data)
                            md_clean = md_clean.replace(img_ref, f"media/{new_name}")
                            self.log(f"  转换图片: {src_path.name} -> PNG")
                        else:
                            # 转换失败，直接复制原图
                            ext = src_path.suffix
                            dst_path = media_dir / f"img_{img_counter}{ext}"
                            shutil.copy2(src_path, dst_path)
                            md_clean = md_clean.replace(img_ref, f"media/img_{img_counter}{ext}")
                            self.log(f"  复制图片(原图): {src_path.name}")

            # 添加标题作为一级标题（如果不存在）
            if not md_clean.strip().startswith('#'):
                md_clean = f"# {title}\n\n{md_clean}"

            # 写入临时MD文件 - 使用绝对路径
            temp_md = temp_dir / 'content.md'
            temp_md.write_text(md_clean, encoding='utf-8')

            temp_html = temp_dir / 'content.html'
            output_path = Path(output_path).absolute()

            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 步骤1: MD -> HTML
            self.log("  Pandoc: MD -> HTML...")
            cmd_md_to_html = [
                pandoc,
                str(temp_md.absolute()),
                '-o', str(temp_html.absolute()),
                '-f', 'markdown',
                '-t', 'html',
                '--standalone',
            ]

            result = subprocess.run(cmd_md_to_html, capture_output=True)
            if result.returncode != 0:
                stderr_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
                self.log(f"  Pandoc MD->HTML 错误: {stderr_msg[:200]}")
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, f"Pandoc MD->HTML failed: {stderr_msg[:200]}"

            # 步骤2: HTML -> EPUB
            self.log("  Pandoc: HTML -> EPUB...")

            # 先写入临时EPUB文件
            temp_epub = temp_dir / 'output.epub'

            # 简化命令 - 使用metadata参数直接传递标题和作者
            cmd_html_to_epub = [
                pandoc,
                str(temp_html.absolute()),
                '-o', str(temp_epub.absolute()),
                '-f', 'html',
                '-t', 'epub3',
                f'--metadata=title:{title}',
                f'--metadata=author:{author}',
            ]

            # 如果有图片，添加资源路径
            if img_counter > 0:
                cmd_html_to_epub.append(f'--resource-path={temp_dir}')

            result = subprocess.run(cmd_html_to_epub, capture_output=True)
            if result.returncode != 0:
                stderr_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
                self.log(f"  Pandoc HTML->EPUB 错误: {stderr_msg[:200]}")
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, f"Pandoc HTML->EPUB failed: {stderr_msg[:200]}"

            # 验证临时EPUB文件已创建
            if not temp_epub.exists() or temp_epub.stat().st_size == 0:
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, "EPUB file was not created or is empty"

            # 复制到最终位置
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(temp_epub, output_path)

            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)

            self.log(f"EPUB创建成功 (Pandoc): {output_path.name}")
            return True, str(output_path)

        except Exception as e:
            self.log(f"Pandoc转换失败: {str(e)}")
            # 确保清理临时目录
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False, str(e)

    def convert_to_epub(self, md_content, title, author, source_url, output_path, images_dir=None):
        """
        将Markdown内容转换为EPUB文件
        优先使用Pandoc，如果不可用则使用手动生成

        Args:
            md_content: Markdown内容
            title: 书名/标题
            author: 作者
            source_url: 原文链接
            output_path: EPUB输出路径
            images_dir: 图片目录路径（如果包含本地图片）

        Returns:
            tuple: (是否成功, 输出路径或错误信息)
        """
        # 优先尝试使用Pandoc
        if self.has_pandoc():
            self.log("正在转换为EPUB格式 (使用Pandoc)...")
            success, result = self._convert_with_pandoc(
                md_content, title, author, source_url, output_path, images_dir
            )
            if success:
                return True, result
            else:
                self.log(f"Pandoc转换失败，尝试手动生成: {result}")
                # Pandoc失败，继续尝试手动生成

        # 手动生成EPUB
        self.log("正在转换为EPUB格式 (手动生成)...")
        try:

            # 生成唯一ID
            book_id = str(uuid.uuid4())

            # 提取日期
            date = datetime.now().strftime('%Y-%m-%d')

            # 查找所有图片引用
            image_refs = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', md_content)
            images = []

            # 处理本地图片
            if images_dir and image_refs:
                self.log(f"处理 {len(image_refs)} 张图片...")
                images_dir = Path(images_dir)

                for i, img_ref in enumerate(image_refs):
                    # 处理相对路径
                    if img_ref.startswith('images/'):
                        img_path = images_dir.parent / img_ref
                    elif not img_ref.startswith('http'):
                        img_path = images_dir / img_ref
                    else:
                        continue  # 跳过网络图片

                    if img_path.exists():
                        # 转换图片为PNG格式以提高兼容性
                        img_filename = f"img_{i}.png"
                        epub_img_path = f"images/{img_filename}"

                        # 转换图片
                        png_data = self._convert_image_to_png(img_path)
                        if png_data:
                            images.append({
                                'original_ref': img_ref,
                                'epub_path': epub_img_path,
                                'image_data': png_data,
                                'media_type': 'image/png'
                            })
                            self.log(f"  包含图片: {img_filename}")
                        else:
                            # 如果转换失败，尝试直接使用原图
                            img_data = img_path.read_bytes()
                            img_filename_orig = f"img_{i}{img_path.suffix}"
                            epub_img_path_orig = f"images/{img_filename_orig}"
                            images.append({
                                'original_ref': img_ref,
                                'epub_path': epub_img_path_orig,
                                'image_data': img_data,
                                'media_type': self._get_media_type(img_path.suffix)
                            })
                            self.log(f"  包含图片(原图): {img_filename_orig}")

            # 更新Markdown中的图片路径为EPUB路径
            md_updated = md_content
            for img_info in images:
                md_updated = md_updated.replace(img_info['original_ref'], img_info['epub_path'])

            # 转换Markdown到HTML - 先移除头部元数据
            md_for_html = self._strip_markdown_header(md_updated)
            html_content = self._markdown_to_html(md_for_html, title)

            # 创建EPUB文件
            output_path = Path(output_path)

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
                # 1. mimetype必须第一个且不压缩
                epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

                # 2. META-INF/container.xml
                epub.writestr('META-INF/container.xml', self._create_container_xml())

                # 3. OEBPS/content.opf
                epub.writestr('OEBPS/content.opf',
                              self._create_content_opf(title, author, book_id, images))

                # 4. OEBPS/nav.xhtml (EPUB 3.0)
                epub.writestr('OEBPS/nav.xhtml', self._create_nav_xhtml(title))

                # 5. OEBPS/toc.ncx (EPUB 2.0 compatibility)
                epub.writestr('OEBPS/toc.ncx', self._create_toc_ncx(title, book_id))

                # 6. OEBPS/content.xhtml
                epub.writestr('OEBPS/content.xhtml',
                              self._create_content_xhtml(title, author, source_url, date, html_content))

                # 7. 添加图片
                for img_info in images:
                    epub.writestr(f"OEBPS/{img_info['epub_path']}", img_info['image_data'])

            self.log(f"EPUB创建成功: {output_path.name}")
            return True, str(output_path)

        except Exception as e:
            self.log(f"EPUB转换失败: {str(e)}")
            return False, str(e)


class GeneralArticleFetcher:
    """通用文章获取器 - 支持微信公众号、Notion博客等"""

    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.image_downloader = ImageDownloader(log_callback)
        self.image_urls = []
        self.raw_html = ""  # 保存原始HTML
        self.source_type = "unknown"  # 文章来源类型

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        print(message)

    def _detect_source_type(self, url, html):
        """检测文章来源类型"""
        if 'mp.weixin.qq.com' in url:
            return 'wechat'
        elif 'notion.com' in url or 'notion.site' in url:
            return 'notion'
        elif 'medium.com' in url:
            return 'medium'
        elif 'zhuanlan.zhihu.com' in url:
            return 'zhihu'
        else:
            return 'general'

    def fetch_article(self, url):
        """获取并解析文章"""
        self.log("正在获取文章...")
        self.image_urls = []
        self.raw_html = ""

        html = self._fetch_html(url)
        if not html:
            return None

        self.raw_html = html
        self.log("正在解析内容...")

        # 检测来源类型
        self.source_type = self._detect_source_type(url, html)
        self.log(f"来源类型: {self.source_type}")

        # 更新图片下载器的 Referer
        self.image_downloader.headers['Referer'] = url

        # 根据来源类型选择解析方法
        if self.source_type == 'wechat':
            title, author, content_html = self._extract_wechat_content(html)
        elif self.source_type == 'notion':
            title, author, content_html = self._extract_notion_content(html)
        else:
            title, author, content_html = self._extract_general_content(html)

        if not title:
            title = "未命名文章"

        self.log(f"标题: {title}")
        self.log(f"作者: {author}")

        # 提取图片URL
        self.image_urls = self._extract_image_urls(content_html, url)
        self.log(f"图片数量: {len(self.image_urls)}")

        # 生成Markdown
        md_content = self._html_to_markdown(content_html)
        md_with_header = self._generate_markdown(url, title, author, md_content)

        # 生成保留样式的HTML
        html_content = self._generate_styled_html(url, title, author, content_html)

        return {
            'title': title,
            'author': author,
            'content': md_with_header,
            'html_content': html_content,
            'content_html': content_html,
            'filename': self._sanitize_filename(title),
            'image_urls': self.image_urls,
            'source_type': self.source_type
        }

    def _fetch_html(self, url):
        """获取HTML内容"""
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
            self.log(f"网络错误: {e}")
            return None
        except Exception as e:
            self.log(f"获取失败: {e}")
            return None

    def _extract_wechat_content(self, html):
        """提取微信公众号文章标题、作者和内容HTML"""
        # 提取标题
        title_match = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html)
        if not title_match:
            title_match = re.search(r'<h1[^>]*class="[^"]*rich_media_title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL)
        if not title_match:
            title_match = re.search(r'<title>(.*?)</title>', html)

        title = ""
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            title = re.sub(r'\s*[-_|]\s*微信公众号.*$', '', title)

        # 提取作者
        author_match = re.search(r'<meta[^>]*name="author"[^>]*content="([^"]*)"', html)
        if not author_match:
            author_match = re.search(r'var\s+nickname\s*=\s*["\']([^"\']+)["\']', html)
        author = author_match.group(1) if author_match else "未知作者"

        # 提取内容区域 - 保留原始HTML（包括所有内联样式）
        content_match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*(?:<div[^>]*class="[^"]*rich_media_tool|<script)', html, re.DOTALL)

        if not content_match:
            content_match = re.search(r'<div[^>]*class="[^"]*rich_media_content[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)

        if content_match:
            content_html = content_match.group(1)
        else:
            self.log("警告: 使用备用解析方式")
            content_html = html

        # 清理脚本和样式标签，但保留内联style属性
        content_html = re.sub(r'<script[^>]*>.*?</script>', '', content_html, flags=re.DOTALL | re.I)
        content_html = re.sub(r'<style[^>]*>.*?</style>', '', content_html, flags=re.DOTALL | re.I)

        return title, author, content_html

    def _extract_notion_content(self, html):
        """提取Notion博客文章标题、作者和内容HTML"""
        # 提取标题
        title_match = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html)
        if not title_match:
            title_match = re.search(r'<meta[^>]*name="title"[^>]*content="([^"]*)"', html)
        if not title_match:
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if not title_match:
            title_match = re.search(r'<title>(.*?)</title>', html)

        title = ""
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            title = re.sub(r'\s*[-_|]\s*Notion.*$', '', title, flags=re.I)

        # 提取作者
        author_match = re.search(r'<meta[^>]*name="author"[^>]*content="([^"]*)"', html)
        if not author_match:
            author_match = re.search(r'"authorName"\s*:\s*"([^"]*)"', html)
        if not author_match:
            author_match = re.search(r'by\s+([A-Za-z\s]+)', html, re.I)
        author = author_match.group(1) if author_match else "Notion"

        # 提取内容区域 - Notion的文章通常在 article 标签或特定class中
        content_match = re.search(r'<article[^>]*class="[^"]*[^"]*"[^>]*>(.*?)</article>', html, re.DOTALL)

        if not content_match:
            # 尝试匹配 notion-content 或 main 内容
            content_match = re.search(r'<div[^>]*class="[^"]*notion-page-content[^"]*"[^>]*>(.*?)</div>\s*(?:<footer|</main|<div[^>]*class="[^"]*footer)', html, re.DOTALL)

        if not content_match:
            # 尝试匹配 article 标签
            content_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)

        if not content_match:
            # 尝试匹配 main 标签
            content_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)

        if content_match:
            content_html = content_match.group(1)
        else:
            self.log("警告: Notion内容解析使用备用方式")
            # 移除头部和尾部，保留主要内容
            content_html = html
            # 移除常见的非内容区域
            content_html = re.sub(r'<header[^>]*>.*?</header>', '', content_html, flags=re.DOTALL | re.I)
            content_html = re.sub(r'<footer[^>]*>.*?</footer>', '', content_html, flags=re.DOTALL | re.I)
            content_html = re.sub(r'<nav[^>]*>.*?</nav>', '', content_html, flags=re.DOTALL | re.I)

        # 清理脚本和样式标签
        content_html = re.sub(r'<script[^>]*>.*?</script>', '', content_html, flags=re.DOTALL | re.I)
        content_html = re.sub(r'<style[^>]*>.*?</style>', '', content_html, flags=re.DOTALL | re.I)

        return title, author, content_html

    def _extract_general_content(self, html):
        """提取通用网页文章标题、作者和内容HTML"""
        # 提取标题
        title_match = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html)
        if not title_match:
            title_match = re.search(r'<meta[^>]*name="title"[^>]*content="([^"]*)"', html)
        if not title_match:
            title_match = re.search(r'<meta[^>]*name="twitter:title"[^>]*content="([^"]*)"', html)
        if not title_match:
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if not title_match:
            title_match = re.search(r'<title>(.*?)</title>', html)

        title = ""
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

        # 提取作者
        author_match = re.search(r'<meta[^>]*name="author"[^>]*content="([^"]*)"', html)
        if not author_match:
            author_match = re.search(r'<meta[^>]*property="article:author"[^>]*content="([^"]*)"', html)
        if not author_match:
            author_match = re.search(r'<span[^>]*class="[^"]*author[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
        author = "未知作者"
        if author_match:
            author = re.sub(r'<[^>]+>', '', author_match.group(1)).strip()
            if not author:
                author = "未知作者"

        # 提取内容区域 - 尝试多种常见的内容区域选择器
        content_html = ""

        # 尝试 article 标签
        content_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
        if content_match:
            content_html = content_match.group(1)

        # 尝试 main 标签
        if not content_html:
            content_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)
            if content_match:
                content_html = content_match.group(1)

        # 尝试常见的内容class
        if not content_html:
            for pattern in [
                r'<div[^>]*class="[^"]*post-content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*article-content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*id="content"[^>]*>(.*?)</div>',
                r'<div[^>]*id="article"[^>]*>(.*?)</div>',
            ]:
                content_match = re.search(pattern, html, re.DOTALL)
                if content_match:
                    content_html = content_match.group(1)
                    break

        # 如果还是没有找到，使用整个body
        if not content_html:
            self.log("警告: 通用内容解析使用备用方式")
            content_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
            if content_match:
                content_html = content_match.group(1)
            else:
                content_html = html

        # 清理脚本、样式、导航等非内容元素
        content_html = re.sub(r'<script[^>]*>.*?</script>', '', content_html, flags=re.DOTALL | re.I)
        content_html = re.sub(r'<style[^>]*>.*?</style>', '', content_html, flags=re.DOTALL | re.I)
        content_html = re.sub(r'<header[^>]*>.*?</header>', '', content_html, flags=re.DOTALL | re.I)
        content_html = re.sub(r'<footer[^>]*>.*?</footer>', '', content_html, flags=re.DOTALL | re.I)
        content_html = re.sub(r'<nav[^>]*>.*?</nav>', '', content_html, flags=re.DOTALL | re.I)
        content_html = re.sub(r'<aside[^>]*>.*?</aside>', '', content_html, flags=re.DOTALL | re.I)

        return title, author, content_html

    def _extract_image_urls(self, html, base_url=None):
        """提取所有图片URL"""
        urls = []
        from urllib.parse import urljoin, urlparse, unquote

        # 匹配src属性（优先使用原始src，不提取代理URL中的实际URL）
        for match in re.finditer(r'<img[^>]*src=["\']([^"\']+)["\']', html, re.I):
            url = match.group(1)
            if url.startswith('data:'):
                continue

            # 解码HTML实体（&amp; -> & 等）
            url = url.replace('&amp;', '&')
            url = url.replace('&lt;', '<')
            url = url.replace('&gt;', '>')
            url = url.replace('&quot;', '"')

            # 处理相对URL
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                # 对于 Notion 的图片代理URL，构建完整的代理URL
                if '/_next/image?url=' in url and base_url:
                    # 从base_url提取域名
                    parsed_base = urlparse(base_url)
                    url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                elif base_url:
                    url = urljoin(base_url, url)
                else:
                    continue
            elif not url.startswith('http'):
                continue

            if url not in urls:
                urls.append(url)
        return urls

    def _html_to_markdown(self, html):
        """HTML转Markdown"""
        # 预处理
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

        # 处理图片 - 同时规范化URL（// 开头的转为 https://）
        def process_img_tag(match):
            full_match = match.group(0)
            # 提取 data-src 或 src
            src_match = re.search(r'(?:data-src|src)="([^"]+)"', full_match)
            if not src_match:
                return ''
            url = src_match.group(1)

            # 规范化URL
            if url.startswith('//'):
                url = 'https:' + url

            # 提取 alt
            alt_match = re.search(r'alt="([^"]*)"', full_match)
            alt = alt_match.group(1) if alt_match else '图片'

            return f'\n\n![{alt}]({url})\n\n'

        html = re.sub(r'<img[^>]*>', process_img_tag, html, flags=re.I)

        # 处理标题
        for i in range(6, 0, -1):
            html = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', rf'\n\n{"#" * i} \1\n', html, flags=re.DOTALL)

        # 处理section
        html = re.sub(r'<section[^>]*>(.*?)</section>', r'\1', html, flags=re.DOTALL)

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
        def process_blockquote(match):
            content = match.group(1)
            lines = content.strip().split('\n')
            result = '\n'
            for line in lines:
                if line.strip():
                    result += f'> {line.strip()}\n'
            return result + '\n'

        html = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', process_blockquote, html, flags=re.DOTALL)

        # 处理列表
        html = re.sub(r'<ul[^>]*>(.*?)</ul>', r'\n\1\n', html, flags=re.DOTALL)
        html = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', html, flags=re.DOTALL)

        def replace_ol(match):
            items = re.findall(r'<li[^>]*>(.*?)</li>', match.group(1), re.DOTALL)
            result = '\n'
            for i, item in enumerate(items, 1):
                result += f'{i}. {item.strip()}\n'
            return result

        html = re.sub(r'<ol[^>]*>(.*?)</ol>', replace_ol, html, flags=re.DOTALL)

        # 处理表格
        def process_table(match):
            table_html = match.group(0)
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
            md_table = '\n'
            for i, row in enumerate(rows):
                cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
                cell_text = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                md_table += '| ' + ' | '.join(cell_text) + ' |\n'
                if i == 0:
                    md_table += '|' + '|'.join(['---'] * len(cells)) + '|\n'
            return md_table + '\n'

        html = re.sub(r'<table[^>]*>.*?</table>', process_table, html, flags=re.DOTALL)

        # 处理代码块
        html = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', r'\n\n```\n\1\n```\n', html, flags=re.DOTALL)
        html = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n\n```\n\1\n```\n', html, flags=re.DOTALL)
        html = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', html, flags=re.DOTALL)

        # 处理分隔线
        html = re.sub(r'<hr\s*/?>', r'\n\n---\n\n', html)

        # 处理span和div
        html = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', html, flags=re.DOTALL)
        html = re.sub(r'<div[^>]*>(.*?)</div>', r'\1', html, flags=re.DOTALL)

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
        html = html.replace('\ufeff', '')

        # 清理多余空白
        html = re.sub(r'\n{3,}', '\n\n', html)
        lines = html.split('\n')
        html = '\n'.join(line.rstrip() for line in lines)

        return html.strip()

    def _generate_markdown(self, url, title, author, content):
        """生成Markdown文件内容"""
        today = datetime.now().strftime('%Y-%m-%d')
        return f"""# {title}

> **作者**: {author}
> **原文链接**: {url}
> **保存日期**: {today}

---

{content}
"""

    def _generate_styled_html(self, url, title, author, content_html):
        """生成保留样式的HTML文件"""
        today = datetime.now().strftime('%Y-%m-%d')

        # 微信公众号样式CSS - 使用较低优先级，让内联样式优先生效
        css = """
        * {
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }
        .article-header {
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }
        .article-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #000;
        }
        .article-meta {
            font-size: 14px;
            color: #999;
        }
        .article-meta a {
            color: #576b95;
            text-decoration: none;
        }
        .article-content {
            font-size: 17px;
            overflow-wrap: break-word;
        }
        /* 基础段落样式 - 但内联样式会覆盖这些 */
        .article-content p {
            margin: 1em 0;
        }
        /* 图片样式 */
        .article-content img {
            max-width: 100% !important;
            height: auto !important;
        }
        /* 表格样式 */
        .article-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }
        .article-content th, .article-content td {
            border: 1px solid #ddd;
            padding: 8px 12px;
        }
        /* 引用块样式 */
        .article-content blockquote {
            border-left: 4px solid #1aad19;
            padding: 10px 20px;
            margin: 1em 0;
            background-color: #f8f8f8;
        }
        /* 代码块样式 */
        .article-content pre {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        .article-content code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: Consolas, Monaco, monospace;
        }
        .article-content pre code {
            background: none;
            padding: 0;
        }
        /* 链接样式 */
        .article-content a {
            color: #576b95;
        }
        /* 分隔线 */
        .article-content hr {
            border: none;
            border-top: 1px solid #eee;
            margin: 2em 0;
        }
        /* 列表样式 */
        .article-content ul, .article-content ol {
            padding-left: 2em;
        }
        /* section标签处理 */
        .article-content section {
            display: block;
        }
        /* 重要：让所有内联样式优先生效 */
        .article-content [style] {
            /* 内联样式自动具有更高优先级 */
        }
        """

        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{css}</style>
</head>
<body>
    <div class="article-header">
        <h1 class="article-title">{title}</h1>
        <div class="article-meta">
            <strong>作者:</strong> {author} |
            <strong>保存日期:</strong> {today} |
            <a href="{url}" target="_blank">原文链接</a>
        </div>
    </div>
    <div class="article-content">
{content_html}
    </div>
</body>
</html>"""
        return html_template

    def _sanitize_filename(self, title):
        """清理文件名"""
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = re.sub(r'\s+', '_', filename)
        if len(filename) > 100:
            filename = filename[:100]
        return filename if filename else 'article'

    def replace_image_urls(self, content, url_mapping):
        """替换图片URL为本地路径"""
        from urllib.parse import urlparse

        for original_url, local_path in url_mapping.items():
            # Replace full URL
            content = content.replace(original_url, local_path)

            # Also try to replace relative URL version (for Notion proxy URLs)
            parsed = urlparse(original_url)
            if parsed.path and parsed.path.startswith('/'):
                relative_url = parsed.path
                if parsed.query:
                    relative_url += '?' + parsed.query
                content = content.replace(relative_url, local_path)

        return content


class ArticleFetcherGUI:
    """图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("网页文章保存工具 - 支持微信/Notion/通用网页")
        self.root.geometry("900x800")
        self.root.minsize(700, 600)

        self.style = ttk.Style()
        self.style.configure('TButton', padding=6)
        self.style.configure('TEntry', padding=6)

        self.fetcher = GeneralArticleFetcher(log_callback=self.log)
        self.current_result = None
        self.save_dir = Path.cwd() / 'output'  # 默认保存到 output 目录
        self.batch_running = False

        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建选项卡
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 单篇下载选项卡
        self.single_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.single_tab, text="单篇下载")
        self._create_single_tab()

        # 批量下载选项卡
        self.batch_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.batch_tab, text="批量下载")
        self._create_batch_tab()

        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪 - 支持微信公众号、Notion博客及通用网页文章")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=(5, 0))

    def _create_single_tab(self):
        """创建单篇下载界面"""
        # URL输入区
        url_frame = ttk.LabelFrame(self.single_tab, text="文章链接 (支持微信/Notion/通用网页)", padding="10")
        url_frame.pack(fill=tk.X, pady=(0, 10))

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=('Arial', 11))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.url_entry.bind('<Return>', lambda e: self.fetch_article())

        btn_frame = ttk.Frame(url_frame)
        btn_frame.pack(side=tk.RIGHT)

        self.fetch_btn = ttk.Button(btn_frame, text="获取文章", command=self.fetch_article, width=12)
        self.fetch_btn.pack(side=tk.LEFT, padx=2)

        self.paste_btn = ttk.Button(btn_frame, text="粘贴", command=self.paste_url, width=6)
        self.paste_btn.pack(side=tk.LEFT, padx=2)

        # 选项区
        options_frame = ttk.LabelFrame(self.single_tab, text="选项", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        # 保存目录
        dir_frame = ttk.Frame(options_frame)
        dir_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(dir_frame, text="保存目录:").pack(side=tk.LEFT)
        self.dir_var = tk.StringVar(value=str(self.save_dir))
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, state='readonly')
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(dir_frame, text="浏览...", command=self.browse_dir, width=8).pack(side=tk.LEFT)

        # 选项复选框
        options_row = ttk.Frame(options_frame)
        options_row.pack(fill=tk.X, pady=(5, 0))

        # 保存格式
        ttk.Label(options_row, text="保存格式:").pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value="md")
        ttk.Radiobutton(options_row, text="HTML(保留样式)", variable=self.format_var, value="html").pack(side=tk.LEFT, padx=(5, 10))
        ttk.Radiobutton(options_row, text="Markdown", variable=self.format_var, value="md").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(options_row, text="EPUB(电子书)", variable=self.format_var, value="epub").pack(side=tk.LEFT, padx=(0, 20))

        # 图片下载选项
        self.download_images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_row,
            text="下载图片到本地 (images子目录)",
            variable=self.download_images_var
        ).pack(side=tk.LEFT)

        # 图片数量显示
        self.img_count_var = tk.StringVar(value="")
        ttk.Label(options_row, textvariable=self.img_count_var, foreground='gray').pack(side=tk.RIGHT)

        # 操作按钮区
        action_frame = ttk.LabelFrame(self.single_tab, text="操作", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))

        btn_row = ttk.Frame(action_frame)
        btn_row.pack(fill=tk.X)

        self.progress = ttk.Progressbar(btn_row, mode='indeterminate', length=120)
        self.progress.pack(side=tk.LEFT, padx=(0, 20))

        self.clear_btn = ttk.Button(btn_row, text="清空", command=self.clear_all, width=10)
        self.clear_btn.pack(side=tk.LEFT, padx=2)

        self.open_btn = ttk.Button(btn_row, text="打开目录", command=self.open_dir, width=10)
        self.open_btn.pack(side=tk.LEFT, padx=2)

        self.img_status_var = tk.StringVar(value="")
        ttk.Label(btn_row, textvariable=self.img_status_var, foreground='#666').pack(side=tk.LEFT, padx=10)

        self.save_btn = ttk.Button(btn_row, text="保存文件", command=self.save_article, width=12, state=tk.DISABLED)
        self.save_btn.pack(side=tk.RIGHT, padx=2)

        # 预览区
        preview_frame = ttk.LabelFrame(self.single_tab, text="内容预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.preview_text = scrolledtext.ScrolledText(
            preview_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg='#fafafa'
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)

    def _create_batch_tab(self):
        """创建批量下载界面"""
        # URL列表输入区
        url_frame = ttk.LabelFrame(self.batch_tab, text="文章链接列表 (每行一个链接，支持微信/Notion/通用网页)", padding="10")
        url_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建带滚动条的文本框
        text_frame = ttk.Frame(url_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.batch_urls_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg='#fafafa',
            height=8
        )
        self.batch_urls_text.pack(fill=tk.BOTH, expand=True)

        # 批量选项区
        batch_options = ttk.LabelFrame(self.batch_tab, text="批量下载选项", padding="10")
        batch_options.pack(fill=tk.X, pady=(0, 10))

        # 第一行：目录和格式
        row1 = ttk.Frame(batch_options)
        row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row1, text="保存目录:").pack(side=tk.LEFT)
        self.batch_dir_var = tk.StringVar(value=str(self.save_dir))
        ttk.Entry(row1, textvariable=self.batch_dir_var, state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(row1, text="浏览...", command=self.browse_batch_dir, width=8).pack(side=tk.LEFT)

        # 第二行：格式和选项
        row2 = ttk.Frame(batch_options)
        row2.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(row2, text="保存格式:").pack(side=tk.LEFT)
        self.batch_format_var = tk.StringVar(value="md")
        ttk.Radiobutton(row2, text="HTML", variable=self.batch_format_var, value="html").pack(side=tk.LEFT, padx=(5, 10))
        ttk.Radiobutton(row2, text="Markdown", variable=self.batch_format_var, value="md").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(row2, text="EPUB", variable=self.batch_format_var, value="epub").pack(side=tk.LEFT, padx=(0, 20))

        self.batch_download_images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="下载图片到本地", variable=self.batch_download_images_var).pack(side=tk.LEFT)

        # 操作按钮区
        action_frame = ttk.Frame(batch_options)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        self.batch_progress = ttk.Progressbar(action_frame, mode='determinate', length=200)
        self.batch_progress.pack(side=tk.LEFT, padx=(0, 20))

        self.batch_progress_label = ttk.Label(action_frame, text="")
        self.batch_progress_label.pack(side=tk.LEFT, padx=10)

        ttk.Button(action_frame, text="打开目录", command=self.open_batch_dir, width=10).pack(side=tk.RIGHT, padx=2)
        ttk.Button(action_frame, text="清空列表", command=self.clear_batch_urls, width=10).pack(side=tk.RIGHT, padx=2)

        self.batch_start_btn = ttk.Button(action_frame, text="开始批量下载", command=self.start_batch_download, width=14)
        self.batch_start_btn.pack(side=tk.RIGHT, padx=2)

        self.batch_stop_btn = ttk.Button(action_frame, text="停止", command=self.stop_batch_download, width=8, state=tk.DISABLED)
        self.batch_stop_btn.pack(side=tk.RIGHT, padx=2)

        # 日志区
        log_frame = ttk.LabelFrame(self.batch_tab, text="下载日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.batch_log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            height=10
        )
        self.batch_log_text.pack(fill=tk.BOTH, expand=True)
        self.batch_log_text.config(state=tk.DISABLED)

    def log(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def paste_url(self):
        try:
            clipboard = self.root.clipboard_get()
            self.url_var.set(clipboard)
        except tk.TclError:
            pass

    def browse_dir(self):
        dir_path = filedialog.askdirectory(initialdir=self.save_dir)
        if dir_path:
            self.save_dir = Path(dir_path)
            self.dir_var.set(str(self.save_dir))

    def open_dir(self):
        os.startfile(str(self.save_dir))

    def fetch_article(self):
        url = self.url_var.get().strip()

        if not url:
            messagebox.showwarning("提示", "请输入文章链接")
            return

        # 验证URL格式
        if not url.startswith('http://') and not url.startswith('https://'):
            messagebox.showwarning("提示", "请输入有效的URL（以 http:// 或 https:// 开头）")
            return

        self.fetch_btn.config(state=tk.DISABLED)
        self.progress.start()

        thread = threading.Thread(target=self._fetch_thread, args=(url,))
        thread.daemon = True
        thread.start()

    def _fetch_thread(self, url):
        try:
            result = self.fetcher.fetch_article(url)
            self.root.after(0, lambda: self._fetch_complete(result))
        except Exception as e:
            self.root.after(0, lambda: self._fetch_error(str(e)))

    def _fetch_complete(self, result):
        self.progress.stop()
        self.fetch_btn.config(state=tk.NORMAL)

        if result:
            self.current_result = result

            # 显示预览
            self.preview_text.delete('1.0', tk.END)
            if self.format_var.get() == "html":
                self.preview_text.insert('1.0', result['html_content'])
            else:
                self.preview_text.insert('1.0', result['content'])

            # 更新图片数量
            img_count = len(result.get('image_urls', []))
            if img_count > 0:
                self.img_status_var.set(f"发现 {img_count} 张图片")
            else:
                self.img_status_var.set("")

            self.save_btn.config(state=tk.NORMAL)
            self.status_var.set(f"获取成功: {result['title']}")
        else:
            self.status_var.set("获取失败")
            messagebox.showerror("错误", "无法获取文章内容")

    def _fetch_error(self, error):
        self.progress.stop()
        self.fetch_btn.config(state=tk.NORMAL)
        self.status_var.set(f"错误: {error}")
        messagebox.showerror("错误", f"获取文章时发生错误:\n{error}")

    def save_article(self):
        if not self.current_result:
            return

        self.save_btn.config(state=tk.DISABLED)
        self.progress.start()

        thread = threading.Thread(target=self._save_thread)
        thread.daemon = True
        thread.start()

    def _save_thread(self):
        try:
            result = self.current_result
            base_filename = result['filename']
            save_format = self.format_var.get()

            # 下载图片
            image_urls = result.get('image_urls', [])
            url_mapping = {}

            # EPUB格式需要强制下载图片
            need_download_images = self.download_images_var.get() or save_format == "epub"
            if need_download_images and image_urls:
                self.root.after(0, lambda: self.log("正在下载图片..."))
                images_dir = self.save_dir / 'images'
                url_mapping = self.fetcher.image_downloader.download_images(
                    image_urls,
                    images_dir,
                    progress_callback=self._download_progress
                )

            # 根据格式保存
            if save_format == "html":
                filepath = self.save_dir / (base_filename + '.html')
                content = result['html_content']
                content = self.fetcher.replace_image_urls(content, url_mapping)
                filepath.write_text(content, encoding='utf-8')
            elif save_format == "epub":
                filepath = self.save_dir / (base_filename + '.epub')
                # 对于EPUB，使用包含本地图片路径的Markdown内容
                md_content = result['content']
                md_content = self.fetcher.replace_image_urls(md_content, url_mapping)

                # 提取来源URL
                source_url = ""
                url_match = re.search(r'\*\*原文链接\*\*:\s*(.+)', md_content)
                if url_match:
                    source_url = url_match.group(1).strip()

                # 提取作者
                author = result.get('author', '未知作者')

                # 创建EPUB
                epub_converter = EpubConverter(log_callback=self.log)
                success, result_path = epub_converter.convert_to_epub(
                    md_content=md_content,
                    title=result['title'],
                    author=author,
                    source_url=source_url,
                    output_path=filepath,
                    images_dir=self.save_dir / 'images'
                )
                if not success:
                    raise Exception(result_path)
            else:
                filepath = self.save_dir / (base_filename + '.md')
                content = result['content']
                content = self.fetcher.replace_image_urls(content, url_mapping)
                filepath.write_text(content, encoding='utf-8')

            downloaded = sum(1 for v in url_mapping.values() if v.startswith('images/'))
            failed = len(image_urls) - downloaded

            self.root.after(0, lambda: self._save_complete(filepath, downloaded, failed))

        except Exception as e:
            self.root.after(0, lambda: self._save_error(str(e)))

    def _download_progress(self, current, total, url):
        self.root.after(0, lambda: self.log(f"下载图片 {current}/{total}..."))

    def _save_complete(self, filepath, downloaded, failed):
        self.progress.stop()
        self.save_btn.config(state=tk.NORMAL)

        # 更新预览
        if self.current_result:
            self.preview_text.delete('1.0', tk.END)
            content = filepath.read_text(encoding='utf-8')
            self.preview_text.insert('1.0', content)

        msg = f"已保存: {filepath.name}"
        if downloaded > 0:
            msg += f" | 图片: {downloaded}张"
            if failed > 0:
                msg += f" (失败{failed}张)"

        self.status_var.set(msg)

        if messagebox.askyesno("成功", f"文件已保存:\n{filepath}\n\n是否打开文件?"):
            os.startfile(str(filepath))

    def _save_error(self, error):
        self.progress.stop()
        self.save_btn.config(state=tk.NORMAL)
        self.status_var.set(f"错误: {error}")
        messagebox.showerror("错误", f"保存失败:\n{error}")

    def clear_all(self):
        self.url_var.set('')
        self.preview_text.delete('1.0', tk.END)
        self.current_result = None
        self.img_status_var.set("")
        self.save_btn.config(state=tk.DISABLED)
        self.status_var.set("就绪 - 支持微信公众号、Notion博客及通用网页文章")

    # ========== 批量下载方法 ==========

    def browse_batch_dir(self):
        dir_path = filedialog.askdirectory(initialdir=self.save_dir)
        if dir_path:
            self.batch_dir_var.set(dir_path)

    def open_batch_dir(self):
        dir_path = self.batch_dir_var.get()
        if Path(dir_path).exists():
            os.startfile(dir_path)
        else:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            os.startfile(dir_path)

    def clear_batch_urls(self):
        self.batch_urls_text.delete('1.0', tk.END)
        self.batch_log_text.config(state=tk.NORMAL)
        self.batch_log_text.delete('1.0', tk.END)
        self.batch_log_text.config(state=tk.DISABLED)

    def batch_log(self, message):
        """向批量下载日志添加消息"""
        self.batch_log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.batch_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.batch_log_text.see(tk.END)
        self.batch_log_text.config(state=tk.DISABLED)

    def start_batch_download(self):
        """开始批量下载"""
        # 获取URL列表
        urls_text = self.batch_urls_text.get('1.0', tk.END).strip()
        if not urls_text:
            messagebox.showwarning("提示", "请输入文章链接列表")
            return

        # 解析URL - 支持所有HTTP/HTTPS链接
        urls = []
        for line in urls_text.split('\n'):
            url = line.strip()
            if url and (url.startswith('http://') or url.startswith('https://')):
                urls.append(url)

        if not urls:
            messagebox.showwarning("提示", "未找到有效的文章链接（需要 http:// 或 https:// 开头）")
            return

        # 确认开始
        if not messagebox.askyesno("确认", f"即将下载 {len(urls)} 篇文章\n是否继续?"):
            return

        # 创建输出目录
        self.batch_save_dir = Path(self.batch_dir_var.get())
        self.batch_save_dir.mkdir(parents=True, exist_ok=True)

        # 更新UI状态
        self.batch_running = True
        self.batch_start_btn.config(state=tk.DISABLED)
        self.batch_stop_btn.config(state=tk.NORMAL)
        self.batch_progress['maximum'] = len(urls)
        self.batch_progress['value'] = 0

        # 清空日志
        self.batch_log_text.config(state=tk.NORMAL)
        self.batch_log_text.delete('1.0', tk.END)
        self.batch_log_text.config(state=tk.DISABLED)

        self.batch_log(f"开始批量下载，共 {len(urls)} 篇文章")
        self.batch_log(f"保存目录: {self.batch_save_dir}")
        self.batch_log("-" * 50)

        # 启动下载线程
        self.batch_urls = urls
        self.batch_index = 0
        self.batch_success = 0
        self.batch_failed = 0
        self.batch_total_images = 0

        thread = threading.Thread(target=self._batch_download_thread)
        thread.daemon = True
        thread.start()

    def stop_batch_download(self):
        """停止批量下载"""
        self.batch_running = False
        self.batch_log("正在停止下载...")

    def _batch_download_thread(self):
        """批量下载线程"""
        save_format = self.batch_format_var.get()
        download_images = self.batch_download_images_var.get()

        for i, url in enumerate(self.batch_urls):
            if not self.batch_running:
                self.root.after(0, lambda: self.batch_log("下载已停止"))
                break

            self.batch_index = i + 1
            self.root.after(0, lambda idx=i+1, total=len(self.batch_urls):
                           self._update_batch_progress(idx, total))
            self.root.after(0, lambda u=url: self.batch_log(f"正在获取: {u[:60]}..."))

            try:
                # 获取文章
                fetcher = GeneralArticleFetcher()
                result = fetcher.fetch_article(url)

                if not result:
                    self.root.after(0, lambda: self.batch_log("  ✗ 获取失败"))
                    self.batch_failed += 1
                    continue

                title = result['title']
                self.root.after(0, lambda t=title: self.batch_log(f"  标题: {t}"))

                # 下载图片 (EPUB格式需要强制下载)
                image_urls = result.get('image_urls', [])
                url_mapping = {}

                need_download = download_images or save_format == "epub"
                if need_download and image_urls:
                    self.root.after(0, lambda n=len(image_urls):
                                   self.batch_log(f"  下载 {n} 张图片..."))
                    images_dir = self.batch_save_dir / 'images'
                    url_mapping = fetcher.image_downloader.download_images(image_urls, images_dir)

                    downloaded = sum(1 for v in url_mapping.values() if v.startswith('images/'))
                    self.batch_total_images += downloaded
                    self.root.after(0, lambda d=downloaded, t=len(image_urls):
                                   self.batch_log(f"  图片: {d}/{t} 张下载成功"))

                # 保存文件
                base_filename = result['filename']
                if save_format == "html":
                    filepath = self.batch_save_dir / (base_filename + '.html')
                    content = result['html_content']
                    content = fetcher.replace_image_urls(content, url_mapping)
                    filepath.write_text(content, encoding='utf-8')
                elif save_format == "epub":
                    filepath = self.batch_save_dir / (base_filename + '.epub')
                    md_content = result['content']
                    md_content = fetcher.replace_image_urls(md_content, url_mapping)

                    # 提取来源URL
                    source_url = ""
                    url_match = re.search(r'\*\*原文链接\*\*:\s*(.+)', md_content)
                    if url_match:
                        source_url = url_match.group(1).strip()

                    epub_converter = EpubConverter()
                    success, result_path = epub_converter.convert_to_epub(
                        md_content=md_content,
                        title=result['title'],
                        author=result.get('author', '未知作者'),
                        source_url=source_url,
                        output_path=filepath,
                        images_dir=self.batch_save_dir / 'images'
                    )
                    if not success:
                        raise Exception(result_path)
                else:
                    filepath = self.batch_save_dir / (base_filename + '.md')
                    content = result['content']
                    content = fetcher.replace_image_urls(content, url_mapping)
                    filepath.write_text(content, encoding='utf-8')

                self.root.after(0, lambda f=filepath: self.batch_log(f"  ✓ 已保存: {f.name}"))
                self.batch_success += 1

            except Exception as e:
                self.root.after(0, lambda err=str(e): self.batch_log(f"  ✗ 错误: {err[:50]}"))
                self.batch_failed += 1

            # 短暂延迟，避免请求过快
            time.sleep(0.5)

        # 完成
        self.root.after(0, self._batch_download_complete)

    def _update_batch_progress(self, current, total):
        """更新批量下载进度"""
        self.batch_progress['value'] = current
        self.batch_progress_label.config(text=f"{current}/{total}")

    def _batch_download_complete(self):
        """批量下载完成"""
        self.batch_running = False
        self.batch_start_btn.config(state=tk.NORMAL)
        self.batch_stop_btn.config(state=tk.DISABLED)

        self.batch_log("-" * 50)
        self.batch_log(f"下载完成!")
        self.batch_log(f"  成功: {self.batch_success} 篇")
        self.batch_log(f"  失败: {self.batch_failed} 篇")
        self.batch_log(f"  图片: {self.batch_total_images} 张")

        self.status_var.set(f"批量下载完成: 成功 {self.batch_success} 篇, 失败 {self.batch_failed} 篇")

        messagebox.showinfo("完成",
            f"批量下载完成!\n\n"
            f"成功: {self.batch_success} 篇\n"
            f"失败: {self.batch_failed} 篇\n"
            f"图片: {self.batch_total_images} 张\n\n"
            f"保存目录: {self.batch_save_dir}")


def main():
    root = tk.Tk()

    try:
        root.iconbitmap('icon.ico')
    except:
        pass

    root.update_idletasks()
    width = 900
    height = 800
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    app = ArticleFetcherGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
