"""
renderer.py — ResumeData → self-contained index.html (embedded CSS + JS)
"""

from __future__ import annotations

import html
from resume_parser import (
    ContactInfo, EducationEntry, ExperienceEntry, ResumeData
)
from typing import List


# ---------------------------------------------------------------------------
# SVG icon library (inline — no external fetch)
# ---------------------------------------------------------------------------

_ICONS = {
    "email": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>'
        '<polyline points="22,6 12,13 2,6"/></svg>'
    ),
    "phone": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 '
        '19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/>'
        '</svg>'
    ),
    "linkedin": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
        'fill="currentColor">'
        '<path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6z"/>'
        '<rect x="2" y="9" width="4" height="12"/>'
        '<circle cx="4" cy="4" r="2"/></svg>'
    ),
    "github": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
        'fill="currentColor">'
        '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 '
        '6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 '
        '0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 '
        '6.44 7A3.37 3.37 0 009 18.13V22"/></svg>'
    ),
    "globe": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="2" y1="12" x2="22" y2="12"/>'
        '<path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>'
        '</svg>'
    ),
    "location": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>'
        '<circle cx="12" cy="10" r="3"/></svg>'
    ),
    "sun": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="5"/>'
        '<line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>'
        '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>'
        '<line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>'
        '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
        '</svg>'
    ),
    "moon": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>'
    ),
}


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def _css_block() -> str:
    return """
:root {
  /* Light theme */
  --bg:              #e0e5ec;
  --bg-card:         #e0e5ec;
  --text-primary:    #2d3748;
  --text-secondary:  #4a5568;
  --text-muted:      #718096;
  --accent:          #5b8dee;
  --accent-light:    #7ba7f5;
  --accent-dark:     #3a6fd8;
  --shadow-dark:     #b8bec7;
  --shadow-light:    #ffffff;
  --neu-raise:       6px 6px 14px var(--shadow-dark), -6px -6px 14px var(--shadow-light);
  --neu-raise-sm:    3px 3px 8px var(--shadow-dark), -3px -3px 8px var(--shadow-light);
  --neu-inset:       inset 4px 4px 10px var(--shadow-dark), inset -4px -4px 10px var(--shadow-light);
  --radius-card:     18px;
  --radius-pill:     50px;
  --font-main:       'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  --transition:      all 0.3s ease;
}

[data-theme="dark"] {
  --bg:              #1e2130;
  --bg-card:         #1e2130;
  --text-primary:    #e2e8f0;
  --text-secondary:  #a0aec0;
  --text-muted:      #718096;
  --accent:          #7ba7f5;
  --accent-light:    #9dc0ff;
  --accent-dark:     #5b8dee;
  --shadow-dark:     #141720;
  --shadow-light:    #282d43;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text-primary);
  font-family: var(--font-main);
  font-size: 15px;
  line-height: 1.7;
  min-height: 100vh;
  transition: var(--transition);
}

.page {
  max-width: 860px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem 4rem;
  display: grid;
  gap: 1.5rem;
}

/* ---- Neomorphic card ---- */
.neu-card {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  box-shadow: var(--neu-raise);
  padding: 1.75rem 2rem;
  transition: var(--transition);
}

/* ---- Header / hero card ---- */
.header-card {
  text-align: center;
  padding: 2.5rem 2rem 2rem;
}

.resume-name {
  font-size: 2.4rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin-bottom: 0.4rem;
}

.resume-tagline {
  font-size: 1rem;
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
  font-style: italic;
}

.contact-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.6rem 1.2rem;
}

.contact-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  text-decoration: none;
  transition: color 0.2s;
}

.contact-item:hover { color: var(--accent); }
.contact-item svg { flex-shrink: 0; }

/* ---- Section title ---- */
.section-title {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 1.2rem;
  padding-bottom: 0.6rem;
  position: relative;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 2.5rem;
  height: 2px;
  background: var(--accent);
  border-radius: 2px;
}

/* ---- Experience ---- */
.experience-entry {
  background: var(--bg-card);
  border-radius: 12px;
  box-shadow: var(--neu-raise-sm);
  padding: 1.2rem 1.4rem;
  margin-bottom: 1rem;
  transition: var(--transition);
}

.experience-entry:last-child { margin-bottom: 0; }

.entry-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-bottom: 0.2rem;
}

.job-title {
  font-weight: 700;
  font-size: 1rem;
  color: var(--text-primary);
}

.job-dates {
  font-size: 0.82rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.job-company {
  font-size: 0.9rem;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 0.6rem;
}

.bullets {
  list-style: none;
  padding: 0;
  margin: 0;
}

.bullets li {
  position: relative;
  padding-left: 1.2rem;
  margin-bottom: 0.3rem;
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.bullets li::before {
  content: '▸';
  position: absolute;
  left: 0;
  color: var(--accent);
  font-size: 0.75rem;
  top: 0.2em;
}

/* ---- Education ---- */
.education-entry {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--shadow-dark);
}

.education-entry:last-child { margin-bottom: 0; border-bottom: none; padding-bottom: 0; }

.degree { font-weight: 700; font-size: 1rem; color: var(--text-primary); }
.institution { font-size: 0.9rem; color: var(--accent); font-weight: 600; }
.edu-dates { font-size: 0.82rem; color: var(--text-muted); }
.edu-details { font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.25rem; }

/* ---- Skills pills ---- */
.skills-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.neu-pill {
  display: inline-block;
  padding: 0.35rem 0.9rem;
  border-radius: var(--radius-pill);
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-card);
  box-shadow: var(--neu-inset);
  transition: var(--transition);
  cursor: default;
}

.neu-pill:hover {
  color: var(--accent);
}

/* ---- Simple lists (certs, projects) ---- */
.simple-list {
  list-style: none;
  padding: 0;
}

.simple-list li {
  position: relative;
  padding-left: 1.2rem;
  margin-bottom: 0.4rem;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.simple-list li::before {
  content: '✦';
  position: absolute;
  left: 0;
  color: var(--accent);
  font-size: 0.6rem;
  top: 0.35em;
}

/* ---- Raw / overflow sections ---- */
.raw-text {
  font-size: 0.875rem;
  color: var(--text-secondary);
  white-space: pre-wrap;
  line-height: 1.6;
}

/* ---- Theme toggle button ---- */
.theme-toggle {
  position: fixed;
  top: 1.2rem;
  right: 1.2rem;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  background: var(--bg-card);
  color: var(--text-secondary);
  box-shadow: var(--neu-raise);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition);
  z-index: 999;
}

.theme-toggle:hover { color: var(--accent); }
.theme-toggle:active { box-shadow: var(--neu-inset); }

/* ---- Summary text ---- */
.summary-text {
  color: var(--text-secondary);
  font-size: 0.95rem;
  line-height: 1.75;
}

/* ---- Responsive ---- */
@media (max-width: 600px) {
  .resume-name { font-size: 1.8rem; }
  .page { padding: 1.5rem 1rem 3rem; }
  .neu-card { padding: 1.25rem 1.2rem; }
}
"""


