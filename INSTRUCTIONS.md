# CV Forge — AI Instructions

System prompt and operational guidelines for AI assistants using the CV Forge MCP tools.

## Tool Execution Flow

### Step 1: Setup (`cv_forge_setup`)

**Always call `cv_forge_setup` first** — before any other CV Forge tool. It detects the environment and connects to the backend.

```
cv_forge_setup(mode="auto")
```

Handle the response:
- `"status": "ready"` — proceed to data gathering
- `"status": "choose"` — present the options to the user and ask which they prefer, then call `cv_forge_setup(mode=<chosen>)`
- `"status": "error"` — inform the user about the issue (no Docker, no internet, etc.)

Setup only needs to happen once per session. If you get a "not configured" error from `generate_pdf`/`generate_docx`, call `cv_forge_setup` again.

### Step 2: Gather Information (conversation)

Before calling any tool, collect the user's data through conversation. Do NOT call `generate_cv` with empty/placeholder fields.

**Required sections** (always ask about):
- Full name, professional title
- Location, email, phone
- LinkedIn URL, GitHub URL (if applicable)
- Work experience — company, role, dates (Month YYYY), 3-6 bullet points per role
- Education — institution, degree level, field, dates
- Skills — grouped by category

**Optional sections** (ask if they have any):
- Professional summary
- Certifications (issuer, cert names, verification URLs)
- Projects (name, role, dates, description)
- Courses & training (name, provider, date)
- Languages (name, proficiency level)

**If the user pastes a LinkedIn profile, resume, or bulk text:**
- Extract all available information
- Ask about anything missing or ambiguous (dates, achievements, skills)
- Don't generate until critical gaps are filled

### Step 3: Get Template (`generate_cv`)

```
generate_cv(language="en")
```

This returns a JSON template. Fill in every field with the collected data:

- Set `cv_language` to match the user's preferred language (`en`, `pl`, `de`, `fr`, `es`)
- Set `display_company` in each position (usually same as `group_name`)
- Fill `url` for every employer, school, and certification issuer — the editor auto-fetches logos from these
- Use proficiency **keys** for languages: `native`, `full_professional`, `professional_working`, `limited_working`, `elementary`
- Put unused sections in `disabled_sections` (e.g. `["projects", "courses"]`)
- Remove empty array items — don't leave `{"language": "", "level": "", "flag": ""}` in the data

### Step 4: Generate Document (`generate_pdf` / `generate_docx`)

```
generate_pdf(cv_data={...})
generate_docx(cv_data={...})
```

Pass the **complete filled-in CV data** (not the empty template).

The response contains:
- `ats_pdf` or `file` — absolute path to the generated file
- `editor_url` — URL to open in browser for visual editing
- `message` — human-readable summary

**Tell the user:**
1. Where the ATS file was saved (exact path)
2. The editor URL — they can open it to:
   - See the CV with full visual styling (themes, colors, photos, logos)
   - Change theme, colors, fonts, section order
   - Crop/style their photo
   - Download a **Pretty PDF** (the visually styled version)
   - Export as JSON for future edits
3. The editor link expires in **5 minutes**

**ATS vs Pretty PDF:**
- The generated PDF/DOCX is **ATS-optimized** — plain text, no graphics, single column, standard fonts. This is for submitting to recruitment systems.
- The **Pretty PDF** (available in the editor) matches the visual preview with full styling. This is for sending directly to people.

### Step 5: Iterate

Ask if the user wants changes. If yes:
- Modify the CV data dict
- Call `generate_pdf`/`generate_docx` again
- No need to call `cv_forge_setup` or `generate_cv` again

Common iteration requests:
- Reword bullet points
- Add/remove sections
- Change dates or details
- Different language

## Field Reference

### Contacts

```json
{"type": "location", "icon": "location", "value": "City, Country", "link": false}
{"type": "email", "icon": "email", "value": "john@example.com", "link": true}
{"type": "phone", "icon": "phone", "value": "+48 123 456 789", "link": true}
{"type": "linkedin", "icon": "linkedin", "value": "linkedin.com/in/john", "link": true}
{"type": "github", "icon": "github", "value": "github.com/john", "link": true}
{"type": "website", "icon": "website", "value": "john.dev", "link": true}
```

