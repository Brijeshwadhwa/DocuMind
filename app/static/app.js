let currentToken = localStorage.getItem("token") || "";
let currentDocId = null;
let pollTimer = null;
let currentTab = "questions";

// DOM Elements
const authDot = document.getElementById("authDot");
const authUserLabel = document.getElementById("authUserLabel");
const btnQuickLogin = document.getElementById("btnQuickLogin");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const progressSection = document.getElementById("progressSection");
const progressFill = document.getElementById("progressFill");
const progressPercent = document.getElementById("progressPercent");
const progressLabel = document.getElementById("progressLabel");
const statQuestions = document.getElementById("statQuestions");
const statAnswered = document.getElementById("statAnswered");
const statReview = document.getElementById("statReview");
const statStatus = document.getElementById("statStatus");
const questionsList = document.getElementById("questionsList");
const reviewItemsList = document.getElementById("reviewItemsList");
const answersMatrixList = document.getElementById("answersMatrixList");
const rawJsonBox = document.getElementById("rawJsonBox");
const docsListContainer = document.getElementById("docsListContainer");
const tabCountQuestions = document.getElementById("tabCountQuestions");
const tabCountReview = document.getElementById("tabCountReview");
const btnLinkRelationship = document.getElementById("btnLinkRelationship");

// Initialization
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  setupDropzone();
  await ensureAuthentication();
  await fetchDocumentsList();
});

// Authentication
async function ensureAuthentication() {
  if (currentToken) {
    try {
      const res = await fetch("/auth/me", {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAuthenticated(data.email);
        return;
      }
    } catch (e) {
      console.warn("Existing token expired or invalid:", e);
    }
  }
  await quickLogin();
}

async function quickLogin() {
  const email = "candidate@pragatibharti.in";
  const password = "SecurePassword2026!";
  authUserLabel.textContent = "Authenticating...";

  try {
    // Try register
    await fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
  } catch (e) {}

  try {
    // Login
    const res = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (res.ok) {
      const data = await res.json();
      currentToken = data.access_token;
      localStorage.setItem("token", currentToken);
      setAuthenticated(email);
    } else {
      authUserLabel.textContent = "Auth Required";
      authDot.style.background = "var(--accent-amber)";
    }
  } catch (err) {
    authUserLabel.textContent = "Offline";
    authDot.style.background = "var(--accent-rose)";
  }
}

btnQuickLogin.addEventListener("click", quickLogin);

function setAuthenticated(email) {
  authDot.style.background = "var(--accent-emerald)";
  authUserLabel.textContent = email;
}

// Dropzone Setup
function setupDropzone() {
  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      uploadFile(e.target.files[0]);
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });
}

// Upload File
async function uploadFile(file) {
  if (!currentToken) {
    alert("Please log in first.");
    return;
  }

  showProgress("Uploading " + file.name + "...", 15);
  statStatus.textContent = "UPLOADING";
  statStatus.style.color = "var(--accent-amber)";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/documents/upload", {
      method: "POST",
      headers: { Authorization: `Bearer ${currentToken}` },
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      alert("Upload failed (" + res.status + "): " + (err.detail || "Error"));
      hideProgress();
      statStatus.textContent = "FAILED";
      statStatus.style.color = "var(--accent-rose)";
      return;
    }

    const data = await res.json();
    currentDocId = data.document_id;
    showProgress("Document queued. Processing pipeline active...", 35);
    statStatus.textContent = "PROCESSING";
    statStatus.style.color = "var(--accent-cyan)";

    startPolling(currentDocId);
    fetchDocumentsList();
  } catch (err) {
    alert("Network error uploading file: " + err.message);
    hideProgress();
  }
}

// 1-Click Sample Document Loader
async function loadSampleDoc(filename) {
  showProgress("Loading sample document: " + filename, 10);
  try {
    const res = await fetch("/samples/" + filename);
    if (!res.ok) {
      throw new Error("Sample file endpoint not found");
    }
    const blob = await res.blob();
    const file = new File([blob], filename, { type: blob.type || "application/pdf" });
    await uploadFile(file);
  } catch (err) {
    alert("Could not load sample file: " + err.message);
    hideProgress();
  }
}

