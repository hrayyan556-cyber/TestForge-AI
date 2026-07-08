const state = {
  token: localStorage.getItem("qa_token") || "",
  user: null,
  projects: [],
  selectedProjectId: null,
  requirements: [],
  selectedRequirementId: null,
  testCases: [],
  analytics: null,
  llmStatus: null,
  historySummary: null,
};

const TEST_TYPES = ["Functional", "Negative", "Boundary", "Validation", "UI", "API", "Security", "Performance"];
const PRIORITIES = ["Low", "Medium", "High", "Critical"];
const SEVERITIES = ["Minor", "Major", "Critical", "Blocker"];
const STATUSES = ["Draft", "Needs Review", "Approved", "Deprecated"];
const CHART_COLORS = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#fb7185", "#60a5fa", "#f472b6", "#2dd4bf"];

const el = (id) => document.getElementById(id);
const authView = el("authView");
const appView = el("appView");
const userBox = el("userBox");
const statusText = el("status");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showStatus(message, isError = false) {
  statusText.textContent = message || "";
  statusText.style.color = isError ? "#fb7185" : "#38bdf8";
}

function authHeaders(extra = {}) {
  return {
    ...extra,
    Authorization: `Bearer ${state.token}`,
  };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    if (response.status === 401 && state.token) setLoggedOut();
    let message = "Request failed";
    try {
      const error = await response.json();
      message = error.detail || message;
    } catch (_) {}
    throw new Error(message);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return response.json();
  return response.text();
}

function setLoggedIn(user) {
  state.user = user;
  authView.classList.add("hidden");
  appView.classList.remove("hidden");
  userBox.classList.remove("hidden");
  el("userName").textContent = user ? `${user.name}` : "";
}

function setLoggedOut() {
  state.token = "";
  state.user = null;
  state.projects = [];
  state.requirements = [];
  state.testCases = [];
  state.selectedProjectId = null;
  state.selectedRequirementId = null;
  localStorage.removeItem("qa_token");
  renderLlmStatus(null);
  renderHistorySummary(null);
  authView.classList.remove("hidden");
  appView.classList.add("hidden");
  userBox.classList.add("hidden");
}

async function bootstrap() {
  renderDashboardPlaceholder();
  if (!state.token) return setLoggedOut();
  try {
    const user = await api("/api/auth/me");
    setLoggedIn(user);
    await loadProjects();
    await loadLlmStatus();
    await loadHistorySummary();
  } catch (_) {
    setLoggedOut();
  }
}

function selectedTestTypes() {
  return Array.from(document.querySelectorAll(".checkbox-group input:checked")).map((box) => box.value);
}

function resetRequirementState() {
  state.requirements = [];
  state.selectedRequirementId = null;
  state.testCases = [];
  renderRequirements();
  renderTable();
}

async function selectProject(projectId) {
  const nextId = Number(projectId);
  if (!nextId) {
    state.selectedProjectId = null;
    resetRequirementState();
    renderDashboardPlaceholder();
    return;
  }

  const changed = state.selectedProjectId !== nextId;
  state.selectedProjectId = nextId;
  if (changed) resetRequirementState();

  if (el("projectSelect").value !== String(nextId)) el("projectSelect").value = String(nextId);
  const project = state.projects.find((p) => p.id === state.selectedProjectId);
  el("selectedProjectLabel").textContent = project ? project.name : "No project selected";
  renderProjects();
  await loadProjectAnalytics();
  await loadRequirements();
}

async function loadProjects() {
  state.projects = await api("/api/projects");
  renderProjectSelect();
  renderProjects();

  if (state.projects.length) {
    const stillExists = state.projects.some((project) => project.id === state.selectedProjectId);
    await selectProject(stillExists ? state.selectedProjectId : state.projects[0].id);
  } else {
    state.selectedProjectId = null;
    el("projectSelect").innerHTML = `<option value="">Create a project first</option>`;
    el("selectedProjectLabel").textContent = "No project selected";
    resetRequirementState();
    renderDashboardPlaceholder();
  }
}

