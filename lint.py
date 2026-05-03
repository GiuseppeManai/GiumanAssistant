import os
from wiki_manager import read_wiki
from llm import ask_llm

def add_ignore_rule(text):
    path = "wiki/lint_ignore.md"

    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n- {text}\n")

def generate_lint_proposals():
    pages = read_wiki()
    ignore_path = "wiki/lint_ignore.md"
    ignore_rules = ""
    if os.path.exists(ignore_path):
        with open(ignore_path, "r", encoding="utf-8") as f:
            ignore_rules = f.read()

    combined = "\n\n".join([f"# {k}\n{v}" for k, v in pages.items()])

    prompt = f"""
    You are improving a markdown wiki.

    TASK:
    - Identify ONLY high-impact issues
    - Focus on structural problems, major duplication across sections/files, or contradictions
    - Think like a senior consultant, not an editor

    DO NOT propose changes for:
    - small wording improvements
    - minor redundancy within the same section
    - stylistic differences
    - removing or rewriting single bullets
    - micro-optimizations that do not materially improve understanding

    Only create a proposal if:
    - it significantly improves clarity OR
    - it removes LARGE duplication across sections/files OR
    - it fixes structural issues

    If the improvement is small, DO NOT create a proposal.

    If the wiki is already acceptable, return NO proposals.

    Return at most 3 proposals.
    Prefer fewer, high-impact changes.

    IGNORE RULES:
    {ignore_rules}

    You MUST NOT propose suggestions that are semantically similar to these rules.

    OUTPUT FORMAT:

    ===PROPOSAL===
    id: <unique_id>
    type: <merge|restructure|dedupe|clarify>
    impact: high | medium
    target_files:
    - file1.md

    description:
    <short description>

    ===FILE: wiki/<filename>.md===
    <full updated content>

    Repeat for each proposal. No other text.

    WIKI:
    {combined}
    """

    response = ask_llm(prompt, [], [])
    return response

def parse_proposals(output):
    proposals = []
    current = None
    buffer = []

    for line in output.splitlines():
        if line.startswith("===PROPOSAL==="):
            if current:
                current["raw"] = "\n".join(buffer).strip()
                proposals.append(current)

            current = {
                "raw": "",
                "files": {}
            }
            buffer = []
        else:
            buffer.append(line)

    if current:
        current["raw"] = "\n".join(buffer).strip()
        proposals.append(current)

    return proposals