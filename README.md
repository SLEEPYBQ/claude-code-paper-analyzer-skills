# Claude Code Paper Analyzer Skills

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills for downloading and analyzing academic papers, generating comprehensive Obsidian notes with extracted figures — all powered by Claude.

> Built on top of [evil-read-arxiv](https://github.com/juliye2025/evil-read-arxiv), extending its paper analysis workflow from arXiv to ACM Digital Library and local PDFs. Uses the same Obsidian vault structure and note format for seamless integration.

## What Are These Skills?

These are **slash command skills** for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Anthropic's CLI tool). Once installed, you can type `/acm-paper-analyze` or `/pdf-paper-analyze` in Claude Code to trigger paper analysis workflows.

| Skill | Slash Command | Purpose |
|-------|---------------|---------|
| **acm-paper-analyze** | `/acm-paper-analyze` | Download papers from ACM Digital Library (via DOI or title) and generate analysis notes |
| **pdf-paper-analyze** | `/pdf-paper-analyze` | Analyze local PDF files (single file or entire directory) and generate analysis notes |

Both skills produce structured Chinese-language Obsidian notes with:
- YAML frontmatter (tags, scoring, metadata)
- Abstract translation and key takeaways
- Research background and motivation
- Method overview with **embedded figures extracted from the paper**
- Experimental results with tables
- Comprehensive evaluation (5-dimension scoring rubric)

## Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/SLEEPYBQ/claude-code-paper-analyzer-skills.git
cd claude-code-paper-analyzer-skills

# 2. Copy skills to Claude Code
cp -r acm-paper-analyze ~/.claude/skills/
cp -r pdf-paper-analyze ~/.claude/skills/

# 3. Set your vault path (add to ~/.zshrc or ~/.bashrc)
echo 'export OBSIDIAN_VAULT_PATH="/path/to/your/obsidian-vault"' >> ~/.zshrc
source ~/.zshrc

# 4. Set up Python environment
conda create -n paper-analyze python=3.11 -y
conda activate paper-analyze
pip install "markitdown[pdf] @ git+https://github.com/microsoft/markitdown.git#subdirectory=packages/markitdown"
pip install PyMuPDF selenium

# 5. Use in Claude Code!
# /acm-paper-analyze 10.1145/3772318.3791819
# /pdf-paper-analyze /path/to/paper.pdf
```

## Installation (Step by Step)

### Step 1: Install Claude Code

If you don't have Claude Code yet, install it first:

```bash
npm install -g @anthropic-ai/claude-code
```

See the [official docs](https://docs.anthropic.com/en/docs/claude-code) for details.

### Step 2: Clone and Copy Skills

```bash
git clone https://github.com/SLEEPYBQ/claude-code-paper-analyzer-skills.git
cd claude-code-paper-analyzer-skills

# Copy skill directories to Claude Code's skills folder
cp -r acm-paper-analyze ~/.claude/skills/
cp -r pdf-paper-analyze ~/.claude/skills/
```

After copying, the skills will appear when you type `/` in Claude Code.

### Step 3: Configure Obsidian Vault Path

The skills need to know where your Obsidian vault is. Set the `OBSIDIAN_VAULT_PATH` environment variable:

**macOS/Linux** — add to your shell config (`~/.zshrc`, `~/.bashrc`, etc.):
```bash
export OBSIDIAN_VAULT_PATH="/Users/yourname/Documents/my-obsidian-vault"
```

**Windows PowerShell**:
```powershell
[System.Environment]::SetEnvironmentVariable("OBSIDIAN_VAULT_PATH", "C:\Users\YourName\Documents\my-obsidian-vault", "User")
```

Then create the required directory structure in your vault:
```bash
mkdir -p "$OBSIDIAN_VAULT_PATH/20_Research/Papers"
```

Your vault should look like:
```
Your Vault/
└── 20_Research/
    └── Papers/           # Paper notes will be organized here by domain
        ├── HCI_AI/       # (auto-created by the skill)
        ├── 大模型/        # (auto-created by the skill)
        └── ...
```

### Step 4: Set Up Python Environment

The skills use [markitdown](https://github.com/microsoft/markitdown) (by Microsoft) for PDF text extraction and [PyMuPDF](https://pymupdf.readthedocs.io/) for figure extraction. **Python >= 3.10 is required** (markitdown does not support Python 3.9).

**Option A: Using Conda (recommended)**
```bash
conda create -n paper-analyze python=3.11 -y
conda activate paper-analyze
pip install "markitdown[pdf] @ git+https://github.com/microsoft/markitdown.git#subdirectory=packages/markitdown"
pip install PyMuPDF
pip install selenium    # only needed for acm-paper-analyze
```

**Option B: Using venv**
```bash
python3.11 -m venv ~/.venvs/paper-analyze
source ~/.venvs/paper-analyze/bin/activate
pip install "markitdown[pdf] @ git+https://github.com/microsoft/markitdown.git#subdirectory=packages/markitdown"
pip install PyMuPDF
pip install selenium    # only needed for acm-paper-analyze
```

**Verify installation:**
```bash
python -c "from markitdown import MarkItDown; import fitz; print('All good!')"
```

### Step 5: Install Chrome (only for `acm-paper-analyze`)

The `acm-paper-analyze` skill uses Selenium to bypass ACM's Cloudflare protection. You need Google Chrome installed:

- **macOS**: `brew install --cask google-chrome` or [download](https://www.google.com/chrome/)
- **Windows**: [Download Chrome](https://www.google.com/chrome/)
- **Linux**: `sudo apt install google-chrome-stable` or [download](https://www.google.com/chrome/)

ChromeDriver is managed automatically by Selenium 4+ — no separate installation needed.

## Usage

### `/acm-paper-analyze` — Download and analyze ACM papers

**By DOI:**
```
/acm-paper-analyze 10.1145/3772318.3791819
```

**By DOI URL:**
```
/acm-paper-analyze https://doi.org/10.1145/3772318.3791819
```

**By paper title** (uses [Semantic Scholar API](https://api.semanticscholar.org/) to resolve DOI):
```
/acm-paper-analyze "Towards human-ai deliberation: Design and evaluation of llm-empowered deliberative ai"
```

> **Note**: When ACM's Cloudflare blocks the download, the skill automatically falls back to downloading from ArXiv (if the paper has an ArXiv version). If both fail, it will suggest you download the PDF manually and use `/pdf-paper-analyze` instead.

### `/pdf-paper-analyze` — Analyze local PDFs

**Single PDF:**
```
/pdf-paper-analyze /path/to/paper.pdf
```

**All PDFs in a directory** (analyzed in parallel):
```
/pdf-paper-analyze /path/to/papers/
```

**With manual domain override:**
```
/pdf-paper-analyze /path/to/paper.pdf --domain CHI2026
```

## Output

Each paper gets its own directory with an analysis note and extracted figures:

```
$OBSIDIAN_VAULT_PATH/20_Research/Papers/
└── HCI_AI/                              # Auto-inferred domain
    └── Paper_Title/
        ├── Paper Title.md               # Full analysis note (Chinese)
        └── images/
            ├── page3.png                # Pages with Figure 1, Table 1, etc.
            ├── page7.png
            └── ...
```

### What's in the Note?

```markdown
---
date: "2026-04-24"
paper_id: "10.1145/..."
title: "Paper Title"
authors: "Author1, Author2"
domain: "HCI_AI"
tags: [论文笔记, CHI-2026, Human-AI-Collaboration]
quality_score: "8.5/10"
status: analyzed
---

# Paper Title

## 核心信息          ← metadata table
## 摘要翻译          ← Chinese abstract + key takeaways
## 研究背景与动机     ← background & motivation
## 方法概述          ← methods with embedded figures
## 实验结果          ← results with data tables
## 深度分析          ← strengths, limitations, implications
## 综合评价          ← 5-dimension scoring rubric
```

### Domain Auto-Inference

If no domain is specified, the skill infers it from paper content keywords:

| Keywords in Paper | Inferred Domain |
|-------------------|----------------|
| agent, multi-agent, orchestration | 智能体 |
| vision, visual, image, multimodal | 多模态技术 |
| reinforcement learning, RL, reward | 强化学习_LLM_Agent |
| language model, LLM, transformer | 大模型 |
| HCI, user study, interface, CHI | HCI_AI |
| diffusion, generation, synthesis | Diffusion |
| memory, personalization | AgentMemory |

Existing subdirectories in your vault are preferred when matching.

## How It Works

```
Input (DOI / title / PDF path)
    │
    ├─ [acm-paper-analyze only]
    │   ├── Title → Semantic Scholar API → DOI
    │   └── DOI → Selenium + Chrome → Download PDF
    │   └── (fallback) → ArXiv PDF if ACM blocked
    │
    ▼
markitdown (Microsoft): PDF → Markdown text
    │
    ▼
PyMuPDF: Render pages containing figures/tables as high-res PNG
    │
    ▼
Claude Code: Deep analysis of full paper content
    │
    ▼
Obsidian note with embedded figures + scoring
```

## Compatibility

- **[evil-read-arxiv](https://github.com/juliye2025/evil-read-arxiv)**: Same vault structure (`20_Research/Papers/`) and note format. The `paper-analyze` skill from evil-read-arxiv handles arXiv papers via TeX source; these skills extend coverage to ACM Digital Library and arbitrary local PDFs.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `OBSIDIAN_VAULT_PATH not set` | Add `export OBSIDIAN_VAULT_PATH="..."` to your shell config and restart terminal |
| `markitdown not found` | Make sure you're using Python >= 3.10 and installed from GitHub (not PyPI) |
| `ACM download blocked by Cloudflare` | The skill auto-falls back to ArXiv. If no ArXiv version, download PDF manually and use `/pdf-paper-analyze` |
| `Chrome/Selenium errors` | Install Chrome browser and ensure `selenium` is installed: `pip install selenium` |
| `No figures extracted` | Some papers use vector graphics; the skill detects pages with >50 drawing operations as figure pages |
| Skills don't appear in Claude Code | Verify files exist at `~/.claude/skills/acm-paper-analyze/skill.md` and `~/.claude/skills/pdf-paper-analyze/skill.md` |

## License

MIT