function renderProjectSelect() {
  if (!state.projects.length) {
    el("projectSelect").innerHTML = `<option value="">Create a project first</option>`;
    return;
  }
  el("projectSelect").innerHTML = state.projects
    .map((project) => `<option value="${project.id}">${escapeHtml(project.name)}</option>`)
    .join("");
}

function renderProjects() {
  const list = el("projectsList");
  if (!state.projects.length) {
    list.innerHTML = `<p class="muted">No projects yet. Create one to start generating QA packs.</p>`;
    return;
  }
  list.innerHTML = state.projects.map((project) => `
    <div class="project-card ${project.id === state.selectedProjectId ? "active" : ""}" data-project-id="${project.id}">
      <div class="card-top">
        <div>
          <h3>${escapeHtml(project.name)}</h3>
          <p>${escapeHtml(project.description || "No description")}</p>
        </div>
        <button class="danger small" title="Delete project" data-delete-project="${project.id}">Delete</button>
      </div>
    </div>
  `).join("");

  document.querySelectorAll("[data-project-id]").forEach((card) => {
    card.addEventListener("click", () => selectProject(card.dataset.projectId));
  });
  document.querySelectorAll("[data-delete-project]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteProject(button.dataset.deleteProject);
    });
  });
}

async function deleteProject(projectId) {
  const project = state.projects.find((item) => item.id === Number(projectId));
  if (!project) return;
  const message = `Delete "${project.name}"? This will permanently remove its requirements, test cases, uploads, and exports from the local database.`;
  if (!confirm(message)) return;

  try {
    await api(`/api/projects/${projectId}`, { method: "DELETE" });
    showStatus(`Project deleted: ${project.name}`);
    state.selectedProjectId = null;
    state.selectedRequirementId = null;
    state.testCases = [];
    await loadProjects();
    await loadHistorySummary();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function loadProjectAnalytics() {
  if (!state.selectedProjectId) return renderDashboardPlaceholder();
  try {
    state.analytics = await api(`/api/projects/${state.selectedProjectId}/analytics`);
    renderDashboard(state.analytics);
  } catch (error) {
    renderDashboardPlaceholder(error.message);
  }
}


async function loadLlmStatus() {
  if (!state.token) return renderLlmStatus(null);
  try {
    state.llmStatus = await api("/api/llm/status");
    renderLlmStatus(state.llmStatus);
  } catch (error) {
    renderLlmStatus({ error: error.message });
  }
}

function renderLlmStatus(status) {
  const box = el("llmStatus");
  if (!box) return;
  if (!status) {
    box.innerHTML = `<p class="muted">Login to check AI engine status.</p>`;
    return;
  }
  if (status.error) {
    box.innerHTML = `<p class="danger-text">${escapeHtml(status.error)}</p>`;
    return;
  }

  const active = status.active_provider || "fallback";
  const badgeClass = active === "ollama" ? "good" : active === "openai" ? "info" : "warn";
  const installed = status.ollama_models_installed || [];
  const ollamaLine = status.ollama_available
    ? `Ollama server is running at ${escapeHtml(status.ollama_base_url)}.`
    : `Ollama is not reachable at ${escapeHtml(status.ollama_base_url)}.`;
  const installedModels = installed.length ? installed.map(escapeHtml).join(", ") : "No installed models detected from Ollama.";

  box.innerHTML = `
    <div class="llm-grid">
      <div><span>Active provider</span><strong class="status-badge ${badgeClass}">${escapeHtml(active.toUpperCase())}</strong></div>
      <div><span>Configured provider</span><strong>${escapeHtml(status.configured_provider || "auto")}</strong></div>
      <div><span>Ollama model</span><strong>${escapeHtml(status.ollama_model || "llama3.1:8b")}</strong></div>
      <div><span>OpenAI key</span><strong>${status.openai_key_set ? "Configured" : "Not added"}</strong></div>
    </div>
    <p class="muted">${ollamaLine}</p>
    <p class="muted"><strong>Installed Ollama models:</strong> ${installedModels}</p>
    ${status.ollama_error && !status.ollama_available ? `<p class="muted"><strong>Ollama note:</strong> ${escapeHtml(status.ollama_error)}</p>` : ""}
  `;
}

async function loadHistorySummary() {
  if (!state.token) return renderHistorySummary(null);
  try {
    state.historySummary = await api("/api/history/summary");
    renderHistorySummary(state.historySummary);
  } catch (error) {
    renderHistorySummary({ error: error.message });
  }
}

function renderHistorySummary(summary) {
  const box = el("historySummary");
  if (!box) return;
  if (!summary) {
    box.innerHTML = `<p class="muted">Login to view saved history.</p>`;
    return;
  }
  if (summary.error) {
    box.innerHTML = `<p class="danger-text">${escapeHtml(summary.error)}</p>`;
    return;
  }
  box.innerHTML = `
    <div class="history-metrics">
      <span><strong>${summary.projects || 0}</strong> projects</span>
      <span><strong>${summary.requirements || 0}</strong> requirements</span>
      <span><strong>${summary.test_cases || 0}</strong> test cases</span>
      <span><strong>${summary.uploaded_documents || 0}</strong> uploads</span>
    </div>
  `;
}

async function clearSelectedProjectHistory() {
  if (!state.selectedProjectId) return showStatus("Select a project first.", true);
  const project = state.projects.find((item) => item.id === Number(state.selectedProjectId));
  const name = project ? project.name : "selected project";
  if (!confirm(`Clear generated history for "${name}"? This removes requirements, test cases, and uploaded text, but keeps the project.`)) return;
  try {
    const result = await api(`/api/history/project/${state.selectedProjectId}`, { method: "DELETE" });
    showStatus(`Cleared ${result.deleted_requirements} requirements and ${result.deleted_test_cases} test cases from ${name}.`);
    state.selectedRequirementId = null;
    state.testCases = [];
    await loadRequirements();
    await loadProjectAnalytics();
    await loadHistorySummary();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function clearAllHistory() {
  if (!confirm("Clear ALL generated history for your account? This removes all requirements, test cases, and uploaded text, but keeps your projects.")) return;
  if (!confirm("Final confirmation: this cannot be undone.")) return;
  try {
    const result = await api("/api/history/all", { method: "DELETE" });
    showStatus(`Cleared ${result.deleted_requirements} requirements and ${result.deleted_test_cases} test cases. Projects kept: ${result.projects_kept}.`);
    state.selectedRequirementId = null;
    state.testCases = [];
    await loadProjects();
    await loadHistorySummary();
  } catch (error) {
    showStatus(error.message, true);
  }
}

function renderDashboardPlaceholder(message = "Create or select a project to unlock analytics.") {
  el("dashboardSubtitle").textContent = message;
  el("metricsGrid").innerHTML = [
    metricCard("Requirements", "0", "Saved user stories"),
    metricCard("Test cases", "0", "Generated cases"),
    metricCard("Approved", "0", "Ready for export"),
    metricCard("High risk", "0", "Critical attention"),
    metricCard("QA score", "0%", "Coverage quality"),
  ].join("");
  el("chartBoard").innerHTML = [
    emptyChartCard("Test Type Mix"),
    emptyChartCard("Priority Mix"),
    emptyChartCard("Status Mix"),
    emptyChartCard("Severity Mix"),
  ].join("");
  el("recommendations").innerHTML = `<span>${escapeHtml(message)}</span>`;
}

function metricCard(label, value, helper) {
  return `
    <div class="metric-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(helper)}</small>
    </div>
  `;
}

function emptyChartCard(title) {
  return `
    <div class="chart-card">
      <h3>${escapeHtml(title)}</h3>
      <div class="pie-wrap"><div class="pie" style="background: conic-gradient(#334155 0 100%)"><span>No data</span></div></div>
      <div class="legend"><div class="legend-item"><span class="legend-dot" style="background:#334155"></span><span>Generate test cases</span><strong>0</strong></div></div>
    </div>
  `;
}

function renderDashboard(analytics) {
  const summary = analytics.summary || {};
  const project = analytics.project || {};
  el("dashboardSubtitle").textContent = project.description || "Live project analytics based on saved test cases.";
  el("selectedProjectLabel").textContent = project.name || "Selected project";

  el("metricsGrid").innerHTML = [
    metricCard("Requirements", summary.requirements || 0, "Saved user stories"),
    metricCard("Test cases", summary.test_cases || 0, "Generated cases"),
    metricCard("Approved", summary.approved_cases || 0, "Ready for export"),
    metricCard("High risk", summary.high_risk_cases || 0, "Critical attention"),
    metricCard("QA score", `${summary.coverage_score || 0}%`, "Coverage quality"),
  ].join("");

  const charts = analytics.charts || {};
  el("chartBoard").innerHTML = [
    pieChartCard("Test Type Mix", charts.by_type || {}, TEST_TYPES),
    pieChartCard("Priority Mix", charts.by_priority || {}, PRIORITIES),
    pieChartCard("Status Mix", charts.by_status || {}, STATUSES),
    pieChartCard("Severity Mix", charts.by_severity || {}, SEVERITIES),
  ].join("");

  const recommendations = analytics.recommendations || [];
  el("recommendations").innerHTML = recommendations.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
}

function pieChartCard(title, counts, preferredOrder) {
  const entries = preferredOrder
    .map((key) => [key, Number(counts[key] || 0)])
    .concat(Object.entries(counts || {}).filter(([key]) => !preferredOrder.includes(key)).map(([key, value]) => [key, Number(value || 0)]));
  const positive = entries.filter(([, value]) => value > 0);
  const total = positive.reduce((sum, [, value]) => sum + value, 0);

  if (!total) return emptyChartCard(title);

  let start = 0;
  const segments = positive.map(([label, value], index) => {
    const end = start + (value / total) * 100;
    const color = CHART_COLORS[index % CHART_COLORS.length];
    const segment = `${color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
    start = end;
    return { label, value, color, segment };
  });

  return `
    <div class="chart-card">
      <h3>${escapeHtml(title)}</h3>
      <div class="pie-wrap"><div class="pie" style="background: conic-gradient(${segments.map((item) => item.segment).join(", ")})"><span>${total}<br/>total</span></div></div>
      <div class="legend">
        ${segments.map((item) => `
          <div class="legend-item">
            <span class="legend-dot" style="background:${item.color}"></span>
            <span>${escapeHtml(item.label)}</span>
            <strong>${item.value}</strong>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

async function loadRequirements() {
  if (!state.selectedProjectId) return;
  state.requirements = await api(`/api/requirements?project_id=${state.selectedProjectId}`);
  const currentExists = state.requirements.some((req) => req.id === state.selectedRequirementId);
  if (!currentExists) {
    state.selectedRequirementId = state.requirements.length ? state.requirements[0].id : null;
  }
  renderRequirements();
  if (state.selectedRequirementId) await loadTestCases(state.selectedRequirementId);
  else {
    state.testCases = [];
    renderTable();
  }
}

async function selectRequirement(requirementId) {
  state.selectedRequirementId = Number(requirementId);
  renderRequirements();
  await loadTestCases(requirementId);
}

function renderRequirements() {
  const list = el("requirementsList");
  if (!state.selectedProjectId) {
    list.innerHTML = `<p class="muted">Create or select a project first.</p>`;
    el("exportHelp").textContent = "Select a project first.";
    return;
  }
  if (!state.requirements.length) {
    list.innerHTML = `<p class="muted">No requirements generated yet.</p>`;
    state.selectedRequirementId = null;
    el("exportHelp").textContent = "Generate a requirement first.";
    return;
  }

  list.innerHTML = state.requirements.map((req) => `
    <div class="requirement-card ${req.id === state.selectedRequirementId ? "active" : ""}" data-requirement-id="${req.id}">
      <div class="card-top">
        <div>
          <h3>${escapeHtml(req.title)}</h3>
          <p>${escapeHtml(req.module_name)}${req.source_filename ? " • " + escapeHtml(req.source_filename) : ""}</p>
        </div>
        <button class="danger small" title="Delete requirement" data-delete-requirement="${req.id}">Delete</button>
      </div>
    </div>
  `).join("");

  document.querySelectorAll("[data-requirement-id]").forEach((card) => {
    card.addEventListener("click", () => selectRequirement(card.dataset.requirementId));
  });
  document.querySelectorAll("[data-delete-requirement]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteRequirement(button.dataset.deleteRequirement);
    });
  });
  el("exportHelp").textContent = state.selectedRequirementId ? "Exports use the selected requirement." : "Select a requirement first.";
}

async function deleteRequirement(requirementId) {
  const req = state.requirements.find((item) => item.id === Number(requirementId));
  if (!req) return;
  if (!confirm(`Delete requirement "${req.title}" and all its test cases?`)) return;
  try {
    await api(`/api/requirements/${requirementId}`, { method: "DELETE" });
    showStatus(`Requirement deleted: ${req.title}`);
    if (state.selectedRequirementId === Number(requirementId)) {
      state.selectedRequirementId = null;
      state.testCases = [];
    }
    await loadRequirements();
    await loadProjectAnalytics();
    await loadHistorySummary();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function loadTestCases(requirementId) {
  if (!requirementId) return;
  state.testCases = await api(`/api/test-cases/${requirementId}`);
  renderTable();
}

function splitLines(value) {
  return String(value || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function filteredCases() {
  const q = el("caseSearch").value.trim().toLowerCase();
  const type = el("caseTypeFilter").value;
  const priority = el("casePriorityFilter").value;
  const status = el("caseStatusFilter").value;

  return (state.testCases || []).filter((tc) => {
    const haystack = [tc.title, tc.test_type, tc.priority, tc.severity, tc.test_data, tc.expected_result, tc.status, ...(tc.preconditions || []), ...(tc.steps || [])]
      .join(" ")
      .toLowerCase();
    return (!q || haystack.includes(q))
      && (!type || tc.test_type === type)
      && (!priority || tc.priority === priority)
      && (!status || tc.status === status);
  });
}

function renderTable() {
  const wrap = el("tableWrap");
  const allCases = state.testCases || [];
  const cases = filteredCases();
  if (!allCases.length) {
    wrap.className = "table-wrap empty-state";
    wrap.innerHTML = state.selectedRequirementId ? "No test cases found for this requirement." : "Generate or select a requirement to view test cases.";
    el("resultMeta").textContent = "";
    return;
  }

  wrap.className = "table-wrap";
  el("resultMeta").textContent = `${cases.length} of ${allCases.length} test cases shown. Edit any row and click Save.`;
  wrap.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Title</th>
          <th>Type</th>
          <th>Priority</th>
          <th>Severity</th>
          <th>Preconditions</th>
          <th>Steps</th>
          <th>Test Data</th>
          <th>Expected Result</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${cases.map((tc) => `
          <tr data-case-row="${tc.id}">
            <td><span class="badge">${tc.id}</span></td>
            <td><textarea data-field="title" rows="3">${escapeHtml(tc.title)}</textarea></td>
            <td>
              <select data-field="test_type">
                ${TEST_TYPES.map((value) => `<option ${tc.test_type === value ? "selected" : ""}>${value}</option>`).join("")}
              </select>
            </td>
            <td>
              <select data-field="priority">
                ${PRIORITIES.map((value) => `<option ${tc.priority === value ? "selected" : ""}>${value}</option>`).join("")}
              </select>
            </td>
            <td>
              <select data-field="severity">
                ${SEVERITIES.map((value) => `<option ${tc.severity === value ? "selected" : ""}>${value}</option>`).join("")}
              </select>
            </td>
            <td><textarea data-field="preconditions" rows="5">${escapeHtml((tc.preconditions || []).join("\n"))}</textarea></td>
            <td><textarea data-field="steps" rows="6">${escapeHtml((tc.steps || []).join("\n"))}</textarea></td>
            <td><textarea data-field="test_data" rows="5">${escapeHtml(tc.test_data)}</textarea></td>
            <td><textarea data-field="expected_result" rows="5">${escapeHtml(tc.expected_result)}</textarea></td>
            <td>
              <select data-field="status">
                ${STATUSES.map((value) => `<option ${tc.status === value ? "selected" : ""}>${value}</option>`).join("")}
              </select>
            </td>
            <td>
              <div class="row-actions">
                <button class="secondary" data-save-case="${tc.id}">Save</button>
                <button class="secondary" data-duplicate-case="${tc.id}">Duplicate</button>
                <button class="danger" data-delete-case="${tc.id}">Delete</button>
              </div>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;

  document.querySelectorAll("[data-save-case]").forEach((button) => button.addEventListener("click", () => saveCase(button.dataset.saveCase)));
  document.querySelectorAll("[data-duplicate-case]").forEach((button) => button.addEventListener("click", () => duplicateCase(button.dataset.duplicateCase)));
  document.querySelectorAll("[data-delete-case]").forEach((button) => button.addEventListener("click", () => deleteCase(button.dataset.deleteCase)));
}

async function saveCase(caseId) {
  const row = document.querySelector(`[data-case-row="${caseId}"]`);
  if (!row) return;
  const read = (field) => row.querySelector(`[data-field="${field}"]`).value;
  const payload = {
    title: read("title"),
    test_type: read("test_type"),
    priority: read("priority"),
    severity: read("severity"),
    preconditions: splitLines(read("preconditions")),
    steps: splitLines(read("steps")),
    test_data: read("test_data"),
    expected_result: read("expected_result"),
    status: read("status"),
  };

  try {
    await api(`/api/test-cases/${caseId}`, { method: "PATCH", body: JSON.stringify(payload) });
    showStatus(`Test case ${caseId} saved.`);
    await loadTestCases(state.selectedRequirementId);
    await loadProjectAnalytics();
    await loadHistorySummary();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function duplicateCase(caseId) {
  try {
    await api(`/api/test-cases/${caseId}/duplicate`, { method: "POST" });
    showStatus(`Test case ${caseId} duplicated.`);
    await loadTestCases(state.selectedRequirementId);
    await loadProjectAnalytics();
    await loadHistorySummary();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function deleteCase(caseId) {
  if (!confirm("Delete this test case?")) return;
  try {
    await api(`/api/test-cases/${caseId}`, { method: "DELETE" });
    showStatus(`Test case ${caseId} deleted.`);
    await loadTestCases(state.selectedRequirementId);
    await loadProjectAnalytics();
    await loadHistorySummary();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function downloadFile(path, fallbackName) {
  if (!state.selectedRequirementId) {
    showStatus("Select a requirement first.", true);
    return;
  }

  const response = await fetch(path, { headers: authHeaders() });
  if (!response.ok) {
    let message = "Download failed";
    try {
      const error = await response.json();
      message = error.detail || message;
    } catch (_) {}
    showStatus(message, true);
    return;
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match ? match[1] : fallbackName;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

el("signupForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await api("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({
        name: el("signupName").value,
        email: el("signupEmail").value,
        password: el("signupPassword").value,
      }),
    });
    state.token = data.access_token;
    localStorage.setItem("qa_token", state.token);
    setLoggedIn(data.user);
    await loadProjects();
    await loadLlmStatus();
    await loadHistorySummary();
  } catch (error) {
    alert(error.message);
  }
});

el("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: el("loginEmail").value,
        password: el("loginPassword").value,
      }),
    });
    state.token = data.access_token;
    localStorage.setItem("qa_token", state.token);
    setLoggedIn(data.user);
    await loadProjects();
    await loadLlmStatus();
    await loadHistorySummary();
  } catch (error) {
    alert(error.message);
  }
});

el("logoutBtn").addEventListener("click", setLoggedOut);
el("refreshLlmBtn").addEventListener("click", loadLlmStatus);
el("clearProjectHistoryBtn").addEventListener("click", clearSelectedProjectHistory);
el("clearAllHistoryBtn").addEventListener("click", clearAllHistory);

el("projectForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const project = await api("/api/projects", {
      method: "POST",
      body: JSON.stringify({
        name: el("projectName").value,
        description: el("projectDescription").value,
      }),
    });
    el("projectForm").reset();
    state.projects.unshift(project);
    renderProjectSelect();
    await selectProject(project.id);
    await loadHistorySummary();
    showStatus(`Project created: ${project.name}`);
  } catch (error) {
    alert(error.message);
  }
});

el("projectSelect").addEventListener("change", (event) => selectProject(event.target.value));

el("extractBtn").addEventListener("click", async () => {
  const file = el("requirementFile").files[0];
  if (!file) {
    showStatus("Please choose a PDF, DOCX, TXT, or MD file first.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  if (state.selectedProjectId) formData.append("project_id", state.selectedProjectId);

  el("extractBtn").disabled = true;
  showStatus("Extracting requirement text...");
  try {
    const data = await api("/api/uploads/extract-requirement", { method: "POST", body: formData });
    el("requirementText").value = data.extracted_text;
    el("requirementTitle").value = data.suggested_title;
    showStatus(`Extracted ${data.character_count} characters from ${data.filename}.`);
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    el("extractBtn").disabled = false;
  }
});

el("generateForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedProjectId) {
    showStatus("Create or select a project first.", true);
    return;
  }

  const types = selectedTestTypes();
  if (!types.length) {
    showStatus("Select at least one test type.", true);
    return;
  }

  const generateBtn = el("generateBtn");
  generateBtn.disabled = true;
  showStatus("Generating and saving test cases...");
  el("assumptions").classList.add("hidden");

  const file = el("requirementFile").files[0];
  const payload = {
    project_id: state.selectedProjectId,
    module_name: el("moduleName").value,
    requirement_title: el("requirementTitle").value,
    requirement_text: el("requirementText").value,
    source_filename: file ? file.name : "",
    number_of_cases: Number(el("numberOfCases").value),
    test_types: types,
  };

  try {
    const data = await api("/api/generate-test-cases", { method: "POST", body: JSON.stringify(payload) });
    state.selectedRequirementId = data.requirement.id;
    state.testCases = data.test_cases || [];
    if (data.ai_assumptions && data.ai_assumptions.length) {
      el("assumptions").innerHTML = `<strong>Notes:</strong> ${data.ai_assumptions.map(escapeHtml).join(" | ")}`;
      el("assumptions").classList.remove("hidden");
    }
    await loadRequirements();
    await selectRequirement(data.requirement.id);
    await loadProjectAnalytics();
    await loadHistorySummary();
    await loadLlmStatus();
    showStatus(`${state.testCases.length} test cases generated and saved.`);
  } catch (error) {
    showStatus(error.message, true);
  } finally {
    generateBtn.disabled = false;
  }
});

document.querySelectorAll("[data-export]").forEach((button) => {
  button.addEventListener("click", async () => {
    const type = button.dataset.export;
    const id = state.selectedRequirementId;
    if (!id) return showStatus("Select a requirement first.", true);
    const map = {
      csv: [`/api/export/csv/${id}`, `test_cases_${id}.csv`],
      excel: [`/api/export/excel/${id}`, `test_cases_${id}.xlsx`],
      pdf: [`/api/export/pdf/${id}`, `test_cases_${id}.pdf`],
      "jira-csv": [`/api/export/jira-csv/${id}`, `jira_test_cases_${id}.csv`],
      playwright: [`/api/export/playwright/${id}`, `generated_tests_${id}.spec.ts`],
    };
    await downloadFile(map[type][0], map[type][1]);
  });
});

["caseSearch", "caseTypeFilter", "casePriorityFilter", "caseStatusFilter"].forEach((id) => {
  el(id).addEventListener("input", renderTable);
  el(id).addEventListener("change", renderTable);
});
el("clearFiltersBtn").addEventListener("click", () => {
  el("caseSearch").value = "";
  el("caseTypeFilter").value = "";
  el("casePriorityFilter").value = "";
  el("caseStatusFilter").value = "";
  renderTable();
});

bootstrap();
