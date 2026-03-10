"""MCP Server for CV Forge — generate CVs from AI conversations."""

import json
import os
import shutil
import subprocess
import tempfile
import time

import httpx
from mcp.server.fastmcp import FastMCP

CONTAINER_NAME = "cv-forge"
IMAGE_NAME = "guidlab/cv-forge"
LOCAL_URL = "http://localhost:5000"
REMOTE_URL = "https://cv.guidlab.pl"

_base_url: str | None = None
_mode: str | None = None  # "local", "remote", or None (not yet chosen)

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


def _check_environment() -> dict:
    """Detect what's available: local running, Docker, remote."""
    info = {"local_running": False, "docker": False, "docker_image": False, "remote": False}

    try:
        r = httpx.get(f"{LOCAL_URL}/", timeout=3)
        if r.status_code == 200:
            info["local_running"] = True
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    if shutil.which("docker"):
        info["docker"] = True
        result = subprocess.run(
            ["docker", "images", "-q", IMAGE_NAME],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            info["docker_image"] = True

    try:
        r = httpx.get(f"{REMOTE_URL}/", timeout=5)
        if r.status_code == 200:
            info["remote"] = True
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    return info


def _get_base_url() -> str:
    """Return the active base URL. Raises if not yet configured."""
    if _base_url:
        return _base_url

    env_url = os.environ.get("CV_FORGE_URL", "").strip().rstrip("/")
    if env_url:
        return env_url

    raise RuntimeError(
        "CV Forge not configured. Call the cv_forge_setup tool first."
    )


def _start_local() -> bool:
    """Start local Docker container. Pulls image if needed. Returns True on success."""
    if not shutil.which("docker"):
        return False

    # Check if already running
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
        capture_output=True, text=True,
    )
    if not (result.returncode == 0 and result.stdout.strip() == "true"):
        start = subprocess.run(["docker", "start", CONTAINER_NAME], capture_output=True)
        if start.returncode != 0:
            # Pull image if not present
            check = subprocess.run(
                ["docker", "images", "-q", IMAGE_NAME],
                capture_output=True, text=True,
            )
            if not check.stdout.strip():
                pull = subprocess.run(
                    ["docker", "pull", IMAGE_NAME],
                    capture_output=True,
                )
                if pull.returncode != 0:
                    return False

            try:
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
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False

    for _ in range(30):
        try:
            r = httpx.get(f"{LOCAL_URL}/", timeout=2)
            if r.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(1)
    return False


def _post_load_data(cv_data: dict) -> str:
    """Store CV data on the server and return the editor URL."""
    base = _get_base_url()
    r = httpx.post(f"{base}/api/load-data", json=cv_data, timeout=10)
    r.raise_for_status()
    return r.json()["url"]


@mcp.tool()
def cv_forge_setup(mode: str = "auto") -> str:
    """Set up CV Forge backend. MUST be called before generate_pdf or generate_docx.

    Detects the environment and lets the user choose how to run CV Forge:
    - "local": Run locally via Docker (pulls image if needed, ~1.7 GB)
    - "remote": Use the hosted demo at cv.guidlab.pl (no install needed)
    - "auto": Auto-detect — use local if Docker is available, otherwise remote

    If mode is "auto", present the user with the available options and ask which
    they prefer. If only one option is available, use it automatically.

    Args:
        mode: "local", "remote", or "auto" (default).
    """
    global _base_url, _mode

    env_url = os.environ.get("CV_FORGE_URL", "").strip().rstrip("/")
    if env_url:
        _base_url = env_url
        _mode = "custom"
        return json.dumps({"status": "ready", "mode": "custom", "url": env_url})

    info = _check_environment()

    if mode == "remote":
        if not info["remote"]:
            return json.dumps({"status": "error", "message": "Remote server cv.guidlab.pl is not reachable."})
        _base_url = REMOTE_URL
        _mode = "remote"
        return json.dumps({"status": "ready", "mode": "remote", "url": REMOTE_URL})

    if mode == "local":
        if info["local_running"]:
            _base_url = LOCAL_URL
            _mode = "local"
            return json.dumps({"status": "ready", "mode": "local", "url": LOCAL_URL})
        if not info["docker"]:
            return json.dumps({"status": "error", "message": "Docker is not installed. Install Docker or use mode='remote'."})
        if _start_local():
            _base_url = LOCAL_URL
            _mode = "local"
            return json.dumps({"status": "ready", "mode": "local", "url": LOCAL_URL})
        return json.dumps({"status": "error", "message": "Failed to start local container."})

    # mode == "auto" — present options
    if info["local_running"]:
        _base_url = LOCAL_URL
        _mode = "local"
        return json.dumps({"status": "ready", "mode": "local", "url": LOCAL_URL,
                           "message": "Using already running local instance."})

    options = []
    if info["docker"]:
        if info["docker_image"]:
            options.append({"mode": "local", "description": "Local Docker (image ready, fast startup)"})
        else:
            options.append({"mode": "local", "description": "Local Docker (needs to pull ~1.7 GB image first)"})
    if info["remote"]:
        options.append({"mode": "remote", "description": "Remote server cv.guidlab.pl (no install needed)"})

    if not options:
        return json.dumps({"status": "error",
                           "message": "No backend available. Install Docker or check your internet connection."})

    if len(options) == 1:
        # Only one option — use it directly
        return cv_forge_setup(mode=options[0]["mode"])

    return json.dumps({
        "status": "choose",
        "message": "Ask the user which mode they prefer:",
        "options": options,
    })


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
    - employer_groups: group_name is the company name, display_company in each position
      should also be set to the company name (or subsidiary/brand name if different)
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
    base = _get_base_url()

    r = httpx.post(f"{base}/api/generate/ats-pdf", json=cv_data, timeout=30)
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
    base = _get_base_url()

    r = httpx.post(
        f"{base}/api/generate/docx",
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
