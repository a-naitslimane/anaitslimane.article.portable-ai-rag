import config


def is_unsupported_minified_text(content):
    return len(content) > 1000 and "\n" not in content


def split_text_into_chunks(content):
    chunk_size = getattr(config, "CHUNK_SIZE", 3500)
    chunk_overlap = getattr(config, "CHUNK_OVERLAP", 800)
    return [
        content[i : i + chunk_size]
        for i in range(0, len(content), chunk_size - chunk_overlap)
    ]