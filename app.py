import difflib
import os
from datetime import datetime

import requests
import streamlit as st
from bs4 import BeautifulSoup
from pypdf import PdfReader

from cleaner import clean_markdown
from lint import add_ignore_rule, generate_lint_proposals, parse_proposals
from llm import ask_llm, summarize_for_wiki
from memory import index_note, query_notes
from source_store import save_raw_source
from wiki_manager import integrate_into_wiki, parse_llm_output, write_wiki


def get_diff(old_text, new_text):
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile="current", tofile="proposed", lineterm=""
    )

    return "\n".join(diff)


NOTES_DIR = "notes"

st.set_page_config(page_title="GiuMan Assistant", layout="wide")
st.title("GiuMan Assistant")

tab1, tab2, tab3 = st.tabs(["Ask Assistant", "Add Knowledge", "Improve Wiki"])


def ensure_notes_dir():
    os.makedirs(NOTES_DIR, exist_ok=True)


def list_note_files():
    ensure_notes_dir()
    return [f for f in os.listdir(NOTES_DIR) if f.endswith(".md") or f.endswith(".txt")]


def append_to_note(filename, content, source_label):
    ensure_notes_dir()
    path = os.path.join(NOTES_DIR, filename)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n\n## Added {timestamp} — {source_label}\n\n")
        f.write(clean_markdown(content))
        f.write("\n")

    with open(path, encoding="utf-8") as f:
        full_text = f.read()

    index_note(full_text, filename)


def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""

    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        text += f"\n\n--- Page {page_num} ---\n{page_text}"

    return text.strip()


def extract_url_text(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else url
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    return title, "\n".join(lines)[:20000]


with tab1:
    question = st.text_input("Ask something")

    if question:
        docs, sources = query_notes(question)

        # HARD FILTER for ideas
        if "idea" in question.lower():
            filtered_docs = []
            filtered_sources = []

            for i in range(len(docs)):
                if sources and i < len(sources) and sources[i]:
                    src = sources[i].get("source", "")
                    if "ideas.md" in src:
                        filtered_docs.append(docs[i])
                        filtered_sources.append(sources[i])

            docs = filtered_docs
            sources = filtered_sources
        from voice import apply_voice

        raw_answer = ask_llm(question, docs, sources)
        answer = apply_voice(raw_answer)

        st.subheader("Answer")
        st.write(answer)

        st.subheader("Sources")
        for s in sources:
            if not s:
                continue

            source = s.get("source", "unknown")
            chunk = s.get("chunk", "unknown")

            st.write(f"- {source} / chunk {chunk}")


with tab2:
    st.subheader("Integrate source into wiki")
    knowledge_type = st.selectbox(
        "Knowledge type",
        [
            "Source only",
            "Idea",
            "Concept",
            "Framework",
            "Project",
            "Client",
            "Decision",
            "Pattern",
            "Profile",
            "Action",
        ],
        index=0,
    )
    source_name = st.text_input("Source name (e.g. article title)", key="integrate_source_name")

    source_text = st.text_area("Paste raw content here", height=200, key="integrate_text_area")

    if st.button("Integrate into Wiki"):
        if source_name and source_text:
            raw_path = save_raw_source(source_name, source_text, "manual")
            updated_files = integrate_into_wiki(source_text, source_name, knowledge_type)
            st.caption(f"Raw source saved: {raw_path}")
            st.success(f"Updated: {updated_files}")
        else:
            st.warning("Provide both source name and content.")
    st.divider()
    st.subheader("Integrate webpage / URL into wiki")

    url = st.text_input("Paste URL", key="wiki_url_input")

    if st.button("Integrate URL into Wiki"):
        if url:
            try:
                page_title, page_text = extract_url_text(url)

                # optional limit
                page_text = page_text[:15000]

                raw_path = save_raw_source(page_title, page_text, "url")

                clean_summary = summarize_for_wiki(page_text)
                clean_summary = apply_voice(clean_summary)

                updated_files = integrate_into_wiki(clean_summary, page_title)
                st.caption(f"Raw source saved: {raw_path}")

                st.success(f"Integrated URL into wiki. Updated: {updated_files}")
            except Exception as e:
                st.error(f"Could not integrate URL: {e}")
        else:
            st.warning("Paste a URL first.")


with tab3:
    st.subheader("Improve Wiki (Lint)")

    if st.button("Run Lint"):
        raw_output = generate_lint_proposals()
        st.session_state["lint_raw"] = raw_output

        proposals = parse_proposals(st.session_state["lint_raw"])

        def is_ignored(proposal_text, ignore_rules):
            text = proposal_text.lower()

            for rule in ignore_rules:
                if rule.lower() in text:
                    return True
            return False

        # Load ignore rules (simple)
        ignore_rules = []
        ignore_path = "wiki/lint_ignore.md"

        if os.path.exists(ignore_path):
            with open(ignore_path, encoding="utf-8") as f:
                ignore_rules = [
                    line.strip("- ").strip()
                    for line in f.readlines()
                    if line.strip().startswith("-")
                ]

        # Filter proposals
        filtered_proposals = []
        for p in proposals:
            if not is_ignored(p["raw"], ignore_rules):
                filtered_proposals.append(p)

        proposals = filtered_proposals

        st.subheader("Parsed Proposals")

        for i, p in enumerate(proposals):
            st.markdown(f"### Proposal {i + 1}")

            # Extract a short description
            lines = p["raw"].splitlines()
            desc = ""

            for line in lines:
                if line.startswith("description:"):
                    desc = line.replace("description:", "").strip()
                    break

            st.markdown(f"**{desc}**")

            # --- Preview Diff ---
            updates = parse_llm_output(p["raw"])

            for filename, new_content in updates.items():
                clean_name = filename.replace("wiki/", "").replace("wiki\\", "")
                path = os.path.join("wiki", clean_name)

                if os.path.exists(path):
                    with open(path, encoding="utf-8") as f:
                        old_content = f.read()
                else:
                    old_content = ""

                diff = get_diff(old_content, new_content)

                st.markdown(f"**Diff for {clean_name}**")
                st.code(diff, language="diff")

            # --- Apply ---
            if st.button(f"Apply Proposal {i + 1}", key=f"apply_{i}"):
                write_wiki(updates)
                st.success(f"Applied Proposal {i + 1}")

            if st.button(f"Ignore Proposal {i + 1}", key=f"ignore_{i}"):
                # simple rule: use description or first line
                add_ignore_rule(p["raw"])

                st.warning(f"Ignored Proposal {i + 1}")
