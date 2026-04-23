# ACM & PDF Paper Analyzer

Claude Code skills for downloading and analyzing academic papers, generating comprehensive Obsidian notes with extracted figures.

Two skills included:

| Skill | Purpose |
|-------|---------|
| `acm-paper-analyze` | Download papers from ACM Digital Library (via DOI or title) and generate analysis notes |
| `pdf-paper-analyze` | Analyze local PDF files (single file or entire directory) and generate analysis notes |

Both skills produce structured Chinese-language Obsidian notes with:
- YAML frontmatter (tags, scoring, metadata)
- Abstract translation and key takeaways
- Research background and motivation
- Method overview with embedded figures
- Experimental results
- Comprehensive evaluation (5-dimension scoring)

## Prerequisites

### 1. Obsidian Vault

Set the `OBSIDIAN_VAULT_PATH` environment variable pointing to your vault root:

**macOS/Linux** (add to `~/.zshrc` or `~/.bashrc`):
```bash
export OBSIDIAN_VAULT_PATH="/Users/yourname/path/to/your-vault"
```

**Windows PowerShell** (permanent):
```powershell
[System.Environment]::SetEnvironmentVariable("OBSIDIAN_VAULT_PATH", "C:/Users/YourName/path/to/your-vault", "User")
```

Your vault should have this directory structure:
```
Your Vault/
└── 20_Research/
    └── Papers/          # Notes organized by domain
        ├── HCI_AI/
        ├── 大模型/
        └── ...
```

### 2. Python Environment (>= 3.10)

```bash
# Create a dedicated environment (recommended)
conda create -n paper-analyze python=3.11 -y
conda activate paper-analyze

# Install dependencies
pip install "markitdown[pdf] @ git+https://github.com/microsoft/markitdown.git#subdirectory=packages/markitdown"
pip install PyMuPDF
pip install selenium  # only needed for acm-paper-analyze
```

### 3. Chrome Browser (only for `acm-paper-analyze`)

ACM Digital Library uses Cloudflare protection. Selenium with a real Chrome browser is required to download PDFs.

- Install [Google Chrome](https://www.google.com/chrome/)
- ChromeDriver is managed automatically by Selenium 4+

## Installation

Copy the skill directories to your Claude Code skills folder:

```bash
cp -r acm-paper-analyze ~/.claude/skills/
cp -r pdf-paper-analyze ~/.claude/skills/
```

## Usage

### Analyze an ACM paper by DOI

```
/acm-paper-analyze 10.1145/3772318.3791819
```

### Analyze an ACM paper by title

```
/acm-paper-analyze "A decision-theoretic representation of assistive interfaces"
```

Title input uses the [Semantic Scholar API](https://api.semanticscholar.org/) to resolve the DOI automatically.

### Analyze a local PDF

```
/pdf-paper-analyze /path/to/paper.pdf
```

### Analyze all PDFs in a directory

```
/pdf-paper-analyze /path/to/papers/
```

### Specify domain manually

```
/pdf-paper-analyze /path/to/paper.pdf --domain CHI2026
```

## Output

Notes are saved to `$OBSIDIAN_VAULT_PATH/20_Research/Papers/[Domain]/[Paper Title]/`:

```
Paper_Title/
├── Paper Title.md       # Analysis note
└── images/
    ├── page3.png        # Extracted figure pages
    ├── page7.png
    └── ...
```

### Domain Auto-Inference

If no domain is specified, the skill infers it from paper content:

| Keywords | Domain |
|----------|--------|
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
    │
    ▼
markitdown: PDF → Markdown text
    │
    ▼
PyMuPDF: Extract pages with figures/tables as PNG
    │
    ▼
Claude Code: Deep analysis of paper content
    │
    ▼
Obsidian note with embedded figures
```

## Compatibility

- Works with [evil-read-arxiv](https://github.com/juliye2025/evil-read-arxiv) — same vault structure (`20_Research/Papers/`) and note format
- The `paper-analyze` skill from evil-read-arxiv handles arXiv papers (TeX source); these skills extend coverage to ACM and arbitrary PDFs

## License

MIT
