/**
 * FinishAI — daily.js
 * Daily checklist page logic: load today's tasks, handle completions,
 * show celebration when all done, adjust plan on skip/delay.
 */

let todayTasks = [];
let completedCount = 0;
let totalCount = 0;

// ─── INIT ────────────────────────────────────────────────────────────────────

async function initDailyPage() {
  renderDateHeader();
  renderMotivation();
  await loadTodayTasks();
}

function renderDateHeader() {
  const dateEl = document.getElementById('today-date');
  const greetEl = document.getElementById('daily-greeting');
  if (dateEl) dateEl.textContent = window.App.todayStr();
  if (greetEl) greetEl.textContent = window.App.greetingByTime();
}

function renderMotivation() {
  const messages = [
    "Every task you complete today is a step closer to your goal. 🎯",
    "Consistency beats perfection. Show up today and keep moving. 💪",
    "The secret to getting ahead is getting started. Start here. ⚡",
    "Small daily actions compound into massive results. Keep going! 🚀",
    "Your future self will thank you for what you do today. ✨",
    "Progress, not perfection. Each task matters. 🌟",
    "Champions are made in the moments when they want to give up. Push! 🏆",
  ];
  const msg = messages[new Date().getDay() % messages.length];
  const el = document.getElementById('motivation-message');
  if (el) el.textContent = msg;
}

// ─── LOAD TASKS ──────────────────────────────────────────────────────────────

async function loadTodayTasks() {
  const container = document.getElementById('daily-tasks-container');
  const statsEl = document.getElementById('daily-stats');

  showLoadingState(container);

  try {
    const result = await window.API.getTodayTasks();
    todayTasks = result.tasks || [];
    totalCount = todayTasks.length;
    completedCount = todayTasks.filter(t => t.status === 'completed').length;

    if (!todayTasks.length) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🎉</div>
          <div class="empty-state-title">All caught up!</div>
          <p class="empty-state-subtitle">No tasks scheduled for today. Take a rest or create a new project.</p>
          <a href="dashboard.html" class="btn btn-primary mt-16">Go to Dashboard</a>
        </div>
      `;
      return;
    }

    renderTasks(container);
    updateDailyStats(statsEl);
    updateProgressBar();

    if (completedCount === totalCount && totalCount > 0) {
      showCelebration();
    }
  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Couldn't load tasks</div>
        <p class="empty-state-subtitle">${err.message}</p>
        <button class="btn btn-primary mt-16" onclick="loadTodayTasks()">Retry</button>
      </div>
    `;
  }
}

// ─── RENDER TASKS ────────────────────────────────────────────────────────────

function renderTasks(container) {
  const pending = todayTasks.filter(t => t.status === 'pending' || t.status === 'delayed');
  const done = todayTasks.filter(t => t.status === 'completed');
  const skipped = todayTasks.filter(t => t.status === 'skipped');

  let html = '';

  if (pending.length) {
    html += `<div style="margin-bottom: 24px">
      <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); letter-spacing: 0.08em; margin-bottom: 16px;">
        📋 TO DO — ${pending.length} task${pending.length !== 1 ? 's' : ''}
      </div>
      <div class="stagger" style="display: flex; flex-direction: column; gap: 12px;">
        ${pending.map(t => renderDailyTaskCard(t)).join('')}
      </div>
    </div>`;
  }

  if (done.length) {
    html += `<div style="margin-bottom: 24px">
      <div style="font-size: 0.8rem; font-weight: 700; color: var(--success); letter-spacing: 0.08em; margin-bottom: 16px;">
        ✅ COMPLETED — ${done.length} task${done.length !== 1 ? 's' : ''}
      </div>
      <div style="display: flex; flex-direction: column; gap: 12px; opacity: 0.7">
        ${done.map(t => renderDailyTaskCard(t, true)).join('')}
      </div>
    </div>`;
  }

  if (skipped.length) {
    html += `<div>
      <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); letter-spacing: 0.08em; margin-bottom: 16px;">
        ⏭️ SKIPPED — ${skipped.length} task${skipped.length !== 1 ? 's' : ''}
      </div>
      <div style="display: flex; flex-direction: column; gap: 12px; opacity: 0.5">
        ${skipped.map(t => renderDailyTaskCard(t, false, true)).join('')}
      </div>
    </div>`;
  }

  container.innerHTML = html;
}

