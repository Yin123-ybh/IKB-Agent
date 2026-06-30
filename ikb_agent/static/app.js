const healthStatus = document.querySelector("#healthStatus");
const uploadForm = document.querySelector("#uploadForm");
const fileInput = document.querySelector("#fileInput");
const importResult = document.querySelector("#importResult");
const queryForm = document.querySelector("#queryForm");
const queryInput = document.querySelector("#queryInput");
const answerBox = document.querySelector("#answerBox");
const demoImportBtn = document.querySelector("#demoImportBtn");
const documentsBox = document.querySelector("#documents");
const docCount = document.querySelector("#docCount");
const tasksBox = document.querySelector("#tasks");
const taskCount = document.querySelector("#taskCount");
const fileName = document.querySelector("#fileName");
const parseModeInputs = document.querySelectorAll('input[name="parseMode"]');
const modeCards = document.querySelectorAll("[data-mode-card]");

const parseModeLabels = {
  pypdf: "轻量版 pypdf",
  mineru: "增强版 MinerU",
};

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json();
}

async function loadHealth() {
  try {
    const data = await api("/api/health");
    healthStatus.textContent = `${data.status.toUpperCase()} · ${data.mode}`;
  } catch (error) {
    healthStatus.textContent = "服务未连接";
  }
}

async function loadDocuments() {
  const data = await api("/api/documents");
  docCount.textContent = `${data.documents.length} 个文档`;
  if (!data.documents.length) {
    documentsBox.innerHTML = `<div class="empty">暂无文档，先导入一份资料。</div>`;
    return;
  }
  documentsBox.innerHTML = data.documents
    .map(
      (doc) => `
        <div class="doc">
          <div>
            <strong>${escapeHtml(doc.file_title)}</strong>
            <span>${escapeHtml(doc.item_name)} · ${doc.chunk_count} chunks · ${doc.created_at}</span>
          </div>
          <span class="file-tag">${escapeHtml(doc.file_name)}</span>
        </div>
      `
    )
    .join("");
}

async function loadTasks() {
  const data = await api("/api/tasks");
  taskCount.textContent = `${data.tasks.length} 个任务`;
  if (!data.tasks.length) {
    tasksBox.innerHTML = `<div class="empty">暂无导入任务。</div>`;
    return;
  }
  tasksBox.innerHTML = data.tasks
    .map(
      (task) => `
        <div class="task">
          <div>
            <strong>${escapeHtml(task.file_name)}</strong>
            <span>${escapeHtml(task.parse_mode || "pypdf")} · ${task.progress}% · ${escapeHtml(task.message)} · ${escapeHtml(task.trace.join(" -> "))}</span>
          </div>
          <span class="badge ${task.status === "failed" ? "failed" : ""} ${task.status === "processing" ? "processing" : ""}">${escapeHtml(task.status)}</span>
        </div>
      `
    )
    .join("");
}

parseModeInputs.forEach((input) => {
  input.addEventListener("change", syncParseModeCards);
});

fileInput.addEventListener("change", () => {
  fileName.textContent = fileInput.files.length ? fileInput.files[0].name : "选择一个知识文档";
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files.length) {
    importResult.textContent = "请先选择一个文件。";
    return;
  }
  const parseMode = getSelectedParseMode();
  const form = new FormData();
  form.append("file", fileInput.files[0]);
  form.append("parse_mode", parseMode);
  importResult.textContent = `正在执行导入链路...
前端选择：${parseModeLabels[parseMode]}
后端模式：${parseMode}`;
  try {
    const data = await api("/api/import", { method: "POST", body: form });
    importResult.textContent = `${data.message.includes("warnings") ? "导入完成但有警告" : "导入成功"}：${data.document.file_title}
前端选择：${parseModeLabels[parseMode]}
商品名：${data.document.item_name}
Chunk 数量：${data.document.chunk_count}
提示：${data.message}
执行链路：${data.trace.join(" -> ")}`;
    await loadDocuments();
    await loadTasks();
  } catch (error) {
    importResult.textContent = `导入失败：${error.message}`;
  }
});

demoImportBtn.addEventListener("click", async () => {
  const parseMode = getSelectedParseMode();
  importResult.textContent = `正在导入示例文档...
前端选择：${parseModeLabels[parseMode]}`;
  try {
    const data = await api("/api/demo-import", { method: "POST" });
    importResult.textContent = `示例导入成功：${data.document.file_title}
前端选择：${parseModeLabels[parseMode]}
商品名：${data.document.item_name}
Chunk 数量：${data.document.chunk_count}
执行链路：${data.trace.join(" -> ")}`;
    await loadDocuments();
    await loadTasks();
  } catch (error) {
    importResult.textContent = `示例导入失败：${error.message}`;
  }
});

queryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) {
    answerBox.textContent = "请输入问题。";
    return;
  }
  answerBox.textContent = "正在检索...";
  try {
    const data = await api("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: 5 }),
    });
    const hits = data.hits
      .map(
        (hit) => `
          <div class="hit">
            <strong>${escapeHtml(hit.title)}</strong>
            <div>${escapeHtml(hit.item_name)} · ${escapeHtml(hit.file_title)} · score=${hit.score}</div>
            <p>${escapeHtml(hit.content.slice(0, 260))}</p>
          </div>
        `
      )
      .join("");
    answerBox.innerHTML = `<div>${escapeHtml(data.answer)}</div>${hits}`;
  } catch (error) {
    answerBox.textContent = `查询失败：${error.message}`;
  }
});

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getSelectedParseMode() {
  return document.querySelector('input[name="parseMode"]:checked')?.value || "pypdf";
}

function syncParseModeCards() {
  const selected = getSelectedParseMode();
  modeCards.forEach((card) => {
    card.classList.toggle("selected", card.dataset.modeCard === selected);
  });
}

syncParseModeCards();
loadHealth();
loadDocuments();
loadTasks();
