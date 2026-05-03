from llm import ask_llm

def apply_voice(text):
    prompt = f"""
    Rewrite in Giuseppe's style.

    STYLE:
    - extremely concise
    - no titles like "Overview" or "Definition"
    - no full sentences unless necessary
    - prefer compressed patterns (X = A + B)
    - think in systems, not descriptions
    - use Salvatore Sanfilippo Antirez style as guidance. 
    - be factual 

    FORMAT:
    - short sections
    - bullets
    - highlight key idea explicitly
    - include 1 insight (constraint / trade-off)

    RULES:
    - remove generic wording
    - remove explanations like "refers to"
    - compress aggressively
    - no fluff
    - no repetition
    - no headings like "Overview", "Definition", "Applications"

    CONTENT:
    {text}
    """

    res = ask_llm(prompt, [], [])
    return res