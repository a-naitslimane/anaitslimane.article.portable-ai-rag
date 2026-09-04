import config


def get_behavior_guides(mode):
    if mode == "strict":
        return "STRICT MODE: Rely solely on provided context. If information is missing, state that it is missing."
    return "HYBRID MODE: Rely on context first. Supplement with general knowledge only if directly relevant."


def construct_audit_prompt(active, behavior_guide, found_sources, context, question):
    if not context or context.strip() == "No context found.":
        return f"""SYSTEM: You are a concise technical assistant.

CRITICAL DIRECTIVE: Answer the user query directly and concisely. If you cannot answer precisely, state that you do not know. Never generate hypothetical code, fake filenames, or unrequested analyses.

USER REQUEST:
{question}"""

    return f"""SYSTEM: You are a {active["persona"]}. {active["instruction"]}

=== CRITICAL INSTRUCTIONS ===
1. PRECISION & CONCISENESS: Provide direct, accurate, and minimal answers. Omit introductory text, boilerplate, and general summaries.
2. ZERO SPECULATION: Base your answer EXCLUSIVELY on the literal content of the PROJECT CONTEXT. Never invent hypothetical files, functions, or scenarios.
3. ABSTENTION MANDATE: If the exact answer cannot be determined from the provided context, state ONLY: "The provided context does not contain enough information to answer this query."

=== BEHAVIOR GUIDE ===
{behavior_guide}

=== PROJECT CONTEXT ===
Sources: {found_sources}
---
{context}
---

=== USER REQUEST ===
{question}"""


def get_final_top_k(request_top_k, question):
    base_top_k = (
        request_top_k if request_top_k is not None else getattr(config, "TOP_K", 30)
    )
    audit_keywords = {
        "mismatch",
        "refactor",
        "inconsistent",
        "broken",
        "check logic",
        "compare",
    }
    is_audit_mode = any(k in question.lower() for k in audit_keywords)
    return base_top_k * 2 if is_audit_mode else base_top_k