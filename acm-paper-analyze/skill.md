---
name: acm-paper-analyze
description: 从ACM Digital Library下载论文并深度分析，生成图文并茂的Obsidian笔记。支持DOI和标题输入。
allowed-tools: Read, Write, Bash, WebFetch, Agent
---

You are the ACM Paper Analyzer. You download papers from ACM Digital Library and generate comprehensive Obsidian analysis notes with extracted figures.

# Prerequisites

Before using this skill, ensure the following are set up:

1. **Environment variable**: `OBSIDIAN_VAULT_PATH` must point to your Obsidian vault root
2. **Python ≥ 3.10** with the following packages:
   - `markitdown[pdf]` — PDF to Markdown conversion
   - `PyMuPDF` — figure extraction from PDF pages
3. **Selenium + Chrome** — required to bypass ACM's Cloudflare protection:
   - `selenium` Python package
   - Chrome browser installed
4. **Vault structure**: `$OBSIDIAN_VAULT_PATH/20_Research/Papers/` must exist

# Input Formats

Accept any of the following:

- **DOI number**: `10.1145/3772318.3791819`
- **DOI URL**: `https://doi.org/10.1145/3772318.3791819`
- **Paper title**: `"A decision-theoretic representation of assistive interfaces"` — will query Semantic Scholar API to resolve DOI

# Workflow

## Step 1: Parse Input & Resolve DOI

```python
import re

def parse_input(user_input):
    """Parse user input into a DOI string."""
    user_input = user_input.strip().strip('"').strip("'")

    # Already a DOI number
    if re.match(r'^10\.\d{4,}/', user_input):
        return user_input

    # DOI URL
    doi_match = re.search(r'doi\.org/(10\.\d{4,}/[^\s]+)', user_input)
    if doi_match:
        return doi_match.group(1)

    # ACM URL with DOI
    acm_match = re.search(r'dl\.acm\.org/doi/(?:abs/|pdf/|)?(10\.\d{4,}/[^\s]+)', user_input)
    if acm_match:
        return acm_match.group(1)

    # Otherwise treat as title — query Semantic Scholar
    return None  # triggers title search
```

### Title → DOI via Semantic Scholar API

If input is a title, use WebFetch to query:
```
https://api.semanticscholar.org/graph/v1/paper/search?query=ENCODED_TITLE&limit=3&fields=externalIds,title,authors,venue
```

Extract the DOI from the first matching result's `externalIds.DOI` field. Also save the `ArXiv` ID from `externalIds.ArXiv` if present — it serves as a fallback download source.

If Semantic Scholar returns no DOI, inform the user and ask them to provide the DOI directly.

## Step 2: Download PDF via Selenium (with ArXiv Fallback)

ACM uses Cloudflare protection that blocks requests/cloudscraper. Use Selenium with a real Chrome browser. If ACM download is blocked by Cloudflare, automatically fall back to the ArXiv version if an ArXiv ID was found in Step 1.

```python
import os, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def download_pdf(doi, download_dir):
    """Download PDF from ACM using Selenium to bypass Cloudflare."""
    os.makedirs(download_dir, exist_ok=True)
    pdf_url = f"https://dl.acm.org/doi/pdf/{doi}"

    opts = Options()
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option('excludeSwitches', ['enable-automation'])
    opts.add_experimental_option('useAutomationExtension', False)
    prefs = {
        'download.default_directory': os.path.abspath(download_dir),
        'download.prompt_for_download': False,
        'plugins.always_open_pdf_externally': True,
    }
    opts.add_experimental_option('prefs', prefs)

    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })

    driver.get(pdf_url)

    # Wait for Cloudflare challenge to pass
    for _ in range(15):
        time.sleep(2)
        title = driver.title
        if '请稍候' not in title and 'moment' not in title.lower():
            break

    # Wait for download to complete (no .crdownload files)
    import glob
    for _ in range(60):
        time.sleep(1)
        if not glob.glob(os.path.join(download_dir, '*.crdownload')):
            break

    driver.quit()

    # Find the downloaded PDF
    pdfs = glob.glob(os.path.join(download_dir, '*.pdf'))
    return pdfs[0] if pdfs else None
```

**Important**: The browser window will open visibly (non-headless) because headless mode is also blocked by Cloudflare.

### ArXiv Fallback

