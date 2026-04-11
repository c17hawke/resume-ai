"""
parser.py — PDF resume → ResumeData dataclass
"""

from __future__ import annotations

import io
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional

import pdfplumber


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ContactInfo:
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    location: str = ""


@dataclass
class ExperienceEntry:
    title: str = ""
    company: str = ""
    dates: str = ""
    bullets: List[str] = field(default_factory=list)


@dataclass
class EducationEntry:
    degree: str = ""
    institution: str = ""
    dates: str = ""
    details: str = ""


@dataclass
class ResumeData:
    name: str = ""
    contact: ContactInfo = field(default_factory=ContactInfo)
    summary: str = ""
    experience: List[ExperienceEntry] = field(default_factory=list)
    education: List[EducationEntry] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)
    raw_sections: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Known section header keywords
# ---------------------------------------------------------------------------

KNOWN_HEADERS = {
    # experience
    "experience", "work experience", "professional experience",
    "employment", "employment history", "work history", "career history",
    # education
    "education", "academic background", "qualifications", "academic qualifications",
    "academic history",
    # skills
    "skills", "technical skills", "core competencies", "competencies",
    "expertise", "key skills", "areas of expertise", "technologies",
    "tools & technologies", "tools and technologies",
    # summary / objective
    "summary", "professional summary", "executive summary", "career summary",
    "objective", "career objective", "professional objective", "profile",
    "about me", "about", "overview",
    # certifications
    "certifications", "certificates", "certification", "licenses",
    "professional certifications",
    # projects
    "projects", "key projects", "notable projects", "personal projects",
    "side projects", "open source",
    # awards / achievements
    "awards", "honors", "achievements", "accomplishments",
    "recognition",
    # publications
    "publications", "research", "papers",
    # other
    "languages", "volunteer", "volunteering", "extracurricular",
    "interests", "hobbies", "references",
}

