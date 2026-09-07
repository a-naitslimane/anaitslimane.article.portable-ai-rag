import { API } from './api.js';
import { Sidebar } from './sidebar.js';

const input = document.getElementById("user-input");
const container = document.getElementById("chat-container");
const loader = document.getElementById("typing-indicator");

function appendUserMessage(text) {
    const html = `
        <div class="message-row user-row">
            <div class="avatar">U</div>
            <div class="message-content">
                <div>${text}</div>
            </div>
        </div>`;
    container.insertAdjacentHTML("beforeend", html);
    container.scrollTop = container.scrollHeight;
}

function insertAiPlaceholder() {
    const html = `
        <div class="message-row ai-row" id="ai-placeholder">
            <div class="avatar">L</div>
            <div class="message-content">
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>`;
    container.insertAdjacentHTML("beforeend", html);
    container.scrollTop = container.scrollHeight;
    return document.getElementById("ai-placeholder");
}

function resolveAiPlaceholder(placeholder, completeText, sources, llmModel) {
    const renderedContent = window.marked ? marked.parse(completeText) : completeText;
    
    let footerHtml = "";
    if (llmModel || sources.length > 0) {
        footerHtml = `<div style="margin-top: 10px; border-top: 1px solid #1f2937; padding-top: 8px;">`;
        if (llmModel) {
            footerHtml += `<div style="font-size: 0.75rem; color: #9ca3af; margin-bottom: 4px;">🧠 Model: <span style="color: #d1d5db;">${llmModel}</span></div>`;
        }
        if (sources.length > 0) {
            footerHtml += `<div style="font-size: 0.75rem; color: #9ca3af;">🗂 Sources: ${sources.join(", ")}</div>`;
        }
        footerHtml += `</div>`;
    }

    placeholder.querySelector(".message-content").innerHTML =
        `<div class="markdown-body">${renderedContent}</div>${footerHtml}`;
    placeholder.removeAttribute("id");
    container.scrollTop = container.scrollHeight;
}

async function handleAsk() {
    const question = input.value.trim();
    const category = document.getElementById("category-select").value;
    const mode = document.getElementById("mode-select").value;

    if (!question) return;

    appendUserMessage(question);
    input.value = "";
    input.disabled = true;

    loader.innerHTML = `<span class="spinner"></span> Querying database...`;
    loader.style.display = "flex";

    const placeholder = insertAiPlaceholder();

    try {
        const stream = API.queryStream({ question, category, mode });

        let completeText = "";
        let sources = [];
        let llmModel = null;
        let buffer = "";
        let metaProcessed = false;

        for await (const fragment of stream) {
            buffer += fragment;

            if (!metaProcessed) {
                const separatorIndex = buffer.indexOf("\n---\n");
                if (separatorIndex !== -1) {
                    const rawMeta = buffer.slice(0, separatorIndex);
                    try {
                        const meta = JSON.parse(rawMeta);
                        sources = meta.sources || [];
                        llmModel = meta.llm_model || null;
                    }
                    catch (e) {
                        sources = [];
                        llmModel = null;
                    }
                    
                    completeText += buffer.slice(separatorIndex + 5);
                    buffer = "";
                    metaProcessed = true;
                }
                else if (!buffer.startsWith("{")) {
                    completeText += buffer;
                    buffer = "";
                    metaProcessed = true;
                }
            }
            else {
                completeText += fragment;
            }
        }

        resolveAiPlaceholder(placeholder, completeText, sources, llmModel);
    }
    catch (e) {
        placeholder.querySelector(".message-content").innerHTML =
            `<div class="markdown-body">⚠️ <strong>Error:</strong> ${e.message}</div>`;
        placeholder.removeAttribute("id");
        console.error(e);
    }
    finally {
        loader.style.display = "none";
        input.disabled = false;
        input.focus();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    Sidebar.init();
    input.focus();
    
    API.getConfig().then(data => {
        const statsContainer = document.getElementById("system-stats");
        if (statsContainer) {
            statsContainer.innerHTML = `
                <div class="stat-badge"><span>SRC</span>${data.source_dir}</div>
                <div class="stat-badge"><span>DB</span>${data.db_path}</div>
                <div class="stat-badge"><span>EMBED</span>${data.embed_model} (${data.embed_dim}d)</div>
                <div class="stat-badge"><span>CHUNK</span>${data.chunk_size} / ${data.chunk_overlap}</div>
                <div class="stat-badge"><span>TOP_K</span>${data.top_k}</div>
            `;
        }
    }).catch(err => console.error(err));

    document.getElementById("send-btn").onclick = handleAsk;
    document.getElementById("refresh-library-btn").onclick = () => Sidebar.refresh();
    input.onkeydown = (e) => { if (e.key === "Enter" && !input.disabled) handleAsk(); };
    document.getElementById("reset-btn").onclick = async () => {
        if (confirm("Wipe local AI memory?")) {
            try {
                await API.reset();
                location.reload();
            } 
            catch (err) { alert("Reset failed."); }
        }
    };
});