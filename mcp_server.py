"""MCP Server for CV Forge — generate CVs from AI conversations."""

import json
import os
import subprocess
import tempfile
import time

import httpx
from mcp.server.fastmcp import FastMCP

CONTAINER_NAME = "cv-forge"
IMAGE_NAME = "guidlab/cv-forge"
BASE_URL = "http://localhost:5000"

mcp = FastMCP("cv-forge")

TEMPLATE = {
    "personal": {
        "name": "",
        "title": "",
        "photo": "",
        "contacts": [
            {"type": "location", "icon": "location", "label": "", "value": "", "link": False},
            {"type": "email", "icon": "email", "label": "", "value": "", "link": True},
            {"type": "phone", "icon": "phone", "label": "", "value": "", "link": True},
            {"type": "linkedin", "icon": "linkedin", "label": "", "value": "", "link": True},
            {"type": "github", "icon": "github", "label": "", "value": "", "link": True},
        ],
    },
    "summary": "",
    "employer_groups": [
        {
            "id": "g1",
            "group_name": "",
            "url": "",
            "logo": "",
            "hidden": False,
            "positions": [
                {
                    "display_company": "",
                    "role": "",
                    "date_from": "Month YYYY",
                    "date_to": "Present",
                    "desc_format": "bullets",
                    "bullets": [],
                    "rich_description": "",
                }
            ],
        }
    ],
    "education": [
        {
            "institution": "",
            "level": "",
            "degree": "",
            "date_from": "Month YYYY",
            "date_to": "Month YYYY",
            "logo": "",
            "url": "",
        }
    ],
    "skills": [
        {"category": "", "items": []}
    ],
    "certifications": [
        {
            "issuer": "",
            "issuer_url": "",
            "logo": "",
            "items": [{"name": "", "url": ""}],
        }
    ],
    "projects": [
        {
            "name": "",
            "url": "",
            "role": "",
            "date_from": "Month YYYY",
            "date_to": "Present",
            "description": "",
        }
    ],
    "courses": [
        {"name": "", "provider": "", "url": "", "date": "YYYY"}
    ],
    "languages": [
        {"language": "", "level": "", "flag": ""}
    ],
    "section_order": [
        "summary", "experience", "skills", "projects",
        "certifications", "education", "courses", "languages",
    ],
    "disabled_sections": [],
    "color_scheme": "navy",
    "show_company_logos": True,
    "show_cert_logos": True,
    "show_lang_flags": True,
    "cv_language": "en",
    "clause_enabled": False,
    "clause_text": "",
}


def _ensure_container():
    """Start the CV Forge Docker container if not running."""
    try:
        r = httpx.get(f"{BASE_URL}/", timeout=3)
        if r.status_code == 200:
            return
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip() == "true":
        pass
    else:
        start = subprocess.run(["docker", "start", CONTAINER_NAME], capture_output=True)
        if start.returncode != 0:
            subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", CONTAINER_NAME,
                    "-p", "5000:5000",
                    "--restart", "unless-stopped",
                    "--memory", "1g",
                    "--cpus", "1.5",
                    IMAGE_NAME,
                ],
                check=True, capture_output=True,
            )

    for _ in range(30):
        try:
            r = httpx.get(f"{BASE_URL}/", timeout=2)
            if r.status_code == 200:
                return
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(1)
    raise RuntimeError("CV Forge container failed to start")


def _post_load_data(cv_data: dict) -> str:
    """Store CV data on the server and return the editor URL."""
    r = httpx.post(f"{BASE_URL}/api/load-data", json=cv_data, timeout=10)
    r.raise_for_status()
    return r.json()["url"]


