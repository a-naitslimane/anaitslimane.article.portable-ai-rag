import { API } from './api.js';

export const Sidebar = {
    init() {
        this.setupResizer();
        this.refresh();
    },

    async refresh() {
        const listElement = document.getElementById('file-list');
        const countElement = document.getElementById('file-count');
        if (!listElement) return;

        try {
            const data = await API.getIndexedFiles();
            const files = data.files || [];
            
            countElement.innerText = `${files.length} files`;

            if (files.length === 0) {
                listElement.innerHTML = '<li class="file-node" style="padding-left:15px">No files indexed</li>';
                return;
            }

            const tree = this.buildTree(files);
            listElement.innerHTML = ""; 
            this.renderTree(tree, listElement);
        }
        catch (error) {
            console.error("Sidebar Refresh Error:", error);
            listElement.innerHTML = `<li class="file-node" style="color:red; padding-left:15px">${error.message}</li>`;
        }
    },

    buildTree(files) {
        const tree = {};
        files.forEach((path) => {
            const parts = path.split("/");
            let current = tree;
            parts.forEach((part, index) => {
                if (!current[part]) {
                    current[part] = (index === parts.length - 1) ? null : {};
                }
                current = current[part];
            });
        });
        return tree;
    },

    renderTree(node, container, depth = 0) {
        const sortedKeys = Object.keys(node).sort((a, b) => {
            if (node[a] && !node[b]) return -1; // Folders first
            if (!node[a] && node[b]) return 1;
            return a.localeCompare(b);
        });

        sortedKeys.forEach((key) => {
            const li = document.createElement("li");
            const indent = depth * 22;
            
            if (node[key] === null) {
                li.className = "file-node";
                li.innerHTML = `<span>📄 ${key}</span>`;
                li.style.paddingLeft = `${indent + 25}px`;
            }
            else {
                li.className = "folder-node";
                li.innerHTML = `<span>📁 ${key}</span>`;
                li.style.paddingLeft = `${indent + 10}px`;
                container.appendChild(li);
                this.renderTree(node[key], container, depth + 1);
                return;
            }
            container.appendChild(li);
        });
    },

    setupResizer() {
        const sidebar = document.getElementById("library-sidebar");
        const resizer = document.getElementById("sidebar-resizer");
        const mainContent = document.getElementById("main-content");

        if (!resizer || !sidebar || !mainContent) return;

        const resize = (e) => {
            const newWidth = e.clientX;
            if (newWidth > 180 && newWidth < 600) {
                sidebar.style.width = `${newWidth}px`;
                mainContent.style.marginLeft = `${newWidth}px`;
            }
        };

        const stopResize = () => {
            document.removeEventListener("mousemove", resize);
            document.removeEventListener("mouseup", stopResize);
            document.body.style.cursor = 'default';
        };

        resizer.addEventListener("mousedown", (e) => {
            e.preventDefault();
            document.body.style.cursor = 'col-resize';
            document.addEventListener("mousemove", resize);
            document.addEventListener("mouseup", stopResize);
        });
    }
};