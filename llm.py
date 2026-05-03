import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_agent_instructions():
    try:
        with open("AGENTS.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def ask_llm(question, docs, sources):
    agent_instructions = load_agent_instructions()

    is_idea_query = any(word in question.lower() for word in ["idea", "ideas"])

    # Pull personal profile explicitly
    personal_context = ""
    for i in range(len(docs)):
        if sources and i < len(sources) and sources[i] and "source" in sources[i]:
            if "personal_profile.md" in sources[i]["source"]:
                personal_context += docs[i] + "\n\n"

    # Build context
    context_parts = []
    for i in range(len(docs)):
        if sources and i < len(sources) and sources[i] and "source" in sources[i]:
            context_parts.append(f"Source: {sources[i]['source']}\n{docs[i]}")

    context = "\n\n".join(context_parts)

    prompt = f"""
{agent_instructions}

You are Giuseppe's twin assistant.

PERSONAL CONTEXT:
{personal_context}

INSTRUCTIONS:
- Think and reason using Giuseppe's decision model and thinking style
- Apply his filters: client relevance, impact, feasibility
- Use challenge mode when solutioning
- Be structured, concise, and practical

SPECIAL RULE:
If the question is about ideas:
- ONLY use ideas.md content
- DO NOT infer or generate ideas from profile, concepts, or strategy pages

---

Context:
{context}

---

Question:
{question}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content


def describe_image(image_bytes, filename):
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
Describe this image for a personal knowledge base.

Include:
- what is visible
- important text
- diagrams or objects
- why useful later

Filename: {filename}
"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded}"
                        }
                    }
                ]
            }
        ]
    )

    return res.choices[0].message.content


def summarize_for_wiki(text):
    agent_instructions = load_agent_instructions()

    prompt = f"""
{agent_instructions}

You are preparing clean input for a knowledge wiki.

TASK:
- Extract only high-value information
- Remove noise (navigation, ads, repetition)
- Convert into structured bullet points

OUTPUT FORMAT:

## Key Points
- ...

## Concepts
- ...

## Applications (if any)
- ...

## Notes
- ...

CONTENT:
{text}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content