DATE_PATTERN = re.compile(
    r"""
    (?:
        (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)
        [\s,.-]*
    )?
    \d{4}
    (?:\s*[-–—]\s*
        (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)
        [\s,.-]*
        (?:\d{4}|[Pp]resent|[Cc]urrent|[Tt]oday|[Nn]ow)
    )?
    """,
    re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

@dataclass
class _Line:
    text: str
    avg_size: float
    is_bold: bool
    x0: float
    top: float


def _assemble_lines(page) -> List[_Line]:
    """Group page.chars by top coordinate (±2pt) into logical lines."""
    chars = page.chars
    if not chars:
        return []

    # Sort chars by vertical position then horizontal
    chars = sorted(chars, key=lambda c: (round(c["top"], 0), c["x0"]))

    lines: List[_Line] = []
    bucket: list = []
    bucket_top: Optional[float] = None

    for ch in chars:
        top = ch["top"]
        if bucket_top is None or abs(top - bucket_top) <= 2:
            bucket.append(ch)
            if bucket_top is None:
                bucket_top = top
        else:
            if bucket:
                lines.append(_chars_to_line(bucket))
            bucket = [ch]
            bucket_top = top

    if bucket:
        lines.append(_chars_to_line(bucket))

    return lines


def _chars_to_line(chars: list) -> _Line:
    chars = sorted(chars, key=lambda c: c["x0"])
    texts = []
    prev_x1 = None
    avg_char_width = sum(c.get("width", 6) for c in chars) / len(chars)
    for ch in chars:
        if prev_x1 is not None and ch["x0"] - prev_x1 > avg_char_width * 0.4:
            texts.append(" ")
        texts.append(ch.get("text", ""))
        prev_x1 = ch["x0"] + ch.get("width", 6)

    text = "".join(texts).strip()
    avg_size = sum(c.get("size", 11) for c in chars) / len(chars)
    is_bold = any("bold" in (c.get("fontname") or "").lower() for c in chars)
    x0 = chars[0]["x0"]
    top = chars[0]["top"]
    return _Line(text=text, avg_size=avg_size, is_bold=is_bold, x0=x0, top=top)


def _font_census(pdf) -> float:
    """Return the body font size (most common size across all pages)."""
    counter: Counter = Counter()
    for page in pdf.pages:
        for ch in page.chars:
            counter[round(ch.get("size", 11), 1)] += 1
    if not counter:
        return 11.0
    return counter.most_common(1)[0][0]


def _is_section_header(line: _Line, body_size: float) -> bool:
    raw = line.text.strip()
    normalized = raw.lower().rstrip(":").strip()
    if normalized in KNOWN_HEADERS:
        return True
    if line.avg_size >= body_size * 1.15 and len(raw.split()) <= 6:
        return True
    if line.is_bold and len(raw.split()) <= 5 and len(raw) > 2:
        return True
    if raw.upper() == raw and 2 < len(raw) <= 40 and raw.replace(" ", "").isalpha():
        return True
    return False


def _canonical_section(text: str) -> str:
    """Map a detected header to a canonical section key."""
    n = text.lower().rstrip(":").strip()
    if any(k in n for k in ("experience", "employment", "career", "work")):
        return "experience"
    if any(k in n for k in ("education", "academic", "qualifications")):
        return "education"
    if any(k in n for k in ("skill", "competenc", "expertise", "technolog", "tools")):
        return "skills"
    if any(k in n for k in ("summary", "profile", "objective", "about", "overview")):
        return "summary"
    if any(k in n for k in ("certif", "license")):
        return "certifications"
    if "project" in n:
        return "projects"
    if any(k in n for k in ("award", "honor", "achievement", "accomplishment")):
        return "awards"
    return n  # keep as-is for unknown sections


def _extract_contact(lines: List[_Line]) -> ContactInfo:
    contact = ContactInfo()
    text = " ".join(l.text for l in lines)
    # Email
    m = re.search(r"[\w.+-]+@[\w.-]+\.\w{2,}", text)
    if m:
        contact.email = m.group()
    # Phone
    m = re.search(r"[\+\(]?[\d\s\(\)\-\.]{7,15}(?=\s|$)", text)
    if m:
        phone = re.sub(r"\s+", "", m.group()).strip()
        if len(re.sub(r"\D", "", phone)) >= 7:
            contact.phone = m.group().strip()
    # LinkedIn
    m = re.search(r"linkedin\.com/in/[\w\-]+", text, re.I)
    if m:
        contact.linkedin = "https://" + m.group() if not m.group().startswith("http") else m.group()
    # GitHub
    m = re.search(r"github\.com/[\w\-]+", text, re.I)
    if m:
        contact.github = "https://" + m.group() if not m.group().startswith("http") else m.group()
    # Generic URL (website)
    m = re.search(r"https?://(?!linkedin|github)[\w./\-]+", text, re.I)
    if m:
        contact.website = m.group()
    # Location (city, state/country pattern)
    m = re.search(r"[A-Z][a-zA-Z\s]+,\s*[A-Z]{2,}", text)
    if m:
        contact.location = m.group().strip()
    return contact


def _parse_experience(lines: List[_Line], body_size: float) -> List[ExperienceEntry]:
    """Split experience section lines into individual job entries."""
    entries: List[ExperienceEntry] = []
    current: Optional[ExperienceEntry] = None

    for line in lines:
        text = line.text.strip()
        if not text:
            continue

        has_date = bool(DATE_PATTERN.search(text))
        is_bold_short = line.is_bold and len(text.split()) <= 10
        is_bullet = text.startswith(("•", "·", "▪", "◦", "-", "–", "*")) or (len(text) > 1 and text[0] == "\u2022")

        if is_bullet:
            bullet_text = re.sub(r"^[•·▪◦\-–\*\u2022]\s*", "", text).strip()
            if current is None:
                current = ExperienceEntry()
                entries.append(current)
            current.bullets.append(bullet_text)
        elif has_date and current is not None:
            # date line — attach dates to current entry
            current.dates = text
        elif is_bold_short and not has_date:
            # New entry header
            new_entry = ExperienceEntry()
            # Heuristic: if current has no title yet, fill title; else company
            if current is None or current.title:
                entries.append(new_entry)
                current = new_entry
                current.title = text
            else:
                current.company = text
        elif current is not None and not current.company and not has_date and not is_bullet:
            if not current.company:
                current.company = text
        else:
            if current is None:
                current = ExperienceEntry()
                entries.append(current)
            if not current.title:
                current.title = text
            elif not current.company:
                current.company = text

    return [e for e in entries if e.title or e.company or e.bullets]


def _parse_education(lines: List[_Line]) -> List[EducationEntry]:
    entries: List[EducationEntry] = []
    current: Optional[EducationEntry] = None

    for line in lines:
        text = line.text.strip()
        if not text:
            continue
        has_date = bool(DATE_PATTERN.search(text))
        if line.is_bold or line.avg_size > 10:
            if current is None or current.degree:
                current = EducationEntry()
                entries.append(current)
            if not current.degree:
                current.degree = text
            elif not current.institution:
                current.institution = text
        elif has_date and current:
            current.dates = text
        elif current:
            if not current.institution:
                current.institution = text
            else:
                current.details = (current.details + " " + text).strip()

    return [e for e in entries if e.degree or e.institution]


def _parse_skills(lines: List[_Line]) -> List[str]:
    """Extract skills as a flat list."""
    all_text = " ".join(l.text for l in lines)
    # Try comma/pipe/semicolon separated first
    separators = re.split(r"[,|;•·▪◦\n\t]+", all_text)
    skills = [s.strip().strip("–-·•*") .strip() for s in separators if s.strip()]
    skills = [s for s in skills if 1 < len(s) <= 60]
    return skills


def _parse_simple_list(lines: List[_Line]) -> List[str]:
    items = []
    for line in lines:
        text = line.text.strip().lstrip("•·▪◦-–*\u2022").strip()
        if text:
            items.append(text)
    return items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_pdf(pdf_file) -> ResumeData:
    """
    Parse a PDF resume into a ResumeData dataclass.

    pdf_file: file-like object or bytes (from st.file_uploader)
    """
    try:
        if isinstance(pdf_file, bytes):
            pdf_bytes = io.BytesIO(pdf_file)
        else:
            pdf_bytes = io.BytesIO(pdf_file.read())

        with pdfplumber.open(pdf_bytes) as pdf:
            return _parse(pdf)
    except Exception as exc:
        # Fallback: return minimal ResumeData with error note
        rd = ResumeData()
        rd.raw_sections["_error"] = str(exc)
        return rd


def _parse(pdf) -> ResumeData:
    body_size = _font_census(pdf)

    # Gather all lines across all pages
    all_lines: List[_Line] = []
    for page in pdf.pages:
        page_lines = _assemble_lines(page)
        if not page_lines:
            # Likely a scanned page — extract plain text as fallback
            text = page.extract_text() or ""
            for row in text.splitlines():
                if row.strip():
                    all_lines.append(_Line(text=row.strip(), avg_size=body_size,
                                           is_bold=False, x0=0, top=0))
        else:
            all_lines.extend(page_lines)

    if not all_lines:
        rd = ResumeData()
        rd.raw_sections["_warning"] = "No text extracted — PDF may be image-based."
        return rd

    # ---- Split into header block and sections ----
    section_map: dict[str, List[_Line]] = {}
    current_section = "_header"
    section_map[current_section] = []

    for line in all_lines:
        if not line.text.strip():
            continue
        if _is_section_header(line, body_size):
            key = _canonical_section(line.text)
            current_section = key
            if key not in section_map:
                section_map[key] = []
        else:
            section_map.setdefault(current_section, []).append(line)

    # ---- Name extraction ----
    header_lines = section_map.get("_header", [])
    name = ""
    contact_lines: List[_Line] = []
    if header_lines:
        # Name = line with largest font size (or first bold line)
        max_size = max(l.avg_size for l in header_lines)
        name_candidates = [l for l in header_lines if l.avg_size >= max_size * 0.95]
        if name_candidates:
            name = name_candidates[0].text.strip()
            contact_lines = [l for l in header_lines if l not in name_candidates[:1]]
        else:
            name = header_lines[0].text.strip()
            contact_lines = header_lines[1:]

    contact = _extract_contact(contact_lines)

    # ---- Summary ----
    summary_lines = section_map.get("summary", [])
    summary = " ".join(l.text for l in summary_lines).strip()

    # ---- Experience ----
    exp_lines = section_map.get("experience", [])
    experience = _parse_experience(exp_lines, body_size)

    # ---- Education ----
    edu_lines = section_map.get("education", [])
    education = _parse_education(edu_lines)

    # ---- Skills ----
    skill_lines = section_map.get("skills", [])
    skills = _parse_skills(skill_lines)

    # ---- Certifications ----
    cert_lines = section_map.get("certifications", [])
    certifications = _parse_simple_list(cert_lines)

    # ---- Projects ----
    proj_lines = section_map.get("projects", [])
    projects = _parse_simple_list(proj_lines)

    # ---- Raw fallback sections (anything else) ----
    raw_sections = {}
    skip = {"_header", "summary", "experience", "education", "skills",
            "certifications", "projects"}
    for key, lines in section_map.items():
        if key not in skip and lines:
            raw_sections[key] = " ".join(l.text for l in lines).strip()

    return ResumeData(
        name=name,
        contact=contact,
        summary=summary,
        experience=experience,
        education=education,
        skills=skills,
        certifications=certifications,
        projects=projects,
        raw_sections=raw_sections,
    )
