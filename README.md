# Portable AI Knowledge Base Engine

A lightweight, fully local RAG (Retrieval-Augmented Generation) system built with FastAPI, LanceDB, and Ollama.

## Prerequisites

* Python 3.12+
* [Ollama](https://ollama.com/) running locally

## Quick Start

1. **Pull required Ollama models**
   ```bash
   ollama pull snowflake-arctic-embed:m-long
   ollama pull stable-coder
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Add documents**
   Place your source files (`.py`, `.cs`, `.php`, `.c`, `.ts`, `.md`, `.pdf`, etc.) inside `./data/source_files/`.

4. **Sync the Vector Database**
   ```bash
   python run_sync.py
   ```

5. **Run the API & UI Server**
   ```bash
   uvicorn web.main:app
   ```
   Open `http://localhost:8000` in your browser.

---

## Prompt tips
* To explicitly tell he AI that it HAS access to your local DB
"Based on the files you can see in your context, what is the main function of my bash script?"
* 3 to 5 core principles, no more no less

## convinient copy on windows
```powershell
    robocopy "C:\Source\Path" "C:\Destination\Path" /E /XD node_modules platforms .migration_backup .git bin obj
```