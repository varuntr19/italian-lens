const els = {
  tabs: document.querySelectorAll(".tab"),
  views: document.querySelectorAll(".view"),

  photoInput: document.getElementById("photoInput"),
  workCanvas: document.getElementById("workCanvas"),

  captureEmpty: document.getElementById("captureEmpty"),
  capturePreview: document.getElementById("capturePreview"),
  previewImg: document.getElementById("previewImg"),
  retakeBtn: document.getElementById("retakeBtn"),
  analyzeBtn: document.getElementById("analyzeBtn"),

  analyzing: document.getElementById("analyzing"),
  analyzeError: document.getElementById("analyzeError"),
  results: document.getElementById("results"),
  sceneDescription: document.getElementById("sceneDescription"),
  phrasesList: document.getElementById("phrasesList"),
  vocabList: document.getElementById("vocabList"),
  doneBtn: document.getElementById("doneBtn"),

  vocabSearch: document.getElementById("vocabSearch"),
  reviewList: document.getElementById("reviewList"),
  reviewEmpty: document.getElementById("reviewEmpty"),

  historyList: document.getElementById("historyList"),
  historyEmpty: document.getElementById("historyEmpty"),

  captureDetail: document.getElementById("captureDetail"),
  closeDetailBtn: document.getElementById("closeDetailBtn"),
  detailImg: document.getElementById("detailImg"),
  detailScene: document.getElementById("detailScene"),
  detailPhrases: document.getElementById("detailPhrases"),
};

let pendingBlob = null;
let allVocabulary = [];

// ---------- Tabs ----------

function switchView(name) {
  els.tabs.forEach((t) => t.classList.toggle("active", t.dataset.view === name));
  els.views.forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  if (name === "review") loadVocabulary();
  if (name === "history") loadHistory();
}

els.tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchView(tab.dataset.view));
});

// ---------- Capture ----------

function resetCapture() {
  pendingBlob = null;
  els.photoInput.value = "";
  els.captureEmpty.hidden = false;
  els.capturePreview.hidden = true;
  els.results.hidden = true;
  els.analyzeError.hidden = true;
  els.analyzing.hidden = true;
}

els.photoInput.addEventListener("change", async () => {
  const file = els.photoInput.files[0];
  if (!file) return;

  try {
    pendingBlob = await normalizeToJpeg(file);
  } catch (err) {
    pendingBlob = file; // fall back to the raw file if canvas normalization fails
  }

  els.previewImg.src = URL.createObjectURL(pendingBlob);
  els.captureEmpty.hidden = true;
  els.capturePreview.hidden = false;
  els.results.hidden = true;
  els.analyzeError.hidden = true;
});

// Draw the captured photo onto a canvas, downscaled and re-encoded as JPEG.
// This sidesteps iOS HEIC uploads and keeps the payload small.
function normalizeToJpeg(file, maxDim = 1600) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      let { width, height } = img;
      if (width > maxDim || height > maxDim) {
        const scale = maxDim / Math.max(width, height);
        width = Math.round(width * scale);
        height = Math.round(height * scale);
      }
      const canvas = els.workCanvas;
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, width, height);
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error("toBlob failed"))),
        "image/jpeg",
        0.85
      );
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

els.retakeBtn.addEventListener("click", resetCapture);
els.doneBtn.addEventListener("click", resetCapture);

