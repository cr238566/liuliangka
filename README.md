# 流量卡优选 - 静态网站

一个专注于流量卡推广的 SEO 优化静态网站，以带图文章为主。

## 项目结构

```
liuliangka/
├── source/
│   ├── articles/         # Markdown 文章源文件
│   ├── images/           # 文章配图
│   └── config.json       # 站点配置
├── templates/            # Jinja2 模板
│   ├── base.html         # 基础模板
│   ├── index.html        # 首页
│   ├── article.html      # 文章页
│   ├── category.html     # 分类页
│   ├── tag.html          # 标签页
│   ├── search.html       # 搜索页
│   ├── about.html        # 关于我们
│   └── privacy.html      # 隐私政策
├── output/               # 生成的静态网站
├── generate.py           # 站点生成器
└── serve.py              # 开发服务器
```

## 快速开始

### 1. 编写文章

在 `source/articles/` 下创建 `.md` 文件，使用 frontmatter 格式：

```markdown
---
title: "文章标题"
slug: wen-zhang-biao-ti
date: 2026-07-05
category: tuijian        # 分类: tuijian/jiqiao/duibi/zixun/huodong
tags: 标签1,标签2
image: /source/images/xxx.jpg
excerpt: "文章摘要..."
priority: 3             # 优先级 0-5，越高越靠前
---

文章正文 Markdown 内容...
```

### 2. 生成站点

```bash
python generate.py
```

### 3. 预览站点

```bash
python serve.py
```

浏览器访问 http://localhost:8000

### 4. 部署

将 `output/` 目录下的所有文件上传到服务器或 CDN 即可。

## SEO 特性

- 语义化 HTML5 结构
- Open Graph 协议支持
- XML Sitemap 自动生成
- Canonical URL
- 响应式设计（移动端优先）
- 面包屑导航
- 标签和分类系统
- 相关文章推荐

## 配置

编辑 `source/config.json`：

- `site_name` - 站点名称
- `site_url` - 站点域名
- `site_description` - 站点描述
- `ga_id` - Google Analytics ID
- `beian` - 备案号
- `categories` - 分类定义