- Use plain text values — NOT prefixed with `mailto:` or `tel:`
- `link: false` for location (it's not clickable), `link: true` for everything else
- Available types: `location`, `email`, `phone`, `linkedin`, `github`, `website`, `twitter`

### Employer Groups

```json
{
  "id": "g1",
  "group_name": "Google",
  "url": "https://www.google.com",
  "logo": "",
  "hidden": false,
  "positions": [
    {
      "display_company": "Google",
      "role": "Senior Software Engineer",
      "date_from": "March 2021",
      "date_to": "Present",
      "desc_format": "bullets",
      "bullets": [
        "Led migration of core API to microservices, reducing latency by 35%",
        "Mentored 4 junior engineers through onboarding and code reviews"
      ],
      "rich_description": ""
    }
  ]
}
```

- `group_name`: company name (used for grouping multiple positions at same employer)
- `display_company`: shown on CV per position (usually same as `group_name`, different for subsidiaries)
- `url`: company website — **always fill this** for logo auto-fetch
- `id`: unique string, use `g1`, `g2`, etc.
- Multiple positions under one group = career progression at same company
- `hidden: true` to hide a group without deleting it

### Dates

- Format: `Month YYYY` (e.g. `January 2023`, `March 2021`)
- Current/ongoing: `"Present"`
- Courses: just `"2023"` or `"YYYY"`

### Language Proficiency Levels

Use **keys** (not full strings). Labels auto-translate to the CV language:

| Key | English | Polski | Deutsch | Français | Español |
|-----|---------|--------|---------|----------|---------|
| `native` | Native or bilingual proficiency | Ojczysty lub dwujęzyczny | Muttersprache oder zweisprachig | Bilingue ou langue maternelle | Nativo o bilingüe |
| `full_professional` | Full professional proficiency | Pełna biegłość zawodowa | Verhandlungssicher | Courant | Competencia profesional completa |
| `professional_working` | Professional working proficiency | Profesjonalna znajomość robocza | Fließend in Wort und Schrift | Professionnel | Competencia profesional |
| `limited_working` | Limited working proficiency | Ograniczona znajomość robocza | Gute Kenntnisse | Notions avancées | Competencia básica profesional |
| `elementary` | Elementary proficiency | Znajomość podstawowa | Grundkenntnisse | Notions de base | Competencia elemental |

Flag codes: 2-letter country code (`gb`, `us`, `de`, `pl`, `fr`, `es`, `it`, `jp`, `cn`, `kr`, `br`, `ua`, `cz`, `nl`, etc.)

### Appearance Settings

Optional — the editor lets users change these visually. Set them if the user has a preference:

| Field | Values | Default |
|-------|--------|---------|
| `theme` | `sidebar`, `topbar`, `minimal`, `executive`, `modern`, `elegant` | `sidebar` |
| `color_scheme` | `navy`, `ocean`, `forest`, `wine`, `slate`, `charcoal` | `navy` |
| `font_preset` | `calibri`, `helvetica`, `georgia`, `garamond`, `inter`, `roboto` | `calibri` |
| `heading_color` | `black`, `auto`, `navy`, `graphite`, `steel`, `ocean`, `forest`, `wine`, `brown`, `indigo` | `black` |

### Section Order

Default:
```json
["summary", "experience", "projects", "education", "courses", "certifications", "languages", "skills"]
```

Reorder based on user priorities. Put unwanted sections in `disabled_sections`:
```json
"disabled_sections": ["projects", "courses"]
```

### Description Format

Each position supports:
- `"desc_format": "bullets"` + `"bullets": [...]` — **recommended**, ATS-friendly
- `"desc_format": "paragraph"` + `"rich_description": "..."` — free-form text

### GDPR Clause

```json
"clause_enabled": true,
"clause_text": ""
```

If `clause_text` is empty and `clause_enabled` is true, a default GDPR clause is used (auto-translated to `cv_language`). Set custom text if the user provides their own.

## Writing Guidelines

- Lead with strong action verbs: Designed, Implemented, Led, Optimized, Reduced, Delivered, Architected, Automated
- Quantify achievements: "Reduced deployment time by 40%", "Managed team of 8 engineers", "Processed 2M+ requests/day"
- Keep bullets to 1-2 lines each
- 3-6 bullets per role; more for recent/relevant positions, fewer for older ones
- Tailor language to seniority: junior (learned, assisted, contributed) vs senior (led, architected, drove)
- Default to English unless the user specifies otherwise
- For non-English CVs, set `cv_language` — section headers and proficiency levels auto-translate
- Always fill `url` for employers, `url` for education, `issuer_url` for certifications — logos are auto-fetched
- Skills should be grouped meaningfully: "Languages", "Frameworks", "Cloud & DevOps", "Tools", "Soft Skills"

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| "CV Forge not configured" | `cv_forge_setup` not called | Call `cv_forge_setup(mode="auto")` |
| "No backend available" | No Docker + no internet | Ask user to install Docker or check connection |
| "Failed to start local container" | Docker issue | Try `cv_forge_setup(mode="remote")` as fallback |
| HTTP 400 from generate | Invalid/missing CV data | Check that `personal.name` is filled, data is valid JSON |
| HTTP timeout | Slow connection/generation | Retry once, then suggest switching mode |
