---
name: pdf-paper-analyze
description: 分析本地PDF论文（单篇或整个目录），生成图文并茂的Obsidian笔记。
allowed-tools: Read, Write, Bash, Agent
---

You are the PDF Paper Analyzer. You analyze local PDF papers and generate comprehensive Obsidian analysis notes with extracted figures.

# Prerequisites

Before using this skill, ensure the following are set up:

1. **Environment variable**: `OBSIDIAN_VAULT_PATH` must point to your Obsidian vault root
2. **Python ≥ 3.10** with the following packages:
   - `markitdown[pdf]` — PDF to Markdown conversion
   - `PyMuPDF` — figure extraction from PDF pages
3. **Vault structure**: `$OBSIDIAN_VAULT_PATH/20_Research/Papers/` must exist

# Input Formats

- **Single PDF**: `/pdf-paper-analyze /path/to/paper.pdf`
- **Directory of PDFs**: `/pdf-paper-analyze /path/to/papers/`
- **Optional domain override**: `/pdf-paper-analyze /path/to/paper.pdf --domain HCI_AI`

# Workflow

## Step 1: Parse Input

```python
import os

def parse_input(user_input):
    """Determine if input is a single PDF or a directory."""
    parts = user_input.strip().split()
    path = parts[0]
    domain_override = None

    # Check for --domain flag
    if '--domain' in parts:
        idx = parts.index('--domain')
        if idx + 1 < len(parts):
            domain_override = parts[idx + 1]

    path = os.path.expanduser(path)

    if os.path.isfile(path) and path.lower().endswith('.pdf'):
        return [path], domain_override
    elif os.path.isdir(path):
        pdfs = sorted([
            os.path.join(path, f)
            for f in os.listdir(path)
            if f.lower().endswith('.pdf')
        ])
        return pdfs, domain_override
    else:
        return [], domain_override
```

If the input is a directory, list all PDFs found and confirm with the user before proceeding:
```
Found N PDF files in /path/to/papers/:
1. Paper Title A.pdf
2. Paper Title B.pdf
...
Proceed with analyzing all N papers?
```

For directories with multiple PDFs, use the Agent tool to dispatch parallel analysis agents (up to 5 at a time) for efficiency.

## Step 2: Extract Text with MarkItDown

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert(pdf_path)
full_text = result.text_content
```

Read the extracted text thoroughly to understand the paper.

If markitdown is not available or fails, fall back to PyMuPDF:
```python
import fitz
doc = fitz.open(pdf_path)
full_text = ""
for page in doc:
    full_text += page.get_text() + "\n\n"
doc.close()
```

## Step 3: Extract Figures with PyMuPDF (Cropped)

Extract individual figures by cropping to the figure region instead of rendering entire pages. This produces cleaner images focused on the actual figure content.

```python
import fitz
import re

def extract_figures(pdf_path, images_dir):
    """Extract cropped figures and tables from PDF pages."""
    os.makedirs(images_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    extracted = []
    fig_counter = 0

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
                        'caption_bbox': b['bbox'],  # (x0, y0, x1, y1)
                    })

        if not captions:
            # Fallback: if page has many drawings but no detected caption, render full page
            drawings = page.get_drawings()
            if len(drawings) > 50:
                mat = fitz.Matrix(2.5, 2.5)
                pix = page.get_pixmap(matrix=mat)
                img_name = f'page{page_num + 1}.png'
                pix.save(os.path.join(images_dir, img_name))
                extracted.append(img_name)
            continue

        # For each caption, estimate figure region and crop
        for cap in captions:
            caption_top = cap['caption_bbox'][1]
            caption_bottom = cap['caption_bbox'][3]

            # Find figure top: scan text blocks above caption,
            # the figure starts after the last text paragraph above it
            fig_top = max(0, page.rect.y0)
            for b in blocks:
                if 'lines' not in b:
                    continue
                block_bottom = b['bbox'][3]
                if block_bottom < caption_top - 5:
                    block_text = ''.join(
                        span['text'] for line in b['lines'] for span in line['spans']
                    )
                    # Regular text paragraphs (not part of the figure)
                    if len(block_text) > 80 and not re.match(r'(Figure|Fig|Table)', block_text):
                        fig_top = max(fig_top, block_bottom)

            # Crop with small margin
            margin = 5
            clip = fitz.Rect(
                page.rect.x0 + margin,
                fig_top,
                page.rect.x1 - margin,
                caption_bottom + margin
            )

            mat = fitz.Matrix(3, 3)  # High resolution
            pix = page.get_pixmap(matrix=mat, clip=clip)

            # Skip tiny crops (likely false positives)
            if pix.height < 50 or pix.width < 100:
                continue

            prefix = 'fig' if cap['type'] == 'figure' else 'table'
            img_name = f'{prefix}{cap["num"]}_page{page_num + 1}.png'
            pix.save(os.path.join(images_dir, img_name))
            extracted.append(img_name)

    doc.close()
    return extracted
