import os

from pypdf import PdfReader


def read_file_content(file_path, mode):
    ext = os.path.splitext(file_path)[1].lower()
    
    if mode == "media":
        return f"MEDIA_ENTRY: {os.path.basename(file_path)} found in media library."

    if ext == '.pdf':
        return _get_text_from_pdf(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Null-byte check: If it contains null bytes, it's a binary file
            preview = f.read(1024)
            if '\0' in preview:
                return ""
            f.seek(0)
            return f.read()
    except:
        return ""



def _get_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        return " ".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
    except:
        return ""