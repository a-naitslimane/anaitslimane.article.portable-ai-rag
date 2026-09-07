import os

import config


def _should_skip_file(file, ext, f_path, mode):
    is_minified = ".min." in file
    is_map_file = ext == ".map"
    is_lock_file = file in {
        "package-lock.json",
        "yarn.lock",
        "composer.lock",
        "packages.lock.json",
    }
    
    if is_minified or is_map_file or is_lock_file:
        return True

    if file in config.SKIP_FILES or ext in {".log", ".pem", ".key", ".tmp", ".bak"}:
        return True

    if mode == "code" and ext in config.MEDIA_EXTS:
        return True

    stat = os.stat(f_path)
    
    return stat.st_size > 1024 * 1024


def scan_workspace_for_file_changes(manifest):
    files_to_process = []
    tracked_files = {}

    print(f"  Starting Strict Scan in: {config.SOURCE_DIR}")
    for root, dirs, files in os.walk(config.SOURCE_DIR):
        dirs[:] = [d for d in dirs if d not in config.SKIP_DIRS]

        rel_root = os.path.relpath(root, config.SOURCE_DIR)
        mode = rel_root.split(os.sep)[0].lower() if rel_root != "." else "general"

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            f_path = os.path.join(root, file)

            if _should_skip_file(file, ext, f_path, mode):
                continue

            r_path = os.path.relpath(f_path, config.SOURCE_DIR).replace(os.sep, "/")
            stat = os.stat(f_path)
            info = {"mtime": stat.st_mtime, "size": stat.st_size, "mode": mode}
            tracked_files[r_path] = info

            if r_path not in manifest or manifest[r_path]["mtime"] < info["mtime"]:
                files_to_process.append((f_path, r_path, info, mode))

    return files_to_process, tracked_files