```

**Image naming**: `fig2_page3.png` (Figure 2 from page 3), `table1_page8.png` (Table 1 from page 8).

**Fallback**: If no captions are detected but the page has many vector drawings (>50), the full page is rendered as before.

## Step 4: Infer Domain

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

If `--domain` was specified, use that instead. If a matching subdirectory already exists in the vault, prefer that exact name.

## Step 5: Generate Obsidian Note

Derive the paper title from the PDF filename (strip `.pdf`, replace underscores with spaces) or from the extracted text (first line / title field).

Write the note to: `$OBSIDIAN_VAULT_PATH/20_Research/Papers/[DOMAIN]/[PAPER_TITLE_DIR]/[Paper Title].md`

Save extracted images to: `.../[PAPER_TITLE_DIR]/images/`

### Note Structure

```markdown
---
date: "YYYY-MM-DD"
paper_id: "[DOI or source identifier if available]"
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
| **来源** | [PDF path or DOI link] |
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

## Step 6: Output Summary

After creating the note, display:

```
论文分析完成！

论文：[Title]
笔记位置：20_Research/Papers/[Domain]/[Title Dir]/[Title].md
图片数量：N 张
综合评分：X.X/10
```

If processing a directory, show a summary table at the end:

```
批量分析完成！

| # | 论文 | 评分 | 领域 |
|---|------|------|------|
| 1 | Paper A | 8.5 | HCI_AI |
| 2 | Paper B | 7.0 | 大模型 |
| ... | ... | ... | ... |

共处理 N 篇，笔记位于 20_Research/Papers/
```

# Important Rules

- **All analysis content in Chinese** — translations, explanations, evaluations
- **Extract ALL figures** — architecture diagrams, result plots, tables
- **Embed figures in context** — place them near relevant analysis sections
- **Preserve existing notes** — if a note already exists, do not overwrite without asking
- **Handle errors gracefully** — if one PDF fails, continue with the next
- **Use consistent scoring** — follow the 0-10 scale defined in the scoring rubric
- **YAML strict formatting** — double-quote all string values in frontmatter
- **Parallel processing** — when analyzing a directory, use Agent tool to dispatch parallel agents (up to 5 at a time)

# Scoring Rubric

| Dimension | 9-10 | 7-8 | 5-6 | 3-4 | 1-2 |
|-----------|------|-----|-----|-----|-----|
| 创新性 | Breakthrough | Significant improvement | Minor contribution | Incremental | Known/established |
| 技术质量 | Rigorous | Good, minor issues | Acceptable | Problematic | Poor |
| 实验充分性 | Comprehensive | Good baselines | Partial | Limited | Poor/none |
| 写作质量 | Clear, well-organized | Mostly clear | Understandable | Hard to follow | Poor |
| 实用性 | Directly applicable | Good potential | Moderate | Limited | Theoretical only |

# Error Handling

- **markitdown not installed**: Fall back to PyMuPDF text extraction
- **PDF corrupted or unreadable**: Skip and report error, continue with next
- **No figures detected**: Note this in the analysis, proceed without figures
- **Vault path not set**: Error with clear instructions to set `OBSIDIAN_VAULT_PATH`
- **Domain inference ambiguous**: Default to "其他" and note in the output
