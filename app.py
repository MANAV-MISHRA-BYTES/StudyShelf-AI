import json
import os
import re
from io import BytesIO

import fitz  # PyMuPDF
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="StudyShelf AI", page_icon="📚", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 2rem;}
.hero {padding: 1.4rem 1.6rem; border: 1px solid #ddd; border-radius: 18px; margin-bottom: 1.2rem;}
.hero h1 {margin-bottom: .25rem;}
.small {color: #666;}
.card {border: 1px solid #e2e2e2; border-radius: 14px; padding: 1rem; margin: .6rem 0;}
.tag {display:inline-block; padding:.18rem .55rem; border-radius:999px; background:#f0f0f0; margin:.15rem .2rem .15rem 0; font-size:.82rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>📚 StudyShelf AI</h1>
<p class="small">Turn a messy folder of study PDFs into an organized, searchable shelf using a local open-weight AI model.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Local AI")
    base_url = st.text_input("LM Studio URL", os.getenv("LM_STUDIO_URL", "http://localhost:1234"))
    model = st.text_input("Model name", os.getenv("LM_STUDIO_MODEL", "local-model"))
    categories = st.text_area(
        "Categories",
        "Mathematics\nComputer Science\nData Science & AI\nProgramming\nEngineering\nGeneral / Other",
        height=160,
    )
    st.caption("Your PDFs stay on this computer. The app sends extracted text only to your local LM Studio server.")

uploaded = st.file_uploader(
    "Upload your study PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    help="Upload several PDFs at once to simulate a messy study folder.",
)


def extract_pdf(file_obj):
    data = file_obj.getvalue()
    doc = fitz.open(stream=data, filetype="pdf")
    text_parts = []
    pages = len(doc)
    for page in doc:
        text_parts.append(page.get_text())
    text = "\n".join(text_parts).strip()
    return text, pages


def ask_local_ai(filename, text, category_list):
    # Keep the request small enough for local models while retaining useful context.
    excerpt = re.sub(r"\s+", " ", text)[:12000]
    prompt = f"""You are organizing a student's PDF library.
Analyze this document and return ONLY valid JSON with these exact keys:
category, tags, priority, summary

Rules:
- category must be exactly one of: {', '.join(category_list)}
- tags must be an array of 3 to 5 short strings
- priority must be exactly one of: High, Medium, Low
- summary must be 1 or 2 concise sentences
- Do not use markdown or code fences.

Filename: {filename}
Document text:
{excerpt}
"""

    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 250,
    }
    response = requests.post(url, json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.I)
    match = re.search(r"\{.*\}", content, flags=re.S)
    if not match:
        raise ValueError("The local model did not return JSON.")
    result = json.loads(match.group(0))
    return result


if uploaded:
    st.write(f"**{len(uploaded)} PDF(s) ready**")
    preview_rows = []
    for f in uploaded:
        preview_rows.append({"File": f.name, "Size": f"{f.size / 1024:.1f} KB"})
    st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

    if st.button("✨ Organize with Local AI", type="primary", use_container_width=True):
        category_list = [x.strip() for x in categories.splitlines() if x.strip()]
        if not category_list:
            st.error("Add at least one category in the sidebar.")
            st.stop()

        results = []
        progress = st.progress(0)
        status = st.empty()

        for i, f in enumerate(uploaded):
            status.write(f"Analyzing **{f.name}**...")
            try:
                text, pages = extract_pdf(f)
                if not text:
                    raise ValueError("No selectable text found. This PDF may be scanned/image-only.")
                ai = ask_local_ai(f.name, text, category_list)
                ai.setdefault("tags", [])
                results.append({
                    "file": f.name,
                    "pages": pages,
                    "category": ai.get("category", "General / Other"),
                    "priority": ai.get("priority", "Medium"),
                    "tags": ai.get("tags", []),
                    "summary": ai.get("summary", "No summary returned."),
                })
            except Exception as exc:
                results.append({
                    "file": f.name,
                    "pages": 0,
                    "category": "Needs Review",
                    "priority": "Medium",
                    "tags": ["manual review"],
                    "summary": f"Could not analyze this PDF: {exc}",
                })
            progress.progress((i + 1) / len(uploaded))

        status.success("Organization complete.")
        st.session_state["results"] = results

if "results" in st.session_state:
    results = st.session_state["results"]
    st.divider()
    st.subheader("Your organized shelf")

    col1, col2, col3 = st.columns(3)
    col1.metric("Documents", len(results))
    col2.metric("Categories", len(set(r["category"] for r in results)))
    col3.metric("High priority", sum(r["priority"] == "High" for r in results))

    query = st.text_input("🔎 Search your organized shelf", placeholder="Try: databases, probability, machine learning...")
    filtered = results
    if query:
        q = query.lower()
        filtered = [r for r in results if q in (r["file"] + " " + r["category"] + " " + " ".join(r["tags"]) + " " + r["summary"]).lower()]

    for r in filtered:
        tags = " ".join(f'<span class="tag">{t}</span>' for t in r["tags"])
        st.markdown(f"""
        <div class="card">
        <h4 style="margin-bottom:.35rem">{r['file']}</h4>
        <div><b>{r['category']}</b> · {r['priority']} priority · {r['pages']} pages</div>
        <p>{r['summary']}</p>
        <div>{tags}</div>
        </div>
        """, unsafe_allow_html=True)

    export = pd.DataFrame([
        {"File": r["file"], "Pages": r["pages"], "Category": r["category"], "Priority": r["priority"], "Tags": ", ".join(r["tags"]), "Summary": r["summary"]}
        for r in results
    ])
    st.download_button(
        "⬇️ Download study index (CSV)",
        export.to_csv(index=False).encode("utf-8"),
        "studyshelf-index.csv",
        "text/csv",
    )
else:
    st.info("Upload a few PDFs above, then click **Organize with Local AI**.")
    st.markdown("### How it works")
    st.markdown("1. Extracts text from each PDF locally.  \n2. Sends the text to your local open-weight model through LM Studio.  \n3. The model assigns a category, tags, priority and summary.  \n4. StudyShelf displays everything as a searchable shelf and lets you export an index.")
