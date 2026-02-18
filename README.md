# 网页文章保存工具 / Web Article Saver

[中文](#中文) | [English](#english)

---

<a name="中文"></a>
## 中文

一个用于保存网页文章到本地 Markdown、HTML 或 EPUB 文件的图形界面工具，支持自动下载图片和批量下载。

### 支持的网站

- **微信公众号文章** (mp.weixin.qq.com)
- **Notion 博客** (notion.com, notion.site)
- **知乎专栏** (zhuanlan.zhihu.com)
- **Medium** (medium.com)
- **通用网页文章** (其他大多数网站)

### 功能特点

- **图形界面**：简单易用的操作界面
- **单篇/批量下载**：支持单篇文章下载和批量下载
- **三种输出格式**：
  - HTML（保留原始样式、颜色、居中等格式）
  - Markdown（纯文本格式，便于编辑）
  - EPUB（电子书格式，可在Kindle、Apple Books等阅读器中打开）
- **自动下载图片**：将所有图片下载到本地 `images/` 子目录，EPUB格式自动嵌入图片
- **自动命名**：文件自动以文章标题命名
- **中文支持**：完美支持中文文件名

### 安装

#### 系统要求

- Python 3.6 或更高版本
- 无需安装额外包（仅使用 Python 标准库）

#### 安装步骤

1. 克隆或下载本仓库
2. 无需 pip install，工具仅使用 Python 标准库

### 使用方法

#### 方法 1：双击运行

```
run.bat
```

双击 `run.bat` 即可启动图形界面。

#### 方法 2：命令行运行

```bash
python article_fetcher_gui.py
```

#### 方法 3：命令行直接获取

```bash
# 微信文章
python fetch_article.py "https://mp.weixin.qq.com/s/xxxxx"

# Notion 博客
python fetch_article.py "https://www.notion.com/blog/xxxxx"

# 通用网页
python fetch_article.py "https://example.com/article"
```

### GUI 操作说明

#### 单篇下载

1. 选择 **"单篇下载"** 选项卡
2. **粘贴链接**：在输入框中输入或粘贴文章链接（支持微信、Notion、通用网页）
3. **选择格式**：选择输出格式
   - **HTML (保留样式)**：保留原始格式、颜色和布局
   - **Markdown**：纯文本格式，适合编辑
   - **EPUB (电子书)**：电子书格式，可在Kindle、Apple Books等阅读器中打开，自动嵌入图片
4. **下载图片**：勾选"下载图片到本地"以下载图片到本地（EPUB格式会自动下载）
5. **点击"获取文章"**：获取并解析文章
6. **预览**：在预览区域查看内容
7. **点击"保存文件"**：保存到本地文件

#### 批量下载

1. 选择 **"批量下载"** 选项卡
2. **输入链接列表**：在文本框中粘贴多个文章链接，每行一个
3. **选择格式**：选择 Markdown、HTML 或 EPUB
4. **下载图片**：勾选"下载图片到本地"（EPUB格式会自动下载）
5. **点击"开始批量下载"**：开始下载所有文章
6. **查看日志**：在日志区域查看下载进度和结果

批量下载示例输入：
```
https://mp.weixin.qq.com/s/xxxxx1
https://www.notion.com/blog/xxxxx2
https://zhuanlan.zhihu.com/p/xxxxx3
```

### 文件结构

```
article_fetcher/
├── run.bat                  # 启动脚本（双击运行）
├── article_fetcher_gui.py   # 主程序（GUI版）
├── fetch_article.py         # 命令行版
├── fetch.bat                # 命令行启动器
├── README.md                # 说明文档
├── output/                  # 默认输出目录
│   ├── 文章标题1.md         # 保存的文章
│   ├── 文章标题2.md
│   ├── 文章标题3.epub       # EPUB电子书格式
│   └── images/              # 下载的图片
│       ├── 20260216_143052_123456_1.jpg
│       └── ...
```

### 输出格式

#### HTML 格式

生成独立的 HTML 文件，包含：
- 内嵌 CSS 样式
- 原始文章颜色和格式
- 文字居中等布局
- 响应式设计
- 表格样式

#### Markdown 格式

生成干净的 Markdown 文件，包含：
- 元数据头部（作者、链接、日期）
- 转换后的表格
- 本地图片引用
- 正确的标题层级

示例：

```markdown
# 文章标题

> **作者**: 作者名
> **原文链接**: https://example.com/article
> **保存日期**: 2026-02-16

---

![图片](images/20260216_143052_123456_1.jpg)

文章内容...
```

#### EPUB 格式

生成标准 EPUB 3.0 电子书文件，包含：
- 所有图片自动嵌入
- 元数据（标题、作者、来源）
- 目录导航
- 可在 Kindle、Apple Books、Calibre 等阅读器中打开
- 适合离线阅读和长期保存

### 图片处理

- 图片下载到 `output/images/` 子目录
- 文件名格式：`YYYYMMDD_HHMMSS_微秒_序号.扩展名`
- 文章中的原始 URL 替换为本地路径
- 支持格式：JPG、PNG、GIF、WebP、BMP、SVG
- 如果图片下载失败（如 CDN 保护），将保留原始 URL

### 常见问题

#### 图片无法下载

- 检查网络连接
- 部分网站的图片可能有 CDN 保护（如 Notion 的 contentful.net），将保留原始 URL
- 查看状态栏的下载计数

#### 文章无法获取

- 确保链接是有效的网页地址
- 链接应以 `http://` 或 `https://` 开头
- 部分文章需要登录，本工具仅支持公开文章
- 某些网站可能有反爬虫机制

#### 内容解析不完整

- 不同网站的结构不同，工具会尝试自动识别内容区域
- 对于解析不完整的情况，建议使用 HTML 格式保存

#### 编码问题

- 工具使用 UTF-8 编码
- 如出现乱码，请用 UTF-8 编码打开文件

---

<a name="english"></a>
## English

A GUI tool for saving web articles to local Markdown, HTML, or EPUB files, with automatic image downloading and batch download support.

### Supported Websites

- **WeChat Public Account** (mp.weixin.qq.com)
- **Notion Blog** (notion.com, notion.site)
- **Zhihu Column** (zhuanlan.zhihu.com)
- **Medium** (medium.com)
- **General Web Articles** (most other websites)

### Features

- **GUI Interface**: Easy-to-use graphical interface
- **Single/Batch Download**: Support for both single article and batch download
- **Three Output Formats**:
  - HTML (preserves original styles, colors, centering)
  - Markdown (clean text format)
  - EPUB (e-book format, openable in Kindle, Apple Books, etc.)
- **Automatic Image Download**: Downloads all images to local `images/` subfolder, automatically embedded in EPUB
- **Auto-naming**: Files are automatically named after the article title
- **Chinese Filename Support**: Handles Chinese characters in filenames

### Installation

#### Requirements

- Python 3.6 or higher
- No additional packages required (uses only standard library)

#### Setup

1. Clone or download this repository
2. No pip install needed - the tool uses only Python standard library

### Usage

#### Method 1: Double-click to Run

```
run.bat
```

Simply double-click `run.bat` to launch the GUI.

#### Method 2: Command Line

```bash
python article_fetcher_gui.py
```

#### Method 3: Command Line (Direct Fetch)

```bash
# WeChat article
python fetch_article.py "https://mp.weixin.qq.com/s/xxxxx"

# Notion blog
python fetch_article.py "https://www.notion.com/blog/xxxxx"

# General web page
python fetch_article.py "https://example.com/article"
```

### GUI Instructions

#### Single Download

1. Select **"单篇下载"** tab
2. **Paste URL**: Enter or paste the article URL (supports WeChat, Notion, general web)
3. **Select Format**: Choose output format
   - **HTML (保留样式)**: Preserves original formatting, colors, and layout
   - **Markdown**: Clean text format suitable for editing
   - **EPUB (电子书)**: E-book format, openable in Kindle, Apple Books, etc., with embedded images
4. **Image Download**: Check "下载图片到本地" to download images locally (EPUB format auto-downloads)
5. **Click "获取文章"**: Fetch and parse the article
6. **Preview**: Review the content in the preview area
7. **Click "保存文件"**: Save to local file

#### Batch Download

1. Select **"批量下载"** tab
2. **Enter URL List**: Paste multiple article URLs in the text box, one per line
3. **Select Format**: Choose Markdown, HTML, or EPUB
4. **Image Download**: Check "下载图片到本地" (EPUB format auto-downloads)
5. **Click "开始批量下载"**: Start downloading all articles
6. **View Log**: Check download progress and results in the log area

Example batch input:
```
https://mp.weixin.qq.com/s/xxxxx1
https://www.notion.com/blog/xxxxx2
https://zhuanlan.zhihu.com/p/xxxxx3
```

### File Structure

```
article_fetcher/
├── run.bat                  # Launch script (double-click to run)
├── article_fetcher_gui.py   # Main GUI application
├── fetch_article.py         # Command-line version
├── fetch.bat                # Command-line launcher
├── README.md                # This file
├── output/                  # Default output directory
│   ├── article_title.md     # Saved articles
│   └── images/              # Downloaded images
│       ├── 20260216_143052_123456_1.jpg
│       └── ...
```

### Output Format

#### HTML Format

Generates a standalone HTML file with:
- Embedded CSS styling
- Original article colors and formatting
- Centered text where applicable
- Responsive design
- Proper table styling

#### Markdown Format

Generates a clean Markdown file with:
- YAML-like header with metadata
- Converted tables
- Image references to local files
- Proper heading hierarchy

Example:

```markdown
# Article Title

> **作者**: Author Name
> **原文链接**: https://example.com/article
> **保存日期**: 2026-02-16

---

![图片](images/20260216_143052_123456_1.jpg)

Article content here...
```

#### EPUB Format

Generates standard EPUB 3.0 e-book files with:
- All images automatically embedded
- Metadata (title, author, source)
- Table of contents navigation
- Openable in Kindle, Apple Books, Calibre, and other e-book readers
- Suitable for offline reading and long-term archiving

### Image Handling

- Images are downloaded to `output/images/` subfolder
- Filename format: `YYYYMMDD_HHMMSS_microseconds_number.ext`
- Original URLs in the article are replaced with local paths
- Supported formats: JPG, PNG, GIF, WebP, BMP, SVG, AVIF
- If image download fails (e.g., CDN protection), original URLs are preserved

### Troubleshooting

#### Images not downloading

- Check your internet connection
- Notion images are now downloaded via Notion proxy (AVIF format)
- Check the status message for download count

#### Article not fetching

- Ensure the URL is a valid web address
- URL should start with `http://` or `https://`
- Some articles may require login; this tool only works with public articles
- Some websites may have anti-scraping measures

#### Incomplete content parsing

- Different websites have different structures; the tool tries to auto-detect content areas
- For incomplete parsing, consider using HTML format to preserve more content

#### Encoding issues

- The tool uses UTF-8 encoding
- If you see garbled characters, try opening files with UTF-8 encoding

### Technical Details

#### Dependencies

- Python Standard Library only:
  - `tkinter` - GUI
  - `urllib` - HTTP requests
  - `re` - Regular expressions
  - `pathlib` - File paths
  - `threading` - Background operations

#### URL Handling

- Handles `//` protocol-relative URLs
- Handles relative URLs starting with `/`
- Decodes HTML entities in URLs
- Supports both `data-src` and `src` attributes
- Extracts actual URLs from image proxy URLs (e.g., Notion's `/_next/image?url=...`)

---

## License

MIT License - Feel free to use and modify.

## Changelog

### v2.1.0
- **New Feature**: Added EPUB output format
- EPUB files can be opened in Kindle, Apple Books, Calibre, and other e-book readers
- All images are automatically embedded in EPUB files
- Fixed Notion image download issue (now using Notion proxy URLs)
- Fixed Windows path separator issue in image path counting
- Added AVIF image format support

### v2.0.0
- **Major Update**: Added support for general web articles (Notion, Medium, Zhihu, etc.)
- Added automatic source detection (WeChat, Notion, general web)
- Added Notion-specific content extraction
- Added general web content extraction with multiple fallback strategies
- Fixed image URL extraction for relative URLs and proxy URLs
- Updated UI to reflect multi-source support

### v1.3.0
- Added batch download feature with progress tracking
- Added tabbed interface (Single Download / Batch Download)
- Added download log viewer

### v1.2.0
- Added bilingual README (Chinese/English)
- Changed default output directory to `output/`

### v1.1.0
- Fixed image URL replacement for Markdown format
- Fixed HTML entity encoding mismatch (`&amp;` vs `&`)
- Moved action buttons above preview area for better visibility

### v1.0.0
- Initial release
- GUI interface
- HTML and Markdown output formats
- Image downloading
- Auto-naming based on article title