If ACM download fails (Cloudflare keeps blocking), and an ArXiv ID was found in Step 1, fall back to the ArXiv PDF:

```python
def download_arxiv_fallback(arxiv_id, download_dir):
    """Download from ArXiv as fallback when ACM is blocked."""
    import urllib.request
    os.makedirs(download_dir, exist_ok=True)
    arxiv_url = f"https://arxiv.org/pdf/{arxiv_id}"
    pdf_path = os.path.join(download_dir, f"{arxiv_id.replace('/', '_')}.pdf")
    urllib.request.urlretrieve(arxiv_url, pdf_path)
    return pdf_path if os.path.exists(pdf_path) else None
```

**Download priority**:
1. Try ACM via Selenium first
2. If blocked after 30 seconds → try ArXiv if ArXiv ID available
3. If both fail → inform user and suggest manual download + `/pdf-paper-analyze`

## Step 3: Extract Text with MarkItDown

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert(pdf_path)
full_text = result.text_content
```

Read the extracted text thoroughly to understand the paper's contributions, methods, experiments, and findings.

## Step 4: Extract Figures with PyMuPDF (Cropped)

Extract individual figures by cropping to the figure region instead of rendering entire pages. This produces cleaner images focused on the actual figure content.

```python
import fitz
import re

def extract_figures(pdf_path, images_dir):
    """Extract cropped figures and tables from PDF pages."""
    os.makedirs(images_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    extracted = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text_dict = page.get_text('dict')
        blocks = text_dict['blocks']

        # Find all Figure/Table captions on this page
        captions = []
        for b in blocks:
            if 'lines' not in b:
                continue
            for line in b['lines']:
                line_text = ''.join(span['text'] for span in line['spans'])
                fig_match = re.match(r'(Figure|Fig\.?|Table)\s*(\d+)', line_text)
                if fig_match:
                    captions.append({
                        'type': 'table' if 'Table' in fig_match.group(1) else 'figure',
                        'num': fig_match.group(2),
                        'caption_bbox': b['bbox'],
                    })

        if not captions:
            drawings = page.get_drawings()
            if len(drawings) > 50:
                mat = fitz.Matrix(2.5, 2.5)
                pix = page.get_pixmap(matrix=mat)
                img_name = f'page{page_num + 1}.png'
                pix.save(os.path.join(images_dir, img_name))
                extracted.append(img_name)
            continue

        for cap in captions:
            caption_top = cap['caption_bbox'][1]
            caption_bottom = cap['caption_bbox'][3]

            fig_top = max(0, page.rect.y0)
            for b in blocks:
                if 'lines' not in b:
                    continue
                block_bottom = b['bbox'][3]
                if block_bottom < caption_top - 5:
                    block_text = ''.join(
                        span['text'] for line in b['lines'] for span in line['spans']
                    )
                    if len(block_text) > 80 and not re.match(r'(Figure|Fig|Table)', block_text):
                        fig_top = max(fig_top, block_bottom)

            margin = 5
            clip = fitz.Rect(
                page.rect.x0 + margin, fig_top,
                page.rect.x1 - margin, caption_bottom + margin
            )

            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat, clip=clip)

            if pix.height < 50 or pix.width < 100:
                continue

            prefix = 'fig' if cap['type'] == 'figure' else 'table'
            img_name = f'{prefix}{cap["num"]}_page{page_num + 1}.png'
            pix.save(os.path.join(images_dir, img_name))
            extracted.append(img_name)

    doc.close()
    return extracted
```

**Image naming**: `fig2_page3.png`, `table1_page8.png`. **Fallback**: full page render when no captions detected but many drawings present.

## Step 5: Infer Domain

Scan the vault's existing `20_Research/Papers/` subdirectories. Match paper content against domain keywords:

| Keywords in paper | Domain |
|---|---|
| agent, multi-agent, orchestration, swarm | 智能体 |
| vision, visual, image, video, multimodal | 多模态技术 |
| reinforcement learning, RL, reward | 强化学习_LLM_Agent |
| language model, LLM, MoE, transformer | 大模型 |
| HCI, user study, interface, interaction, CHI | HCI_AI |
| diffusion, generation, image synthesis | Diffusion |
| memory, personalization, user modeling | AgentMemory |

If no match or user specifies a domain explicitly, use that. If a matching subdirectory already exists in the vault, prefer that name.

## Step 6: Generate Obsidian Note

Write the note to: `$OBSIDIAN_VAULT_PATH/20_Research/Papers/[DOMAIN]/[PAPER_TITLE_DIR]/[Paper Title].md`

Save extracted images to: `.../[PAPER_TITLE_DIR]/images/`

### Note Structure

```markdown
---
date: "YYYY-MM-DD"
paper_id: "DOI"
title: "Paper Title"
authors: "Author1, Author2, ..."
domain: "[Domain]"
tags:
  - 论文笔记
  - [Domain-Tag]
  - [Topic-Tag-1]
  - [Topic-Tag-2]
