/**
 * FinishAI — api.js
 * Centralized API layer. All fetch calls go through this module.
 * Handles base URL, error handling, and response parsing.
 */

const API_BASE = window.location.hostname 
  === 'localhost' 
  ? 'http://localhost:8000'
  : 'https://YOUR_RAILWAY_URL';

/**
 * Core fetch wrapper with error handling
 */
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
  };
  const config = { ...defaults, ...options };
  if (options.headers) {
    config.headers = { ...defaults.headers, ...options.headers };
  }

  try {
    const res = await fetch(url, config);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}: ${res.statusText}`);
    }
    return data;
  } catch (err) {
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new Error('Cannot connect to server. Is the backend running on port 8000?');
    }
    throw err;
  }
}

// ─── PROJECTS ────────────────────────────────────────────────────────────────

/** Create a new project (triggers AI plan generation) */
async function createProject(data) {
  return apiFetch('/api/projects/create', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/** Get all projects with stats */
async function getProjects() {
  return apiFetch('/api/projects');
}

/** Get a single project with all tasks and stats */
async function getProject(id) {
  return apiFetch(`/api/projects/${id}`);
}

/** Delete a project */
async function deleteProject(id) {
  return apiFetch(`/api/projects/${id}`, { method: 'DELETE' });
}

// ─── TASKS ───────────────────────────────────────────────────────────────────

/** Create a new manual task */
async function createTask(data) {
  return apiFetch('/api/tasks/create', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/** Mark a task as complete */
async function completeTask(id, note = '') {
  return apiFetch(`/api/tasks/${id}/complete`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  });
}

/** Mark a task as skipped */
async function skipTask(id, note = '') {
  return apiFetch(`/api/tasks/${id}/skip`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  });
}

/** Mark a task as delayed */
async function delayTask(id, note = '') {
  return apiFetch(`/api/tasks/${id}/delay`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  });
}

/** Get all tasks due today across all projects */
async function getTodayTasks() {
  return apiFetch('/api/tasks/today');
}

// ─── AI ──────────────────────────────────────────────────────────────────────

/** Detect delays for a project */
async function detectDelays(projectId) {
  return apiFetch('/api/ai/detect-delays', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  });
}

/** Generate a plan preview (used in modal step 3) */
async function generatePlan(data) {
  return apiFetch('/api/ai/generate-plan', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ─── REPLAN ──────────────────────────────────────────────────────────────────

/** Send chat messages to the conversational AI onboarding endpoint */
async function sendChat(messages) {
  return apiFetch('/api/ai/chat', {
    method: 'POST',
    body: JSON.stringify({ messages }),
  });
}

/** Trigger AI re-planning for a project */
async function replanProject(projectId, reason = 'manual') {
  return apiFetch(`/api/replan/${projectId}`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

// ─── HEALTH ──────────────────────────────────────────────────────────────────

async function healthCheck() {
  return apiFetch('/health');
}

// ─── EXPORTS ─────────────────────────────────────────────────────────────────
// Using window globals since there's no module bundler
window.API = {
  createProject,
  createTask,
  getProjects,
  getProject,
  deleteProject,
  completeTask,
  skipTask,
  delayTask,
  getTodayTasks,
  detectDelays,
  generatePlan,
  sendChat,
  replanProject,
  healthCheck,
};
