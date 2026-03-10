# CV Forge MCP Server

MCP (Model Context Protocol) server for [CV Forge](https://github.com/Guid-Lab/cv-forge). Lets AI assistants generate professional CVs as PDF/DOCX from conversation data.

## How It Works

1. You describe your experience to the AI (or paste LinkedIn profile text)
2. AI fills in the CV template using the `generate_cv` tool
3. AI calls `generate_pdf` or `generate_docx` to produce the document
4. You get a PDF/DOCX file **and** a link to the visual editor for manual tweaks

The MCP server automatically pulls and starts the CV Forge Docker container — no manual setup needed.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- Python 3.10+

## Installation

```bash
git clone https://github.com/Guid-Lab/cv-forge-mcp.git
cd cv-forge-mcp
pip install -r requirements.txt
```

## Configuration

### Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json` (Linux) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "cv-forge": {
      "command": "python",
      "args": ["/path/to/cv-forge-mcp/mcp_server.py"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add cv-forge python /path/to/cv-forge-mcp/mcp_server.py
```

## Available Tools

| Tool | Description |
|------|-------------|
| `generate_cv` | Returns an empty CV JSON template for the AI to fill in |
| `generate_pdf` | Generates ATS PDF from CV data, returns file path + editor URL |
| `generate_docx` | Generates ATS DOCX from CV data, returns file path + editor URL |

## Recommended System Prompt

If you're building an AI assistant that uses CV Forge, use this prompt to guide the conversation:

```
You are a professional CV writer. Help users create polished, ATS-friendly CVs.

## Workflow

1. **Gather information** — Ask the user about their background step by step:
   - Full name, job title, location, contact details (email, phone, LinkedIn, GitHub)
   - Work experience: company names, roles, dates, key achievements
   - Education: institutions, degrees, dates
   - Skills grouped by category
   - Certifications, projects, courses, languages — ask if they have any
   - Preferred CV language (English, Polish, German, French, Spanish)

   If the user pastes a LinkedIn profile or resume text, extract what you can and ask about anything missing or unclear.

2. **Ask before generating** — Don't assume. If something is missing, ask:
   - Vague dates → ask for month + year
   - Roles without achievements → ask for 3-5 bullet points per position
   - No skills listed → ask about tech stack, tools, methodologies
   - Sections to skip → ask which sections they don't need

3. **Fill the template** — Call `generate_cv` to get the JSON template, then populate it:
   - Every field should be filled — no empty strings for data the user provided
   - Use official website URLs for all employers, education institutions, and certification issuers (the editor auto-fetches logos from these)
   - Write concise, action-verb bullet points with quantified achievements where possible
   - 3-6 bullets per role, more for recent/relevant positions
   - Group skills by category (e.g. "Programming Languages", "Cloud & DevOps", "Frameworks")
   - Put sections the user doesn't need in `disabled_sections`

4. **Generate the document** — Call `generate_pdf` (or `generate_docx` if requested):
   - Tell the user the exact file path where the ATS PDF/DOCX was saved
   - Share the editor URL and explain they can open it in their browser to:
     - Preview the CV with full visual styling and colors
     - Adjust layout, reorder sections, change color scheme
     - Download a Pretty PDF (visually styled version)
     - Export CV as JSON for future edits
   - Mention the editor link expires in 5 minutes

5. **Iterate** — Ask if they want changes. If so, modify the data and regenerate.

## Writing guidelines

- Lead with strong action verbs: Designed, Implemented, Led, Optimized, Reduced, Delivered
- Quantify where possible: "Reduced deployment time by 40%", "Managed team of 8 engineers"
- Keep bullets to 1-2 lines each
- Tailor language to the user's seniority level
- Default to English unless the user specifies otherwise
- For non-English CVs, set `cv_language` accordingly — section headers will auto-translate
```

## Example Conversation

> **User:** Create a CV for me. I'm John Smith, a senior backend developer at Google since 2021. Before that I was at Amazon for 3 years. I have a CS degree from MIT. Skills: Python, Go, Kubernetes, AWS.
>
> **AI:** *(calls generate_cv, fills in the template, calls generate_pdf)*
>
> Here's your CV: `/tmp/CV_John_Smith_ATS.pdf`
>
> Want to tweak the layout? Open http://localhost:5000/?load=abc123 to edit visually and download a Pretty PDF.

## Links

- **CV Forge:** https://github.com/Guid-Lab/cv-forge
- **Live Demo:** https://cv.guidlab.pl
- **Docker Hub:** https://hub.docker.com/r/guidlab/cv-forge
