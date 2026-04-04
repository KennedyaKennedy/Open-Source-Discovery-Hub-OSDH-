const API = "/api";
let currentPage = 1;
let currentOffset = 0;
let paginationMode = "pages";
let totalResources = 0;
let currentFilters = {};

document.addEventListener("DOMContentLoaded", () => {
    loadFilters();
    loadStats();
    loadResources();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById("search-input").addEventListener("input", debounce(() => {
        currentPage = 1;
        currentOffset = 0;
        loadResources();
    }, 300));

    document.getElementById("sort-by").addEventListener("change", () => {
        currentPage = 1;
        currentOffset = 0;
        loadResources();
    });

    document.getElementById("sort-order").addEventListener("change", () => {
        currentPage = 1;
        currentOffset = 0;
        loadResources();
    });

    document.getElementById("apply-filters").addEventListener("click", () => {
        currentPage = 1;
        currentOffset = 0;
        loadResources();
    });

    document.getElementById("clear-filters").addEventListener("click", () => {
        document.getElementById("filter-source").value = "";
        document.getElementById("filter-language").value = "";
        document.getElementById("filter-license").value = "";
        document.getElementById("filter-status").value = "";
        document.getElementById("filter-archived").checked = false;
        document.getElementById("filter-duplicate").checked = true;
        document.getElementById("filter-tags").value = "";
        currentPage = 1;
        currentOffset = 0;
        loadResources();
    });

    document.getElementById("prev-page").addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            currentOffset = (currentPage - 1) * 50;
            loadResources();
        }
    });

    document.getElementById("next-page").addEventListener("click", () => {
        currentPage++;
        currentOffset = (currentPage - 1) * 50;
        loadResources();
    });

    document.getElementById("load-more").addEventListener("click", () => {
        currentOffset += 50;
        loadResources(true);
    });

    document.getElementById("view-grid").addEventListener("click", () => {
        document.getElementById("view-grid").classList.add("active");
        document.getElementById("view-list").classList.remove("active");
        document.getElementById("results").className = "results-grid";
    });

    document.getElementById("view-list").addEventListener("click", () => {
        document.getElementById("view-list").classList.add("active");
        document.getElementById("view-grid").classList.remove("active");
        document.getElementById("results").className = "results-list";
    });

    document.getElementById("pagination-mode").addEventListener("click", () => {
        const btn = document.getElementById("pagination-mode");
        if (paginationMode === "pages") {
            paginationMode = "infinite";
            btn.textContent = "Mode: Infinite";
            document.getElementById("pagination").style.display = "none";
            document.getElementById("infinite-scroll").style.display = "flex";
        } else {
            paginationMode = "pages";
            btn.textContent = "Mode: Pages";
            document.getElementById("pagination").style.display = "flex";
            document.getElementById("infinite-scroll").style.display = "none";
        }
    });

    document.getElementById("modal-close").addEventListener("click", closeModal);
    document.getElementById("modal").addEventListener("click", (e) => {
        if (e.target.id === "modal") closeModal();
    });

    document.getElementById("aggregate-github").addEventListener("click", () => runAggregate("github"));
    document.getElementById("aggregate-awesome").addEventListener("click", () => runAggregate("awesome"));
    document.getElementById("aggregate-edu").addEventListener("click", () => runAggregate("educational"));
    document.getElementById("aggregate-all").addEventListener("click", () => runAggregate("all"));
    document.getElementById("run-ai").addEventListener("click", runAI);
    document.getElementById("create-snapshot").addEventListener("click", createSnapshot);
}

function getFilters() {
    return {
        q: document.getElementById("search-input").value,
        source_type: document.getElementById("filter-source").value,
        language: document.getElementById("filter-language").value,
        license: document.getElementById("filter-license").value,
        maintenance_status: document.getElementById("filter-status").value,
        is_archived: document.getElementById("filter-archived").checked ? false : null,
        is_duplicate: document.getElementById("filter-duplicate").checked ? false : null,
        tags: document.getElementById("filter-tags").value || null,
        sort: document.getElementById("sort-by").value,
        order: document.getElementById("sort-order").value,
        limit: 50,
        offset: paginationMode === "pages" ? currentOffset : currentOffset,
    };
}

async function loadResources(append = false) {
    const filters = getFilters();
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
        if (v !== null && v !== "") params.append(k, v);
    });

    try {
        const resp = await fetch(`${API}/resources?${params}`);
        const data = await resp.json();
        totalResources = data.total;

        if (append) {
            renderResources(data.resources, true);
        } else {
            renderResources(data.resources, false);
        }

        updatePagination(data.total, data.limit, data.offset);
    } catch (e) {
        showToast("Failed to load resources");
    }
}