els.analyzeBtn.addEventListener("click", async () => {
  if (!pendingBlob) return;

  els.capturePreview.hidden = true;
  els.analyzing.hidden = false;
  els.analyzeError.hidden = true;

  const formData = new FormData();
  formData.append("photo", pendingBlob, "photo.jpg");

  try {
    const res = await fetch("/api/analyze", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Analysis failed.");
    renderResults(data);
  } catch (err) {
    els.analyzeError.textContent = err.message;
    els.analyzeError.hidden = false;
  } finally {
    els.analyzing.hidden = true;
  }
});

function renderResults(data) {
  els.sceneDescription.textContent = data.scene_description;

  els.phrasesList.innerHTML = "";
  data.phrases.forEach((p) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <div><span class="phrase-it">${escapeHtml(p.italian)}</span><span class="phrase-category">${escapeHtml(p.category)}</span></div>
      <div class="phrase-en">${escapeHtml(p.english)}</div>
    `;
    els.phrasesList.appendChild(li);
  });

  els.vocabList.innerHTML = "";
  data.vocabulary.forEach((v) => els.vocabList.appendChild(vocabCard(v)));

  els.results.hidden = false;
}

function vocabCard(v, { deletable = false } = {}) {
  const li = document.createElement("li");
  li.className = "vocab-card";
  li.innerHTML = `
    <div>
      <div><span class="vocab-it">${escapeHtml(v.italian)}</span><span class="vocab-pos">${escapeHtml(v.part_of_speech || "")}</span></div>
      <div class="vocab-example">${escapeHtml(v.example_it || "")}<br>${escapeHtml(v.example_en || "")}</div>
      ${deletable ? `<div class="vocab-meta">seen ${v.times_seen}×${v.deleteAffordance || ""}</div>` : ""}
    </div>
    <span class="vocab-en hidden-answer">${escapeHtml(v.english)}</span>
  `;
  li.addEventListener("click", (e) => {
    if (e.target.classList.contains("vocab-delete")) return;
    li.classList.toggle("revealed");
    li.querySelector(".vocab-en").classList.toggle("hidden-answer");
  });

  if (deletable) {
    const meta = li.querySelector(".vocab-meta");
    const del = document.createElement("button");
    del.className = "vocab-delete";
    del.textContent = "Remove";
    del.addEventListener("click", async (e) => {
      e.stopPropagation();
      await fetch(`/api/vocabulary/${v.id}`, { method: "DELETE" });
      li.remove();
    });
    meta.appendChild(del);
  }

  return li;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---------- Review ----------

async function loadVocabulary() {
  const res = await fetch("/api/vocabulary");
  allVocabulary = await res.json();
  renderVocabulary(allVocabulary);
}

function renderVocabulary(list) {
  els.reviewList.innerHTML = "";
  els.reviewEmpty.hidden = list.length > 0;
  list.forEach((v) => els.reviewList.appendChild(vocabCard(v, { deletable: true })));
}

els.vocabSearch.addEventListener("input", () => {
  const q = els.vocabSearch.value.trim().toLowerCase();
  const filtered = q
    ? allVocabulary.filter(
        (v) => v.italian.toLowerCase().includes(q) || v.english.toLowerCase().includes(q)
      )
    : allVocabulary;
  renderVocabulary(filtered);
});

// ---------- History ----------

async function loadHistory() {
  const res = await fetch("/api/captures");
  const items = await res.json();
  els.historyList.innerHTML = "";
  els.historyEmpty.hidden = items.length > 0;
  items.forEach((c) => {
    const li = document.createElement("li");
    li.className = "history-item";
    const date = new Date(c.created_at).toLocaleString();
    li.innerHTML = `
      <img src="${c.image_url}" alt="">
      <div class="history-info">
        <p class="history-scene">${escapeHtml(c.scene_description)}</p>
        <p class="history-date">${date}</p>
      </div>
    `;
    li.addEventListener("click", () => openDetail(c.id));
    els.historyList.appendChild(li);
  });
}

async function openDetail(id) {
  const res = await fetch(`/api/captures/${id}`);
  const c = await res.json();
  els.detailImg.src = c.image_url;
  els.detailScene.textContent = c.scene_description;
  els.detailPhrases.innerHTML = "";
  c.phrases.forEach((p) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <div><span class="phrase-it">${escapeHtml(p.italian)}</span><span class="phrase-category">${escapeHtml(p.category)}</span></div>
      <div class="phrase-en">${escapeHtml(p.english)}</div>
    `;
    els.detailPhrases.appendChild(li);
  });
  els.captureDetail.hidden = false;
}

els.closeDetailBtn.addEventListener("click", () => {
  els.captureDetail.hidden = true;
});
