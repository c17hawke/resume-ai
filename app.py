"""
app.py — Streamlit UI for PDF Resume → Neomorphic HTML converter
Run: streamlit run app.py
"""

import os
import streamlit as st
from resume_parser import parse_pdf
from renderer import build_html

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Resume → Neomorphic HTML",
    page_icon="📄",
    layout="centered",
)

st.title("Resume → Neomorphic HTML")
st.caption(
    "Upload your PDF resume and get a beautiful, self-contained **index.html** "
    "with neomorphism styling and dark/light theme — ready to host on GitHub Pages."
)

# ---------------------------------------------------------------------------
# File uploader
# ---------------------------------------------------------------------------

uploaded = st.file_uploader("Drop your resume PDF here", type=["pdf"])

if uploaded is None:
    st.info("Upload a PDF resume to get started.")
    st.stop()

# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

with st.spinner("Parsing resume…"):
    resume_data = parse_pdf(uploaded)

# Check for errors
if "_error" in resume_data.raw_sections:
    st.error(f"Failed to parse PDF: {resume_data.raw_sections['_error']}")
    st.stop()

if "_warning" in resume_data.raw_sections:
    st.warning(resume_data.raw_sections["_warning"])

# ---------------------------------------------------------------------------
# Preview parsed sections
# ---------------------------------------------------------------------------

with st.expander("Parsed sections preview", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**Name:** {resume_data.name or '_(not detected)_'}")
        c = resume_data.contact
        if c.email:
            st.markdown(f"**Email:** {c.email}")
        if c.phone:
            st.markdown(f"**Phone:** {c.phone}")
        if c.linkedin:
            st.markdown(f"**LinkedIn:** {c.linkedin}")
        if c.github:
            st.markdown(f"**GitHub:** {c.github}")
        if c.location:
            st.markdown(f"**Location:** {c.location}")
    with col_b:
        st.markdown(f"**Summary:** {'✔ detected' if resume_data.summary else '_(none)_'}")
        st.markdown(f"**Experience entries:** {len(resume_data.experience)}")
        st.markdown(f"**Education entries:** {len(resume_data.education)}")
        st.markdown(f"**Skills:** {len(resume_data.skills)}")
        st.markdown(f"**Certifications:** {len(resume_data.certifications)}")
        st.markdown(f"**Projects:** {len(resume_data.projects)}")

    if resume_data.experience:
        st.divider()
        st.markdown("**Experience entries detected:**")
        for i, e in enumerate(resume_data.experience, 1):
            label = e.title or e.company or f"Entry {i}"
            st.markdown(
                f"&nbsp;&nbsp;**{i}.** {label}"
                + (f" @ {e.company}" if e.company and e.title else "")
                + (f" — {e.dates}" if e.dates else "")
                + (f" ({len(e.bullets)} bullets)" if e.bullets else ""),
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# Generate + download
# ---------------------------------------------------------------------------

st.divider()
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("⚡ Generate & Save index.html", type="primary", use_container_width=True):
        with st.spinner("Generating HTML…"):
            html_str = build_html(resume_data)

        # Write to project root (same directory as app.py)
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_str)

        st.session_state["html_str"] = html_str
        st.session_state["output_path"] = output_path
        st.success(f"Saved → `{output_path}`")

with col2:
    if "html_str" in st.session_state:
        st.download_button(
            label="⬇ Download index.html",
            data=st.session_state["html_str"],
            file_name="index.html",
            mime="text/html",
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# Live preview
# ---------------------------------------------------------------------------

if "html_str" in st.session_state:
    st.subheader("Live preview")
    st.caption(
        "Theme toggle works in the preview below. "
        "The downloaded file will remember your preference across browser sessions."
    )
    st.components.v1.html(st.session_state["html_str"], height=650, scrolling=True)

# ---------------------------------------------------------------------------
# GitHub Pages tip
# ---------------------------------------------------------------------------

st.divider()
st.info(
    "**To publish on GitHub Pages:**  \n"
    "1. Push `index.html` to your repository root  \n"
    "2. Go to **Settings → Pages → Branch: main → / (root)**  \n"
    "3. Your resume will be live at `https://yourusername.github.io/reponame/`"
)