function renderResources(resources, append = false) {
    const container = document.getElementById("results");
    if (!append) container.innerHTML = "";

    if (resources.length === 0 && !append) {
        container.innerHTML = '<div class="empty-state">No resources found. Try aggregating some sources!</div>';
        return;
    }

    resources.forEach(r => {
        const card = document.createElement("div");
        card.className = "resource-card";
        card.innerHTML = `
            <h3>${escapeHtml(r.name)}</h3>
            <p class="description">${escapeHtml(r.description || "No description")}</p>
            <div class="meta">
                <span class="status-badge status-${r.maintenance_status}">${r.maintenance_status}</span>
                <span>★ ${r.stars}</span>
                <span>⑂ ${r.forks}</span>
                ${r.language ? `<span>${r.language}</span>` : ""}
                ${r.license ? `<span>${r.license}</span>` : ""}
                <span>${r.source_type}</span>
            </div>
            ${r.ai_tags && r.ai_tags.length ? `
                <div class="tags">
                    ${r.ai_tags.slice(0, 5).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
                </div>
            ` : ""}
        `;
        card.addEventListener("click", () => showResourceDetail(r));
        container.appendChild(card);
    });
}

function updatePagination(total, limit, offset) {
    if (paginationMode === "pages") {
        const totalPages = Math.ceil(total / limit);
        document.getElementById("page-info").textContent = `Page ${currentPage} of ${totalPages || 1}`;
        document.getElementById("prev-page").disabled = currentPage <= 1;
        document.getElementById("next-page").disabled = currentPage >= totalPages;
    }
}

async function loadFilters() {
    try {
        const resp = await fetch(`${API}/filters`);
        const data = await resp.json();

        const sourceSelect = document.getElementById("filter-source");
        data.source_types.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s;
            opt.textContent = s;
            sourceSelect.appendChild(opt);
        });

        const langSelect = document.getElementById("filter-language");
        data.languages.forEach(l => {
            const opt = document.createElement("option");
            opt.value = l;
            opt.textContent = l;
            langSelect.appendChild(opt);
        });

        const licSelect = document.getElementById("filter-license");
        data.licenses.forEach(l => {
            const opt = document.createElement("option");
            opt.value = l;
            opt.textContent = l;
            licSelect.appendChild(opt);
        });
    } catch (e) {
        console.error("Failed to load filters:", e);
    }
}

async function loadStats() {
    try {
        const resp = await fetch(`${API}/stats`);
        const data = await resp.json();

        const container = document.getElementById("stats-content");
        container.innerHTML = `
            <div class="stat-row"><span class="stat-label">Total</span><span class="stat-value">${data.total}</span></div>
            <div class="stat-row"><span class="stat-label">Active</span><span class="stat-value" style="color:var(--success)">${data.by_status.active}</span></div>
            <div class="stat-row"><span class="stat-label">Maintained</span><span class="stat-value" style="color:var(--accent)">${data.by_status.maintained}</span></div>
            <div class="stat-row"><span class="stat-label">Stale</span><span class="stat-value" style="color:var(--warning)">${data.by_status.stale}</span></div>
            <div class="stat-row"><span class="stat-label">Archived</span><span class="stat-value" style="color:var(--danger)">${data.by_status.archived}</span></div>
        `;
    } catch (e) {
        document.getElementById("stats-content").innerHTML = "<p>Failed to load stats</p>";
    }
}

async function showResourceDetail(resource) {
    try {
        const resp = await fetch(`${API}/resources/${resource.id}`);
        const r = await resp.json();

        const body = document.getElementById("modal-body");
        body.innerHTML = `
            <h2>${escapeHtml(r.name)}</h2>
            <p style="color:var(--text-secondary);margin-bottom:1rem;">${escapeHtml(r.url)}</p>
            <p style="margin-bottom:1rem;">${escapeHtml(r.description || "No description")}</p>
            ${r.readme_summary ? `
                <div style="background:var(--bg-tertiary);padding:1rem;border-radius:8px;margin-bottom:1rem;">
                    <h4 style="margin-bottom:0.5rem;">AI Summary</h4>
                    <p>${escapeHtml(r.readme_summary)}</p>
                </div>
            ` : ""}
            <div class="meta" style="margin-bottom:1rem;">
                <span class="status-badge status-${r.maintenance_status}">${r.maintenance_status}</span>
                <span>★ ${r.stars}</span>
                <span>⑂ ${r.forks}</span>
                ${r.language ? `<span>${r.language}</span>` : ""}
                ${r.license ? `<span>${r.license}</span>` : ""}
            </div>
            ${r.ai_tags && r.ai_tags.length ? `
                <div class="tags" style="margin-bottom:1rem;">
                    ${r.ai_tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
                </div>
            ` : ""}
            ${r.topics && r.topics.length ? `
                <div class="tags">
                    ${r.topics.map(t => `<span class="tag" style="color:var(--accent)">${escapeHtml(t)}</span>`).join("")}
                </div>
            ` : ""}
        `;
        document.getElementById("modal").style.display = "flex";
    } catch (e) {
        showToast("Failed to load resource details");
    }
}

function closeModal() {
    document.getElementById("modal").style.display = "none";
}

async function runAggregate(source) {
    showToast(`Starting ${source} aggregation...`);
    try {
        const resp = await fetch(`${API}/aggregate/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source, run_ai: true }),
        });
        const data = await resp.json();
        showToast(`Found: ${data.resources_found}, Added: ${data.resources_added}, Updated: ${data.resources_updated}`);
        loadResources();
        loadStats();
    } catch (e) {
        showToast("Aggregation failed");
    }
}

async function runAI() {
    showToast("Starting AI processing...");
    try {
        await fetch(`${API}/aggregate/ai-process`, { method: "POST" });
        showToast("AI processing started in background");
    } catch (e) {
        showToast("AI processing failed");
    }
}

async function createSnapshot() {
    showToast("Creating snapshot...");
    try {
        const resp = await fetch(`${API}/snapshots/create?format=all`, { method: "POST" });
        const data = await resp.json();
        showToast(`Snapshot created: ${data.resource_count} resources`);
    } catch (e) {
        showToast("Snapshot creation failed");
    }
}

function showToast(message) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.style.display = "block";
    setTimeout(() => { toast.style.display = "none"; }, 3000);
}

function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
