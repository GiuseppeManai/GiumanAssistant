import difflib
import os
from datetime import datetime

import requests
import streamlit as st
from bs4 import BeautifulSoup
from pypdf import PdfReader

from giuman_assistant.ainote_importer import (
    import_new_notes,
    migrate_legacy_imports,
    validate_inbox,
)
from giuman_assistant.cleaner import clean_markdown
from giuman_assistant.lint import (
    add_ignore_rule,
    generate_lint_proposals,
    parse_proposals,
)
from giuman_assistant.llm import ask_llm, summarize_for_wiki
from giuman_assistant.memory import index_note, query_notes
from giuman_assistant.security import validate_url
from giuman_assistant.source_store import save_raw_source
from giuman_assistant.wiki_manager import (
    integrate_into_wiki,
    parse_llm_output,
    write_wiki,
)


def main():
    def get_diff(old_text, new_text):
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="current",
            tofile="proposed",
            lineterm="",
        )

        return "\n".join(diff)

    notes_dir = "notes"

    st.set_page_config(page_title="My Assistant", layout="wide")
    st.markdown(
        """
        <style>

        .stApp {
            background-color: #003366;
            color: #F4F7FA;
        }

        section[data-testid="stSidebar"] {
            background-color: #102A43;
        }

        h1, h2, h3, h4, h5, h6,
        label,
        [data-testid="stMarkdownContainer"] p {
            color: #F4F7FA;
        }

        [data-testid="stMarkdownContainer"] {
            color: #F4F7FA;
        }

        .stTextInput input,
        .stTextArea textarea {
            background-color: #0F253D;
            color: #F4F7FA;
            border: 1px solid #B7FF2A;
            border-radius: 8px;
        }

        .stTextInput label,
        .stTextArea label,
        .stSelectbox label {
            color: #F4F7FA;
        }

        .stButton button {
            background-color: #B7FF2A !important;
            color: #001F3F !important;
            border-radius: 8px;
            border: none;
            font-weight: 700;
        }

        .stButton button *,
        button[kind="secondary"] *,
        button[kind="primary"] * {
            color: #001F3F !important;
        }

        .stButton button:hover {
            background-color: #D4FF70 !important;
            color: #001F3F !important;
        }

        .stButton button:hover * {
            color: #001F3F !important;
        }

        div[role="radiogroup"] label {
            color: #F4F7FA;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.title("GiuMan Assistant")
    st.sidebar.caption("Local-first AI memory system")
    st.markdown(
        """
        # GiuMan Assistant

        Local-first AI memory and strategic reasoning system.
        """
    )

    page = st.sidebar.radio(
        "Navigation",
        [
            "Ask Assistant",
            "Add Knowledge",
            "Import Notes",
            "Improve Wiki",
        ],
    )

    def ensure_notes_dir():
        os.makedirs(notes_dir, exist_ok=True)

    def list_note_files():
        ensure_notes_dir()
        return [f for f in os.listdir(notes_dir) if f.endswith(".md") or f.endswith(".txt")]

    def append_to_note(filename, content, source_label):
        ensure_notes_dir()
        path = os.path.join(notes_dir, filename)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n\n## Added {timestamp} - {source_label}\n\n")
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
        response = requests.get(
            url,
            timeout=10,
            allow_redirects=True,
            stream=True,
        )

        max_size = 5 * 1024 * 1024
        content_length = response.headers.get("Content-Length")

        if content_length and int(content_length) > max_size:
            raise ValueError("Response too large")

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            raise ValueError(f"Unsupported content type: {content_type}")

        chunks = []
        total = 0

        for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
            if not chunk:
                continue

            total += len(chunk.encode("utf-8"))
            if total > max_size:
                raise ValueError("Response too large")

            chunks.append(chunk)

        html = "".join(chunks)
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        return title, "\n".join(lines)[:20_000]

    if page == "Ask Assistant":
        question = st.text_input("Ask something")

        if question:
            migrate_legacy_imports()
            docs, sources = query_notes(question, max_distance=1.2)
            if not docs:
                docs, sources = query_notes(question)

            if "idea" in question.lower():
                filtered_docs = []
                filtered_sources = []

                for i, doc in enumerate(docs):
                    if sources and i < len(sources) and sources[i]:
                        source = sources[i].get("source", "")
                        if "ideas.md" in source:
                            filtered_docs.append(doc)
                            filtered_sources.append(sources[i])

                docs = filtered_docs
                sources = filtered_sources

            from giuman_assistant.voice import apply_voice

            raw_answer = ask_llm(question, docs, sources)
            answer = apply_voice(raw_answer)

            st.subheader("Answer")
            st.write(answer)

            st.subheader("Retrieved context")
            for source in sources:
                if not source:
                    continue

                source_name = source.get("source_path") or source.get("source") or "unknown"
                original_filename = source.get("original_filename")
                detected_title = source.get("detected_title")
                wiki_page = source.get("wiki_page_filename")
                chunk = source.get("chunk", "unknown")
                distance = source.get("distance")

                parts = [source_name]
                if wiki_page and wiki_page not in source_name:
                    parts.append(f"page: {wiki_page}")
                if original_filename:
                    parts.append(f"original: {original_filename}")
                if detected_title:
                    parts.append(f"title: {detected_title}")
                parts.append(f"chunk {chunk}")
                if distance is not None:
                    parts.append(f"distance {distance:.3f}")

                st.write(" - ".join(parts))

    if page == "Add Knowledge":
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
                    validate_url(url)
                    page_title, page_text = extract_url_text(url)
                    page_text = page_text[:15000]

                    raw_path = save_raw_source(page_title, page_text, "url")

                    clean_summary = summarize_for_wiki(page_text)
                    clean_summary = apply_voice(clean_summary)

                    updated_files = integrate_into_wiki(clean_summary, page_title, "Source only")
                    st.caption(f"Raw source saved: {raw_path}")
                    st.success(f"Integrated URL into wiki. Updated: {updated_files}")
                except Exception as e:
                    st.error(f"Could not integrate URL: {e}")
            else:
                st.warning("Paste a URL first.")

    if page == "Import Notes":
        st.subheader("Import AINOTE2 Notes")
        st.write("Place exported AINOTE2 PDF or image files in `AINOTE2_inbox/raw/`.")

        category = st.selectbox(
            "Category",
            [
                "personal",
                "family",
                "professional",
                "confidential",
                "health",
                "finance",
                "learning",
                "ideas",
            ],
            index=2,
        )
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
            key="ainote_knowledge_type",
        )

        if st.button("Validate inbox"):
            result = validate_inbox()
            st.write(result["message"])
            st.write("New")
            st.write(result["new"])
            st.write("Already imported")
            st.write(result["already_imported"])
            st.write("Unsupported")
            st.write(result["unsupported"])

        if st.button("Import new notes"):
            result = import_new_notes(category, knowledge_type)
            st.write(result["message"])
            st.write("Processed")
            st.write(result["processed"])
            st.write("Skipped")
            st.write(result["skipped"])
            st.write("Failed")
            st.write(result["failed"])

    if page == "Improve Wiki":
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

            ignore_rules = []
            ignore_path = "wiki/lint_ignore.md"

            if os.path.exists(ignore_path):
                with open(ignore_path, encoding="utf-8") as f:
                    ignore_rules = [
                        line.strip("- ").strip()
                        for line in f.readlines()
                        if line.strip().startswith("-")
                    ]

            filtered_proposals = []
            for proposal in proposals:
                if not is_ignored(proposal["raw"], ignore_rules):
                    filtered_proposals.append(proposal)

            proposals = filtered_proposals
            st.subheader("Parsed Proposals")

            for i, proposal in enumerate(proposals):
                st.markdown(f"### Proposal {i + 1}")

                lines = proposal["raw"].splitlines()
                desc = ""

                for line in lines:
                    if line.startswith("description:"):
                        desc = line.replace("description:", "").strip()
                        break

                st.markdown(f"**{desc}**")

                updates = parse_llm_output(proposal["raw"])

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

                if st.button(f"Apply Proposal {i + 1}", key=f"apply_{i}"):
                    write_wiki(updates)
                    st.success(f"Applied Proposal {i + 1}")

                if st.button(f"Ignore Proposal {i + 1}", key=f"ignore_{i}"):
                    add_ignore_rule(proposal["raw"])
                    st.warning(f"Ignored Proposal {i + 1}")