@mcp.tool()
def generate_cv(language: str = "en") -> str:
    """Return an empty CV JSON template for the AI to fill in.

    IMPORTANT: Before calling this tool, gather the user's information first.
    Ask the user about each section they want to include:
    - Full name, job title, contact details (email, phone, LinkedIn, GitHub, location)
    - Work experience: company names, roles, dates, key achievements/responsibilities
    - Education: institutions, degrees, dates
    - Skills: categorized technical and soft skills
    - Certifications, projects, courses, languages (if applicable)

    Do NOT generate a CV with placeholder or empty fields. Ask follow-up questions
    for any missing critical sections (at minimum: personal info, experience, education, skills).

    IMPORTANT: Always fill in URLs for employers, education institutions, and certification issuers.
    Use their official website URLs (e.g. url: "https://www.google.com" for Google,
    issuer_url: "https://www.offensive-security.com" for OffSec). The editor uses these URLs
    to automatically fetch company/institution logos.

    Template field reference:
    - Dates: 'Month YYYY' format (e.g. 'January 2023'), use 'Present' for current positions
    - bullets: array of achievement/responsibility strings for each position
    - Contact types: location, email, phone, linkedin, github, website
    - Flag codes: 2-letter country code (gb, us, de, pl, fr, es, etc.)
    - Language levels: Native, Fluent, Professional working proficiency, Limited working proficiency, Elementary
    - desc_format: 'bullets' (list) or 'paragraph' (rich_description field)
    - disabled_sections: array of section names to hide (e.g. ['projects', 'courses'])
    - color_scheme: navy, emerald, charcoal, burgundy, slate, forest, royal, copper

    Args:
        language: CV language for section headers — en, pl, de, fr, or es.
    """
    template = json.loads(json.dumps(TEMPLATE))
    template["cv_language"] = language
    return json.dumps(template, indent=2)


@mcp.tool()
def generate_pdf(cv_data: dict) -> str:
    """Generate an ATS-optimized PDF and provide a link to the visual editor.

    Takes a complete CV JSON object (same structure as generate_cv template).
    All required fields (personal, experience, education, skills) must be filled in.

    Returns:
    - ats_pdf: absolute path to the generated ATS PDF file (saved in system temp directory)
    - editor_url: URL to open in the browser (http://localhost:5000/?load=<token>)
      where the user can preview their CV with full visual styling, customize colors/layout,
      and download a Pretty PDF version. The link expires after 5 minutes.

    The ATS PDF is a clean, text-based document optimized for applicant tracking systems.
    For a visually styled PDF with colors, logos, and layout — direct the user to open
    the editor_url in their browser and click "Download Pretty PDF" there.

    Args:
        cv_data: Complete CV data dictionary with all sections filled in.
    """
    _ensure_container()

    r = httpx.post(f"{BASE_URL}/api/generate/ats-pdf", json=cv_data, timeout=30)
    r.raise_for_status()

    name = cv_data.get("personal", {}).get("name", "CV").replace(" ", "_")
    path = os.path.join(tempfile.gettempdir(), f"CV_{name}_ATS.pdf")
    with open(path, "wb") as f:
        f.write(r.content)

    editor_url = _post_load_data(cv_data)

    return json.dumps({
        "ats_pdf": path,
        "editor_url": editor_url,
        "message": f"ATS PDF saved to {path}. "
                   f"Open {editor_url} in browser to customize the visual layout and download a Pretty PDF.",
    })


@mcp.tool()
def generate_docx(cv_data: dict) -> str:
    """Generate an ATS-optimized DOCX from CV data.

    Takes a complete CV JSON object (same structure as generate_cv template).
    All required fields (personal, experience, education, skills) must be filled in.

    Returns:
    - file: absolute path to the generated DOCX file (saved in system temp directory)
    - editor_url: URL to open in the browser (http://localhost:5000/?load=<token>)
      where the user can preview their CV visually, adjust layout/colors,
      and download alternative formats. The link expires after 5 minutes.

    Args:
        cv_data: Complete CV data dictionary with all sections filled in.
    """
    _ensure_container()

    r = httpx.post(
        f"{BASE_URL}/api/generate/docx",
        json=cv_data,
        timeout=30,
    )
    r.raise_for_status()

    name = cv_data.get("personal", {}).get("name", "CV").replace(" ", "_")
    path = os.path.join(tempfile.gettempdir(), f"CV_{name}.docx")
    with open(path, "wb") as f:
        f.write(r.content)

    editor_url = _post_load_data(cv_data)

    return json.dumps({
        "file": path,
        "editor_url": editor_url,
        "message": f"DOCX saved to {path}. Open {editor_url} to edit visually.",
    })


def main():
    mcp.run()

if __name__ == "__main__":
    main()
