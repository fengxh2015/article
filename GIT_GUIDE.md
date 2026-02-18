# Git 版本控制使用指南

## 目录
1. [Git 基础概念](#1-git-基础概念)
2. [初始化配置](#2-初始化配置)
3. [基本工作流程](#3-基本工作流程)
4. [分支管理](#4-分支管理)
5. [远程仓库 (GitHub)](#5-远程仓库-github)
6. [常用命令速查](#6-常用命令速查)
7. [本项目管理指南](#7-本项目管理指南)

---

## 1. Git 基础概念

### 什么是 Git？
Git 是一个分布式版本控制系统，可以：
- 记录文件的每一次修改历史
- 支持多人协作开发
- 创建分支进行功能开发
- 随时回退到任意历史版本

### 三个重要区域
```
工作目录 (Working Directory)  →  暂存区 (Staging Area)  →  本地仓库 (Repository)
     [编辑文件]                    [git add]                  [git commit]
                                    选择要提交的更改             保存快照
```

### 文件状态
- **Untracked**: 未跟踪的新文件
- **Modified**: 已修改但未暂存
- **Staged**: 已暂存，准备提交
- **Committed**: 已提交到仓库

---

## 2. 初始化配置

### 首次使用必须配置
```bash
# 配置用户名和邮箱（必须，用于标识提交者）
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"

# 查看当前配置
git config --list

# 配置默认分支名为 main（可选）
git config --global init.defaultBranch main
```

### 生成 SSH 密钥（用于 GitHub）
```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "你的邮箱@example.com"

# 查看公钥（复制到 GitHub → Settings → SSH Keys）
cat ~/.ssh/id_ed25519.pub
```

---

## 3. 基本工作流程

### 3.1 初始化仓库
```bash
# 在项目目录中初始化
git init

# 或者克隆现有仓库
git clone https://github.com/用户名/仓库名.git
```

### 3.2 查看状态
```bash
# 查看当前状态
git status

# 简洁模式
git status -s

# 查看提交历史
git log
git log --oneline          # 简洁模式
git log --oneline --graph  # 图形化显示
```

### 3.3 添加文件到暂存区
```bash
# 添加单个文件
git add article_fetcher_gui.py

# 添加多个文件
git add file1.py file2.py

# 添加所有更改
git add .

# 添加所有 .py 文件
git add *.py

# 交互式添加（可以选择部分更改）
git add -p
```

### 3.4 提交更改
```bash
# 提交暂存区的内容
git commit -m "添加 EPUB 转换功能"

# 提交并添加所有已跟踪文件的更改
git commit -am "修复图片格式问题"

# 修改上一次提交（未推送到远程时）
git commit --amend -m "新的提交信息"
```

### 3.5 查看差异
```bash
# 查看工作目录与暂存区的差异
git diff

# 查看暂存区与最新提交的差异
git diff --staged
git diff --cached

# 查看两个提交之间的差异
git diff commit1 commit2
```

### 3.6 撤销操作
```bash
# 撤销工作目录的修改（危险！会丢失更改）
git checkout -- filename
# 或新语法
git restore filename

# 取消暂存（保留工作目录的修改）
git reset HEAD filename
# 或新语法
git restore --staged filename

# 撤销最近的提交（保留更改）
git reset --soft HEAD~1

# 撤销最近的提交（丢弃更改，危险！）
git reset --hard HEAD~1
```

---

## 4. 分支管理

### 4.1 创建和切换分支
```bash
# 查看所有分支
git branch

# 创建新分支
git branch feature-epub

# 切换到分支
git checkout feature-epub
# 或新语法
git switch feature-epub

# 创建并切换（推荐）
git checkout -b feature-epub
# 或新语法
git switch -c feature-epub
```

### 4.2 合并分支
```bash
# 先切换到目标分支（如 main）
git checkout main

# 合并 feature 分支
git merge feature-epub

# 删除已合并的分支
git branch -d feature-epub
```

### 4.3 解决冲突
当合并出现冲突时：
```bash
# 1. 查看冲突文件
git status

# 2. 手动编辑冲突文件，解决冲突标记：
# <<<<<<< HEAD
# 当前分支的内容
# =======
# 要合并分支的内容
# >>>>>>> feature-epub

# 3. 解决后添加并提交
git add .
git commit -m "解决合并冲突"
```

---

## 5. 远程仓库 (GitHub)

### 5.1 连接远程仓库
```bash
# 添加远程仓库
git remote add origin https://github.com/用户名/仓库名.git

# 使用 SSH（推荐）
git remote add origin git@github.com:用户名/仓库名.git

# 查看远程仓库
git remote -v

# 修改远程仓库地址
git remote set-url origin 新地址
```

### 5.2 推送和拉取
```bash
# 首次推送（设置上游分支）
git push -u origin main

# 后续推送
git push

# 拉取最新更改
git pull

# 拉取并合并（等同于 fetch + merge）
git pull origin main

# 仅获取（不合并）
git fetch origin
```

### 5.3 GitHub 工作流程
```bash
# 1. Fork 项目（在 GitHub 网页上操作）

# 2. 克隆你的 Fork
git clone git@github.com:你的用户名/仓库名.git

# 3. 添加上游仓库
git remote add upstream git@github.com:原作者/仓库名.git

# 4. 同步上游更新
git fetch upstream
git checkout main
git merge upstream/main

# 5. 创建功能分支开发
git checkout -b feature-new

# 6. 推送到你的 Fork
git push origin feature-new

# 7. 在 GitHub 上创建 Pull Request
```

---

## 6. 常用命令速查

| 操作 | 命令 |
|------|------|
| 初始化仓库 | `git init` |
| 克隆仓库 | `git clone <url>` |
| 查看状态 | `git status` |
| 添加文件 | `git add <file>` |
| 添加所有 | `git add .` |
| 提交 | `git commit -m "message"` |
| 查看历史 | `git log --oneline` |
| 查看差异 | `git diff` |
| 创建分支 | `git checkout -b <branch>` |
| 切换分支 | `git checkout <branch>` |
| 合并分支 | `git merge <branch>` |
| 推送 | `git push` |
| 拉取 | `git pull` |
| 查看远程 | `git remote -v` |
| 撤销修改 | `git restore <file>` |
| 查看配置 | `git config --list` |

---

## 7. 本项目管理指南

### 项目结构
```
20260216_article_md/
├── article_fetcher_gui.py  # 主程序
├── fetch_article.py        # 文章获取模块
├── run.bat                 # 启动脚本
├── README.md               # 项目说明
├── .gitignore              # Git忽略配置
├── GIT_GUIDE.md            # 本指南
└── output/                 # 输出目录（已忽略）
```

### 推荐的提交规范
```bash
# 功能添加
git commit -m "feat: 添加 EPUB 转换功能"

# 修复 bug
git commit -m "fix: 修复图片下载失败的问题"

# 文档更新
git commit -m "docs: 更新使用说明"

# 重构代码
git commit -m "refactor: 重构 EpubConverter 类"

# 样式调整
git commit -m "style: 格式化代码"

# 性能优化
git commit -m "perf: 优化图片转换速度"
```

### 推荐的工作流程
```bash
# 1. 开始新功能前，确保主分支是最新的
git checkout main
git pull origin main

# 2. 创建功能分支
git checkout -b feature-新功能名

# 3. 开发过程中定期提交
git add .
git commit -m "feat: 完成部分功能"

# 4. 功能完成后，合并回主分支
git checkout main
git merge feature-新功能名

# 5. 推送到远程
git push origin main

# 6. 删除功能分支
git branch -d feature-新功能名
```

### .gitignore 说明
本项目的 `.gitignore` 配置了以下忽略规则：
- `__pycache__/` - Python 缓存目录
- `output/` - 用户生成的输出文件
- `*.epub`, `*.html` - 生成的文件（保留 README.md）
- `.idea/`, `.vscode/` - IDE 配置
- 测试文件和临时文件

---

## 快速开始

### 第一次提交本项目
```bash
# 1. 配置用户信息（如果还没配置）
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"

# 2. 添加所有文件
git add .

# 3. 查看将要提交的文件
git status

# 4. 提交
git commit -m "初始化项目：网页文章保存工具"

# 5. 在 GitHub 创建仓库后，连接并推送
git remote add origin git@github.com:你的用户名/article-saver.git
git push -u origin main
```

### 日常更新
```bash
# 1. 查看修改
git status
git diff

# 2. 添加修改的文件
git add article_fetcher_gui.py

# 3. 提交
git commit -m "fix: 修复 EPUB 转换问题"

# 4. 推送
git push
```

---

## 常见问题

### Q: 如何撤销最后一次提交？
```bash
git reset --soft HEAD~1  # 保留更改
git reset --hard HEAD~1  # 丢弃更改（危险）
```

### Q: 如何查看某次提交的详细信息？
```bash
git show commit_hash
```

### Q: 如何恢复已删除的文件？
```bash
git checkout HEAD^ -- path/to/file
```

### Q: 如何暂存当前工作？
```bash
git stash              # 暂存
git stash list         # 查看暂存列表
git stash pop          # 恢复最近一次暂存
git stash apply stash@{0}  # 恢复指定暂存
```

### Q: 推送被拒绝怎么办？
```bash
# 先拉取远程更改
git pull --rebase origin main
# 然后再推送
git push origin main
```

---

## 学习资源

- [Git 官方文档](https://git-scm.com/doc)
- [Pro Git 书籍（免费）](https://git-scm.com/book/zh/v2)
- [GitHub 文档](https://docs.github.com)
- [Learn Git Branching（交互式学习）](https://learngitbranching.js.org)

