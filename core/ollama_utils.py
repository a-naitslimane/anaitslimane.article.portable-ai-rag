import ollama


def ensure_models(*model_names: str, pull_if_missing: bool = False):
    try:
        response = ollama.list()
        available = {m.model for m in response.models}
    except Exception as e:
        raise RuntimeError(f"Ollama is not running or unreachable: {e}")

    def base_name(m: str) -> str:
        return m.split(":")[0]

    available_base = {base_name(m) for m in available}
    missing = [m for m in model_names if base_name(m) not in available_base]

    if not missing:
        return

    if pull_if_missing:
        for model in missing:
            print(f"Model '{model}' not found locally. Pulling...")
            ollama.pull(model)
            print(f"Model '{model}' ready.")
    else:
        raise RuntimeError(
            f"Required models not available in Ollama: {missing}. "
            f"Run 'ollama pull <model>' or check config.py."
        )