function renderDailyTaskCard(task, completed = false, skipped = false) {
  const statusClass = completed ? 'completed' : skipped ? 'skipped' : '';

  return `
    <div class="daily-task-card ${statusClass} fade-up" id="daily-task-${task.id}">
      <div class="task-checkbox ${completed ? 'checked' : ''}"
           onclick="${!completed && !skipped ? `completeDailyTask('${task.id}')` : ''}">
        ${completed ? '✓' : ''}
      </div>
      <div style="flex: 1; min-width: 0">
        <div style="font-size: 1rem; font-weight: ${completed ? '500' : '600'}; color: ${completed ? 'var(--text-muted)' : 'var(--text-primary)'}; 
             text-decoration: ${completed ? 'line-through' : 'none'}; margin-bottom: 6px; line-height: 1.4">
          ${task.name}
        </div>
        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
          <span class="badge badge-info" style="font-size: 0.75rem">⏱ ${task.duration_minutes}m</span>
          ${window.App.priorityDot(task.priority)}
          <span style="font-size: 0.8rem; color: var(--text-muted)">${task.priority} priority</span>
        </div>
      </div>
      ${!completed && !skipped ? `
        <div class="task-actions">
          <button class="task-action-btn done" onclick="completeDailyTask('${task.id}')" id="done-btn-${task.id}">
            ✅ Done
          </button>
          <button class="task-action-btn skip" onclick="skipDailyTask('${task.id}')" title="Skip">
            ⏭️
          </button>
          <button class="task-action-btn delay" onclick="delayDailyTask('${task.id}')" title="Delay to tomorrow">
            ⏰
          </button>
        </div>
      ` : completed ? '<span style="font-size: 1.2rem">🎉</span>' : '<span style="font-size: 1.2rem; opacity: 0.5">—</span>'}
    </div>
  `;
}

// ─── TASK ACTIONS ────────────────────────────────────────────────────────────

async function completeDailyTask(taskId) {
  const card = document.getElementById(`daily-task-${taskId}`);
  const btn = document.getElementById(`done-btn-${taskId}`);

  if (btn) window.App.setButtonLoading(btn, true);

  try {
    await window.API.completeTask(taskId);
    todayTasks = todayTasks.map(t => t.id === taskId ? { ...t, status: 'completed' } : t);
    completedCount = todayTasks.filter(t => t.status === 'completed').length;

    window.App.showToast('✅ Task complete!', 'Keep the momentum going!', 'success');
    await loadTodayTasks();

    if (completedCount >= totalCount) {
      showCelebration();
    }
  } catch (err) {
    window.App.showToast('Failed to complete task', err.message, 'error');
    if (btn) window.App.setButtonLoading(btn, false);
  }
}

async function skipDailyTask(taskId) {
  try {
    const result = await window.API.skipTask(taskId);
    todayTasks = todayTasks.map(t => t.id === taskId ? { ...t, status: 'skipped' } : t);

    if (result.needs_replan) {
      window.App.showToast('Task skipped', '⚠️ Consider running AI re-plan.', 'warning');
    } else {
      window.App.showToast('Task skipped', "It'll be handled tomorrow.", 'info');
    }

    await loadTodayTasks();
    checkSkippedTasks();
  } catch (err) {
    window.App.showToast('Failed to skip task', err.message, 'error');
  }
}

async function delayDailyTask(taskId) {
  try {
    const result = await window.API.delayTask(taskId);
    todayTasks = todayTasks.map(t => t.id === taskId ? { ...t, status: 'delayed' } : t);

    window.App.showToast('Task delayed', 'Moved to tomorrow.', 'info');
    await loadTodayTasks();
    checkSkippedTasks();
  } catch (err) {
    window.App.showToast('Failed to delay task', err.message, 'error');
  }
}

// ─── STATS & PROGRESS ────────────────────────────────────────────────────────

