export const API = {
    async *queryStream(payload) {
        const response = await fetch("/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            let errorMessage = "Server unreachable";
            try {
                const errData = await response.json();
                errorMessage = errData.error || errData.detail || `HTTP Error ${response.status}`;
            }
            catch (_) {}
            throw new Error(errorMessage);
        }

        const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            yield value;
        }
    },

    async reset() {
        const response = await fetch("/reset", { method: "POST" });
        return await response.json();
    },

    async getIndexedFiles() {
        const response = await fetch('/indexed-files');
        if (!response.ok) {
            let errorMessage = "Failed to fetch library";
            try {
                const errData = await response.json();
                errorMessage = errData.error || errData.detail || `HTTP Error ${response.status}`;
            }
            catch (_) {}
            throw new Error(errorMessage);
        }
        return await response.json();
    },

    async getConfig() {
        const response = await fetch('/config');
        if (!response.ok) {
            throw new Error("Failed to fetch config");
        }
        return await response.json();
    }
};