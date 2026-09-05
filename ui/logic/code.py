import config


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