function updateDailyStats(statsEl) {
  if (!statsEl) return;
  const pct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
  const totalMinutes = todayTasks.filter(t => t.status !== 'completed').reduce((sum, t) => sum + (t.duration_minutes || 0), 0);

  statsEl.innerHTML = `
    <div style="display: flex; gap: 24px; align-items: center; flex-wrap: wrap">
      <div>
        <span style="font-size: 2rem; font-weight: 800; color: var(--primary)">${completedCount}</span>
        <span style="color: var(--text-muted)">/${totalCount} done</span>
      </div>
      <div style="height: 32px; width: 1px; background: var(--border)"></div>
      <div>
        <span style="font-size: 1.1rem; font-weight: 700">${pct}%</span>
        <span style="color: var(--text-muted); font-size: 0.875rem"> complete</span>
      </div>
      <div style="height: 32px; width: 1px; background: var(--border)"></div>
      <div>
        <span style="color: var(--text-muted); font-size: 0.875rem">≈ ${totalMinutes}m remaining</span>
      </div>
    </div>
  `;
}

function updateProgressBar() {
  const bar = document.getElementById('daily-progress-bar');
  if (!bar) return;
  const pct = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
  bar.style.width = `${pct}%`;
}

// ─── SKIPPED TASKS MESSAGE ───────────────────────────────────────────────────

function checkSkippedTasks() {
  const skipped = todayTasks.filter(t => t.status === 'skipped' || t.status === 'delayed');
  const container = document.getElementById('skipped-message');
  if (!container) return;

  if (skipped.length) {
    container.style.display = 'block';
    container.innerHTML = `
      <div class="glass-card" style="border-color: rgba(245,158,11,0.2); background: rgba(245,158,11,0.06)">
        <div style="font-weight: 700; margin-bottom: 8px">🤖 AI Note</div>
        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 16px">
          You skipped or delayed ${skipped.length} task${skipped.length > 1 ? 's' : ''} today. 
          AI has noted this and will adjust tomorrow's plan. Here's what to prioritize first tomorrow:
        </p>
        <div style="padding: 12px; background: var(--bg-card); border-radius: 10px; font-weight: 600">
          → ${skipped[0]?.name || 'Your highest priority skipped task'}
        </div>
      </div>
    `;
  } else {
    container.style.display = 'none';
  }
}

// ─── CELEBRATION ─────────────────────────────────────────────────────────────

function showCelebration() {
  window.App.launchConfetti();

  const overlay = document.getElementById('celebration-overlay');
  if (overlay) {
    overlay.style.display = 'flex';
    const totalTime = todayTasks.reduce((sum, t) => sum + (t.duration_minutes || 0), 0);
    overlay.innerHTML = `
      <div class="celebration-message" style="pointer-events: all">
        <div style="font-size: 4rem; margin-bottom: 16px; animation: bounce 1s ease-in-out infinite">🎉</div>
        <h2 style="font-size: 2rem; font-weight: 800; margin-bottom: 12px">All Done!</h2>
        <p style="color: var(--text-secondary); margin-bottom: 24px">
          Amazing work! You completed <strong style="color: var(--text-primary)">${completedCount} tasks</strong>
          and saved approximately <strong style="color: var(--text-primary)">${totalTime} minutes</strong> of planning.
        </p>
        <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap">
          <a href="dashboard.html" class="btn btn-primary">📊 View Projects</a>
          <button class="btn btn-secondary" onclick="document.getElementById('celebration-overlay').style.display='none'">
            Keep Working
          </button>
        </div>
      </div>
    `;
  }
}

// ─── LOADING STATE ───────────────────────────────────────────────────────────

function showLoadingState(container) {
  container.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 12px">
      ${[1,2,3].map(() => `
        <div class="skeleton" style="height: 80px; border-radius: 12px;"></div>
      `).join('')}
    </div>
  `;
}

// ─── INIT ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', initDailyPage);

window.completeDailyTask = completeDailyTask;
window.skipDailyTask = skipDailyTask;
window.delayDailyTask = delayDailyTask;
window.loadTodayTasks = loadTodayTasks;