// Status Polling
function startPolling(docId) {
  if (pollTimer) clearInterval(pollTimer);

  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/documents/${docId}/status`, {
        headers: { Authorization: `Bearer ${currentToken}` }
      });
      if (!res.ok) return;

      const data = await res.json();
      const progress = Math.max(data.progress || 0, 20);
      showProgress(`Processing Document (${data.status})...`, progress);

      if (data.status === "COMPLETED" || data.status === "FAILED") {
        clearInterval(pollTimer);
        pollTimer = null;
        showProgress("Processing Complete!", 100);
        setTimeout(hideProgress, 1200);

        statStatus.textContent = data.status;
        statStatus.style.color = data.status === "COMPLETED" ? "var(--accent-emerald)" : "var(--accent-rose)";

        await loadDocumentResults(docId);
        await fetchDocumentsList();
      }
    } catch (e) {
      console.error("Polling error:", e);
    }
  }, 1000);
}

function showProgress(label, percent) {
  progressSection.style.display = "block";
  progressLabel.textContent = label;
  progressPercent.textContent = percent + "%";
  progressFill.style.width = percent + "%";
}

function hideProgress() {
  progressSection.style.display = "none";
}

// Load Questions, Answers & Review Items
async function loadDocumentResults(docId) {
  try {
    // 1. Questions
    const qRes = await fetch(`/documents/${docId}/questions`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });
    const qData = qRes.ok ? await qRes.json() : { questions: [] };

    // 2. Answers
    const aRes = await fetch(`/documents/${docId}/answers`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });
    const aData = aRes.ok ? await aRes.json() : { answers: [], answered_count: 0 };

    // 3. Review Items
    const rRes = await fetch(`/documents/${docId}/review-items`, {
      headers: { Authorization: `Bearer ${currentToken}` }
    });
    const rData = rRes.ok ? await rRes.json() : { review_items: [] };

    // Update stats
    statQuestions.textContent = qData.questions.length;
    statAnswered.textContent = aData.answered_count || 0;
    statReview.textContent = rData.review_items.length;
    tabCountQuestions.textContent = qData.questions.length;
    tabCountReview.textContent = rData.review_items.length;

    // Render tabs
    renderQuestions(qData.questions);
    renderReviewItems(rData.review_items);
    renderAnswers(aData);

    rawJsonBox.textContent = JSON.stringify({
      document_id: docId,
      status: "COMPLETED",
      questions: qData.questions,
      answers: aData,
      review_items: rData.review_items
    }, null, 2);

  } catch (err) {
    console.error("Error loading document results:", err);
  }
}

// Render Questions
function renderQuestions(questions) {
  if (!questions || questions.length === 0) {
    questionsList.innerHTML = `
      <div style="text-align: center; padding: 3rem; color: var(--text-dim);">
        No questions extracted for this document. Check the Review Items tab for warnings.
      </div>`;
    return;
  }

  questionsList.innerHTML = questions.map((q) => {
    const isMultiPage = q.source_pages && q.source_pages.length > 1;
    const pageBadgeText = isMultiPage ? `Pages ${q.source_pages.join(", ")} (Spanning)` : `Page ${q.source_pages ? q.source_pages[0] : 1}`;

    const confVal = q.extraction_confidence || 0.0;
    const confClass = confVal >= 0.90 ? "conf-high" : (confVal >= 0.70 ? "conf-med" : "conf-low");

    // Options HTML
    let optionsHtml = "";
    if (q.options && Object.keys(q.options).length > 0) {
      optionsHtml = `<div class="options-grid">` +
        Object.entries(q.options).map(([key, val]) => {
          const isCorrect = q.answer && q.answer.toUpperCase() === key.toUpperCase();
          return `
            <div class="option-tile ${isCorrect ? 'is-correct' : ''}">
              <span class="option-key">${key}</span>
              <span>${val}</span>
            </div>
          `;
        }).join("") +
      `</div>`;
    }

    return `
      <article class="question-card">
        <div class="question-meta-row">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <span class="badge-qnum">Question ${q.question_number}</span>
            <span class="badge-type">${q.question_type}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="badge-pages">${pageBadgeText}</span>
            <span class="conf-pill ${confClass}">Conf: ${Math.round(confVal * 100)}%</span>
          </div>
        </div>

        <div class="question-prompt">${q.question || q.question_text}</div>

        ${optionsHtml}

        <div class="question-footer-row">
          <div>
            ${q.answer ? `<span style="color: var(--accent-emerald); font-weight: 600;">✓ Correct Answer: Option ${q.answer}</span> <span style="font-size: 0.72rem; color: var(--text-dim);">(${Math.round((q.answer_confidence || 0.95) * 100)}% Match)</span>` : `<span style="color: var(--text-dim);">Answer Unmatched</span>`}
          </div>
          <button class="btn btn-secondary btn-sm" onclick="toggleTrace('trace_${q.id}')">View Source Text</button>
        </div>

        <div id="trace_${q.id}" class="trace-box">
${q.source_text || "No raw text recorded"}
        </div>
      </article>
    `;
  }).join("");
}

function toggleTrace(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.display = el.style.display === "none" ? "block" : "none";
  }
}

// Render Review Items
function renderReviewItems(items) {
  if (!items || items.length === 0) {
    reviewItemsList.innerHTML = `
      <div class="glass-card" style="text-align: center; padding: 2rem; color: var(--accent-emerald); font-weight: 600;">
        ✓ Zero extraction warnings! Document parsed with high fidelity.
      </div>`;
    return;
  }

  reviewItemsList.innerHTML = items.map(item => `
    <div class="review-card">
      <div>
        <div class="review-type">${item.issue_type}</div>
        <div class="review-msg">${item.message}</div>
      </div>
      <div style="text-align: right;">
        <span class="conf-pill conf-low">${item.status}</span>
        ${item.confidence ? `<div style="font-size: 0.72rem; color: var(--text-dim); margin-top: 0.2rem;">Conf: ${Math.round(item.confidence * 100)}%</div>` : ''}
      </div>
    </div>
  `).join("");
}

// Render Answer Key Matrix
function renderAnswers(data) {
  if (!data.answers || data.answers.length === 0) {
    answersMatrixList.innerHTML = `<div style="text-align: center; color: var(--text-dim);">No answer keys found.</div>`;
    return;
  }

  answersMatrixList.innerHTML = `
    <div style="margin-bottom: 1rem; font-weight: 600;">
      Answer Summary (${data.answered_count} / ${data.total_questions} Answered)
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.75rem;">
      ${data.answers.map(a => `
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 0.75rem; text-align: center; box-shadow: var(--shadow-subtle);">
          <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 500;">Question ${a.question_number}</div>
          <div style="font-size: 1.3rem; font-weight: 700; color: ${a.answer ? 'var(--accent-emerald)' : 'var(--text-dim)'}; margin: 0.2rem 0;">
            ${a.answer || "—"}
          </div>
          <div style="font-size: 0.7rem; color: var(--text-dim);">
            ${a.answer ? `Conf: ${Math.round((a.answer_confidence || 0.95) * 100)}%` : 'Missing Key'}
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

// Documents List
async function fetchDocumentsList() {
  if (!currentToken) return;
  try {
    const res = await fetch("/documents?page=1&limit=10", {
      headers: { Authorization: `Bearer ${currentToken}` }
    });
    if (!res.ok) return;

    const data = await res.json();
    if (!data.documents || data.documents.length === 0) {
      docsListContainer.innerHTML = `<div style="font-size: 0.8rem; color: var(--text-dim); text-align: center; padding: 1rem;">No documents uploaded yet.</div>`;
      return;
    }

    docsListContainer.innerHTML = data.documents.map(d => `
      <div onclick="selectDocument('${d.id}')" class="doc-list-item">
        <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 180px; font-weight: 500;">${d.filename}</span>
        <span style="font-size: 0.7rem; font-weight: 600; color: ${d.status === 'COMPLETED' ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">${d.status}</span>
      </div>
    `).join("");
  } catch (e) {
    console.error("Failed to fetch documents list:", e);
  }
}

async function selectDocument(docId) {
  currentDocId = docId;
  statStatus.textContent = "LOADING";
  await loadDocumentResults(docId);
  statStatus.textContent = "COMPLETED";
  statStatus.style.color = "var(--accent-emerald)";
}

// Multi-Document Relationship linking
btnLinkRelationship.addEventListener("click", async () => {
  if (!currentToken) return;
  btnLinkRelationship.textContent = "Uploading & Linking...";

  try {
    // 1. Upload Question Paper 05a
    const resA = await fetch("/samples/05a_question_paper_only.pdf");
    const blobA = await resA.blob();
    const fileA = new File([blobA], "05a_question_paper_only.pdf", { type: "application/pdf" });
    const formA = new FormData();
    formA.append("file", fileA);

    const upA = await fetch("/documents/upload", {
      method: "POST",
      headers: { Authorization: `Bearer ${currentToken}` },
      body: formA
    });
    const dataA = await upA.json();

    // 2. Upload Answer Key 05b
    const resB = await fetch("/samples/05b_separate_answer_key.pdf");
    const blobB = await resB.blob();
    const fileB = new File([blobB], "05b_separate_answer_key.pdf", { type: "application/pdf" });
    const formB = new FormData();
    formB.append("file", fileB);

    const upB = await fetch("/documents/upload", {
      method: "POST",
      headers: { Authorization: `Bearer ${currentToken}` },
      body: formB
    });
    const dataB = await upB.json();

    // 3. Establish Relationship
    const relRes = await fetch(`/documents/${dataA.document_id}/relationships`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${currentToken}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        related_document_id: dataB.document_id,
        relationship_type: "ANSWER_KEY"
      })
    });

    if (relRes.ok) {
      alert("Success! Linked Answer Key (05b) to Question Paper (05a). Answers have been associated!");
      await selectDocument(dataA.document_id);
    } else {
      alert("Relationship linking failed.");
    }
  } catch (err) {
    alert("Error linking relationship: " + err.message);
  } finally {
    btnLinkRelationship.textContent = "🔗 Link 5b (Answer Key) → 5a (Question Paper)";
  }
});

// Tab Switcher
function switchTab(tabName) {
  currentTab = tabName;
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.getElementById("tabQuestions").style.display = tabName === "questions" ? "block" : "none";
  document.getElementById("tabReview").style.display = tabName === "review" ? "block" : "none";
  document.getElementById("tabAnswers").style.display = tabName === "answers" ? "block" : "none";
  document.getElementById("tabJson").style.display = tabName === "json" ? "block" : "none";

  const activeIndex = ["questions", "review", "answers", "json"].indexOf(tabName);
  if (activeIndex >= 0) {
    document.querySelectorAll(".tab-btn")[activeIndex].classList.add("active");
  }
}

// Theme Switcher & Persistence
function initTheme() {
  const savedTheme = localStorage.getItem("theme") || "light";
  applyTheme(savedTheme);

  const btnThemeToggle = document.getElementById("btnThemeToggle");
  if (btnThemeToggle) {
    btnThemeToggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const next = current === "light" ? "dark" : "light";
      applyTheme(next);
      localStorage.setItem("theme", next);
    });
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const themeIcon = document.getElementById("themeIcon");
  const themeLabel = document.getElementById("themeLabel");
  if (themeIcon && themeLabel) {
    if (theme === "dark") {
      themeIcon.textContent = "🌙";
      themeLabel.textContent = "Dark";
    } else {
      themeIcon.textContent = "☀️";
      themeLabel.textContent = "Light";
    }
  }
}
