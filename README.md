# CV Forge MCP Server

[![PyPI](https://img.shields.io/pypi/v/cv-forge-mcp)](https://pypi.org/project/cv-forge-mcp/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)

MCP (Model Context Protocol) server for [CV Forge](https://github.com/Guid-Lab/cv-forge). Lets AI assistants generate professional CVs as PDF/DOCX from conversation data.

## How It Works

1. You describe your experience to the AI (or paste LinkedIn profile text)
2. AI fills in the CV template using the `generate_cv` tool
3. AI calls `generate_pdf` or `generate_docx` to produce the document
4. You get a PDF/DOCX file **and** a link to the visual editor for manual tweaks

The MCP server automatically pulls and starts the CV Forge Docker container — no manual setup needed.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)

## Quick Start

### Claude Code

```bash
claude mcp add cv-forge -- uvx cv-forge-mcp
```

### Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json` (Linux) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "cv-forge": {
      "command": "uvx",
      "args": ["cv-forge-mcp"]
    }
  }
}
```

### Manual install (alternative)

```bash
pip install cv-forge-mcp
```

## Available Tools

| Tool | Description |
|------|-------------|
| `generate_cv` | Returns an empty CV JSON template for the AI to fill in |
| `generate_pdf` | Generates ATS PDF from CV data, returns file path + editor URL |
| `generate_docx` | Generates ATS DOCX from CV data, returns file path + editor URL |

## AI Instructions

See [`INSTRUCTIONS.md`](INSTRUCTIONS.md) for the full system prompt and workflow guidelines for AI assistants using CV Forge.

## Links

- **CV Forge:** https://github.com/Guid-Lab/cv-forge
- **Live Demo:** https://cv.guidlab.pl
- **Docker Hub:** https://hub.docker.com/r/guidlab/cv-forge