# ---------------------------------------------------------------------------
# JS
# ---------------------------------------------------------------------------

def _js_block() -> str:
    sun = _ICONS["sun"]
    moon = _ICONS["moon"]
    sun_escaped = sun.replace("`", "\\`")
    moon_escaped = moon.replace("`", "\\`")
    return f"""
(function() {{
  var html = document.documentElement;
  var btn  = document.getElementById('themeToggle');
  var SUN  = `{sun_escaped}`;
  var MOON = `{moon_escaped}`;

  function applyTheme(t) {{
    html.setAttribute('data-theme', t);
    btn.innerHTML = (t === 'dark') ? SUN : MOON;
    btn.setAttribute('aria-label', (t === 'dark') ? 'Switch to light mode' : 'Switch to dark mode');
  }}

  var stored = localStorage.getItem('resume-theme') || 'light';
  applyTheme(stored);

  btn.addEventListener('click', function() {{
    var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    localStorage.setItem('resume-theme', next);
    applyTheme(next);
  }});
}})();
"""


# ---------------------------------------------------------------------------
# HTML component builders
# ---------------------------------------------------------------------------

def _e(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text) if text else "")


def _header_card(name: str, contact: ContactInfo, summary: str) -> str:
    tagline = ""
    if summary:
        # Use first sentence as tagline
        first_sentence = summary.split(".")[0].strip()
        if len(first_sentence) > 10:
            tagline = first_sentence + "."

    contact_items = []
    if contact.email:
        contact_items.append(
            f'<a class="contact-item" href="mailto:{_e(contact.email)}">'
            f'{_ICONS["email"]}<span>{_e(contact.email)}</span></a>'
        )
    if contact.phone:
        phone_clean = contact.phone.replace(" ", "").replace("-", "")
        contact_items.append(
            f'<a class="contact-item" href="tel:{_e(phone_clean)}">'
            f'{_ICONS["phone"]}<span>{_e(contact.phone)}</span></a>'
        )
    if contact.linkedin:
        label = contact.linkedin.split("linkedin.com/in/")[-1].rstrip("/")
        contact_items.append(
            f'<a class="contact-item" href="{_e(contact.linkedin)}" target="_blank" rel="noopener">'
            f'{_ICONS["linkedin"]}<span>{_e(label) or "LinkedIn"}</span></a>'
        )
    if contact.github:
        label = contact.github.split("github.com/")[-1].rstrip("/")
        contact_items.append(
            f'<a class="contact-item" href="{_e(contact.github)}" target="_blank" rel="noopener">'
            f'{_ICONS["github"]}<span>{_e(label) or "GitHub"}</span></a>'
        )
    if contact.website:
        label = contact.website.replace("https://", "").replace("http://", "").rstrip("/")
        contact_items.append(
            f'<a class="contact-item" href="{_e(contact.website)}" target="_blank" rel="noopener">'
            f'{_ICONS["globe"]}<span>{_e(label)}</span></a>'
        )
    if contact.location:
        contact_items.append(
            f'<span class="contact-item">'
            f'{_ICONS["location"]}<span>{_e(contact.location)}</span></span>'
        )

    contact_html = "\n    ".join(contact_items)
    tagline_html = f'<p class="resume-tagline">{_e(tagline)}</p>' if tagline else ""

    return f"""  <div class="neu-card header-card">
    <h1 class="resume-name">{_e(name) or "Resume"}</h1>
    {tagline_html}
    <div class="contact-row">
    {contact_html}
    </div>
  </div>"""