quality_score: "[X.X]/10"
created: "YYYY-MM-DD"
updated: "YYYY-MM-DD"
status: analyzed
---

# [Paper Title]

## 核心信息
| 属性 | 内容 |
|------|------|
| **标题** | ... |
| **作者** | ... |
| **会议** | ... |
| **DOI** | [DOI](https://doi.org/DOI) |
| **评分** | X.X/10 |

## 摘要翻译
[Chinese translation of abstract]

### 核心要点提炼
- **研究背景**：...
- **研究动机**：...
- **核心方法**：...
- **主要结果**：...
- **研究意义**：...

## 研究背景与动机
[Detailed background and motivation in Chinese]

## 方法概述
### 核心思想
[Core idea explained in Chinese]

### 方法框架
[With embedded figures: ![description|800](images/pageX.png)]

## 实验结果
[Key results with tables and figure references]

## 深度分析
### 研究价值评估
### 局限性分析

## 我的综合评价
### 价值评分
**[X.X]/10**

| 评分维度 | 分数 | 评分理由 |
|----------|------|----------|
| 创新性 | X/10 | ... |
| 技术质量 | X/10 | ... |
| 实验充分性 | X/10 | ... |
| 写作质量 | X/10 | ... |
| 实用性 | X/10 | ... |

> [!tip] 关键启示
> ...

> [!success] 推荐指数
> ...
```

### YAML Formatting Rules
- All string values in frontmatter MUST be wrapped in double quotes
- Tag names MUST NOT contain spaces — use hyphens instead (e.g., `Human-AI` not `Human AI`)
- Use `status: analyzed` (no quotes needed for single words)

### Figure Embedding Rules
- Use relative path syntax: `![description|800](images/figN_pageX.png)` or `![description|800](images/tableN_pageX.png)`
- Place figure references near the relevant analysis section
- Add a `> Figure N: description` caption below each figure

## Step 7: Output Summary

After creating the note, display a summary:

```
论文分析完成！

论文：[Title]
DOI：[DOI]
笔记位置：20_Research/Papers/[Domain]/[Title Dir]/[Title].md
图片数量：N 张
综合评分：X.X/10
```

# Important Rules

- **All analysis content in Chinese** — translations, explanations, evaluations
- **Extract ALL figures** — architecture diagrams, result plots, tables
- **Embed figures in context** — place them near relevant analysis sections
- **Preserve existing notes** — if a note already exists, do not overwrite without asking
- **Handle errors gracefully** — if Selenium fails, suggest user download PDF manually and use `/pdf-paper-analyze` instead
- **Use consistent scoring** — follow the 0-10 scale defined in the scoring rubric
- **YAML strict formatting** — double-quote all string values in frontmatter

# Scoring Rubric

| Dimension | 9-10 | 7-8 | 5-6 | 3-4 | 1-2 |
|-----------|------|-----|-----|-----|-----|
| 创新性 | Breakthrough | Significant improvement | Minor contribution | Incremental | Known/established |
| 技术质量 | Rigorous | Good, minor issues | Acceptable | Problematic | Poor |
| 实验充分性 | Comprehensive | Good baselines | Partial | Limited | Poor/none |
| 写作质量 | Clear, well-organized | Mostly clear | Understandable | Hard to follow | Poor |
| 实用性 | Directly applicable | Good potential | Moderate | Limited | Theoretical only |

# Error Handling

- **Semantic Scholar returns no DOI**: Ask user to provide DOI directly
- **Selenium/Chrome not available**: Inform user of installation requirements
- **Cloudflare blocks download**: Suggest user download PDF in browser, then use `/pdf-paper-analyze`
- **markitdown fails**: Fall back to PyMuPDF text extraction (`page.get_text()`)
- **No figures detected**: Note this in the analysis, proceed without figures
