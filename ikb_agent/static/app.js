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
  documentsBox.innerHTML = data.documents
    .map(
      (doc) => `
        <div class="doc">
          <div>
            <strong>${escapeHtml(doc.file_title)}</strong>
            <span>${escapeHtml(doc.item_name)} · ${doc.chunk_count} chunks · ${doc.created_at}</span>
          </div>
          <span>${escapeHtml(doc.file_name)}</span>
        </div>
      `
    )
    .join("");
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files.length) {
    importResult.textContent = "请先选择一个文件。";
    return;
  }
  const form = new FormData();
  form.append("file", fileInput.files[0]);
  importResult.textContent = "正在执行导入链路...";
  try {
    const data = await api("/api/import", { method: "POST", body: form });
    importResult.textContent = `导入成功：${data.document.file_title}
商品名：${data.document.item_name}
Chunk 数量：${data.document.chunk_count}
执行链路：${data.trace.join(" -> ")}`;
    await loadDocuments();
  } catch (error) {
    importResult.textContent = `导入失败：${error.message}`;
  }
});

demoImportBtn.addEventListener("click", async () => {
  importResult.textContent = "正在导入示例文档...";
  try {
    const data = await api("/api/demo-import", { method: "POST" });
    importResult.textContent = `示例导入成功：${data.document.file_title}
商品名：${data.document.item_name}
Chunk 数量：${data.document.chunk_count}
执行链路：${data.trace.join(" -> ")}`;
    await loadDocuments();
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

loadHealth();
loadDocuments();