def _section_card(title: str, content_html: str) -> str:
    if not content_html.strip():
        return ""
    return f"""  <section class="neu-card">
    <h2 class="section-title">{_e(title)}</h2>
    {content_html}
  </section>"""


def _summary_html(summary: str) -> str:
    return f'<p class="summary-text">{_e(summary)}</p>'


def _experience_html(entries: List[ExperienceEntry]) -> str:
    if not entries:
        return ""
    parts = []
    for e in entries:
        bullets_html = ""
        if e.bullets:
            items = "\n      ".join(f"<li>{_e(b)}</li>" for b in e.bullets)
            bullets_html = f'<ul class="bullets">\n      {items}\n    </ul>'

        company_html = f'<div class="job-company">{_e(e.company)}</div>' if e.company else ""

        parts.append(f"""    <div class="experience-entry">
      <div class="entry-header">
        <span class="job-title">{_e(e.title)}</span>
        <span class="job-dates">{_e(e.dates)}</span>
      </div>
      {company_html}
      {bullets_html}
    </div>""")
    return "\n".join(parts)


def _education_html(entries: List[EducationEntry]) -> str:
    if not entries:
        return ""
    parts = []
    for e in entries:
        details_html = f'<p class="edu-details">{_e(e.details)}</p>' if e.details else ""
        parts.append(f"""    <div class="education-entry">
      <div class="degree">{_e(e.degree)}</div>
      <div class="institution">{_e(e.institution)}</div>
      <div class="edu-dates">{_e(e.dates)}</div>
      {details_html}
    </div>""")
    return "\n".join(parts)


def _skills_html(skills: List[str]) -> str:
    if not skills:
        return ""
    pills = "\n    ".join(f'<span class="neu-pill">{_e(s)}</span>' for s in skills)
    return f'<div class="skills-grid">\n    {pills}\n  </div>'


def _simple_list_html(items: List[str]) -> str:
    if not items:
        return ""
    li_items = "\n    ".join(f"<li>{_e(i)}</li>" for i in items)
    return f'<ul class="simple-list">\n    {li_items}\n  </ul>'


def _raw_section_html(text: str) -> str:
    return f'<pre class="raw-text">{_e(text)}</pre>'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_html(resume_data: ResumeData) -> str:
    css = _css_block()
    js = _js_block()

    sections = []

    sections.append(_header_card(resume_data.name, resume_data.contact, resume_data.summary))

    if resume_data.summary:
        sections.append(_section_card("Summary", _summary_html(resume_data.summary)))

    if resume_data.experience:
        sections.append(_section_card("Experience", _experience_html(resume_data.experience)))

    if resume_data.education:
        sections.append(_section_card("Education", _education_html(resume_data.education)))

    if resume_data.skills:
        sections.append(_section_card("Skills", _skills_html(resume_data.skills)))

    if resume_data.certifications:
        sections.append(_section_card("Certifications", _simple_list_html(resume_data.certifications)))

    if resume_data.projects:
        sections.append(_section_card("Projects", _simple_list_html(resume_data.projects)))

    # Render any remaining unmapped sections
    for key, text in resume_data.raw_sections.items():
        if key.startswith("_") or not text:
            continue
        title = key.replace("_", " ").title()
        sections.append(_section_card(title, _raw_section_html(text)))

    # Filter out empty sections
    body_sections = "\n\n".join(s for s in sections if s.strip())

    name_title = _e(resume_data.name) or "Resume"

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{name_title} – Resume">
  <title>{name_title} – Resume</title>
  <style>{css}</style>
</head>
<body>

  <button class="theme-toggle" id="themeToggle" aria-label="Switch to dark mode">
    {_ICONS["moon"]}
  </button>

  <div class="page">
{body_sections}
  </div>

  <script>{js}</script>
</body>
</html>
"""
