/**
 * FinishAI — project.js
 * Project detail page logic: tabs, task management, AI insights, timeline.
 * Used by project.html
 */

let currentProject = null;
let currentTasks = [];
let currentStats = null;
let activeTab = 'overview';

// ─── INIT ────────────────────────────────────────────────────────────────────

async function initProjectPage() {
  const params = new URLSearchParams(window.location.search);
  const projectId = params.get('id');

  if (!projectId) {
    window.location.href = 'dashboard.html';
    return;
  }

  showProjectSkeleton();

  try {
    const data = await window.API.getProject(projectId);
    currentProject = data.project;
    currentTasks = data.tasks;
    currentStats = data.stats;

    renderProjectHeader();
    renderOverviewTab();
    renderTimelineTab();
    renderTasksTab();

    // Auto-detect delays in background
    autoDetectDelays(projectId);

  } catch (err) {
    document.getElementById('project-content').innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">❌</div>
        <div class="empty-state-title">Failed to load project</div>
        <p class="empty-state-subtitle">${err.message}</p>
        <a href="dashboard.html" class="btn btn-primary mt-16">← Back to Dashboard</a>
      </div>
    `;
  }
}

// ─── HEADER ──────────────────────────────────────────────────────────────────

function renderProjectHeader() {
  const { name, type, emoji, deadline, status } = currentProject;
  const stats = currentStats;
  const days = window.App.daysRemaining(deadline);

  document.getElementById('project-title').textContent = `${emoji || '📋'} ${name}`;
  document.getElementById('project-type-badge').innerHTML = `<span class="badge badge-info">${type}</span>`;
  document.getElementById('project-status-badge').innerHTML = window.App.statusBadge(status);
  document.getElementById('project-deadline').textContent = `${days > 0 ? days : 0} days remaining`;

  // Progress circle
  const circleEl = document.getElementById('progress-circle');
  if (circleEl) window.App.renderProgressCircle(circleEl, stats.actual_percent, 80);

  // Roadmap button link
  const roadmapBtn = document.getElementById('btn-roadmap');
  if (roadmapBtn && currentProject && currentProject.id) {
    roadmapBtn.href = `roadmap.html?id=${currentProject.id}`;
  }
}

// ─── OVERVIEW TAB ────────────────────────────────────────────────────────────

function renderOverviewTab() {
  const stats = currentStats;

  // Stats row
  document.getElementById('stat-total').textContent = stats.total_tasks;
  document.getElementById('stat-completed').textContent = stats.completed_tasks;
  document.getElementById('stat-remaining').textContent = stats.remaining_tasks;
  document.getElementById('stat-days').textContent = Math.max(stats.days_remaining, 0);

  // Milestones
  renderMilestones();

  // Coach message
  renderCoachMessage();

  // Next best action
  renderNextAction();
}

function renderMilestones() {
  const container = document.getElementById('milestones-container');
  if (!container || !currentProject.milestones) return;

  container.innerHTML = currentProject.milestones.map((milestone, i) => {
    const milestoneTasks = currentTasks.filter(t => t.milestone_id === milestone.id);
    const completedCount = milestoneTasks.filter(t => t.status === 'completed').length;
    const pct = milestoneTasks.length ? (completedCount / milestoneTasks.length) * 100 : 0;

    const milestoneStatus = pct === 100 ? 'completed' : (pct > 0 ? 'in_progress' : 'pending');
    const statusEmoji = { completed: '✅', in_progress: '🔄', pending: '⏳' }[milestoneStatus];

    // Resources Section
    const resourcesHtml = (milestone.resources && milestone.resources.length) ? `
      <div style="margin: 16px 0; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 16px;">
        <h5 style="color: var(--text-primary); font-size: 0.95rem; font-weight: 700; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
          📚 Resources for this phase
        </h5>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${milestone.resources.map(res => {
            const icons = { youtube: '📺', website: '🌐', tool: '🛠️', article: '📄' };
            const icon = icons[res.type] || '🌐';
            return `
              <div class="glass-card-sm" style="padding: 12px; display: flex; align-items: center; justify-content: space-between; gap: 12px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 10px; flex: 1;">
                  <span style="font-size: 1.3rem;">${icon}</span>
                  <div>
                    <div style="font-weight: 700; font-size: 0.9rem; color: var(--text-primary);">${res.title}</div>
                    ${res.description ? `<div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px;">${res.description}</div>` : ''}
                  </div>
                </div>
                ${res.url ? `<a href="${res.url}" target="_blank" rel="noopener noreferrer" class="btn-open-resource" style="padding: 6px 12px; font-size: 0.85rem; flex-shrink: 0; font-weight: 600; color: #3B82F6; text-decoration: none;">Open →</a>` : ''}
              </div>
            `;
          }).join('')}
        </div>
      </div>
    ` : '';

    // Checkpoint Section
    const checkpointHtml = milestone.checkpoint ? `
      <div style="margin: 16px 0;">
        <h5 style="color: var(--text-primary); font-size: 0.95rem; font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
          ✅ How to know you're ready
        </h5>
        <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px 16px; color: #10B981; font-size: 0.88rem; font-weight: 500;">
          ${milestone.checkpoint}
        </div>
      </div>
    ` : '';

    // Tips Section
    const tipsHtml = (milestone.tips && milestone.tips.length) ? `
      <div style="margin: 16px 0;">
        <h5 style="color: var(--text-primary); font-size: 0.95rem; font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
          💡 Tips
        </h5>
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
          ${milestone.tips.map(tip => `
            <span style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60A5FA; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 500;">
              💡 ${tip}
            </span>
          `).join('')}
        </div>
      </div>
    ` : '';

    // Warnings Section
    const warningsHtml = (milestone.warnings && milestone.warnings.length) ? `
      <div style="margin: 16px 0;">
        <h5 style="color: var(--text-primary); font-size: 0.95rem; font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
          ⚠️ Common mistakes
        </h5>
        <div style="display: flex; flex-direction: column; gap: 6px;">
          ${milestone.warnings.map(warn => `
            <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); color: #FBBF24; padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; font-weight: 500;">
              ⚠️ ${warn}
            </div>
          `).join('')}
        </div>
      </div>
    ` : '';

    return `
      <div class="milestone-card" style="min-height: 100px; padding: 20px 24px; color: var(--text-primary); margin-bottom: 16px;">
        <div class="milestone-header" onclick="toggleMilestone('mil-${milestone.id}')" style="color: var(--text-primary);">
          <div class="milestone-number">${i + 1}</div>
          <div style="flex: 1">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
              <span style="font-weight: 700; color: var(--text-primary);">${milestone.name}</span>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="text-secondary" style="font-size: 0.85rem; color: var(--text-secondary);">Target: ${window.App.formatDate(milestone.target_date)}</span>
                <span>${statusEmoji}</span>
              </div>
            </div>
            <div class="progress-bar-container">
              <div class="progress-bar-fill ${window.App.progressColor(pct)}" style="width: ${pct}%"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
              <span style="font-size: 0.8rem; color: var(--text-secondary);">${completedCount}/${milestoneTasks.length} tasks ${milestone.resources ? `• ${milestone.resources.length} resources` : ''}</span>
              <span style="font-size: 0.8rem; color: var(--primary); font-weight: 600;">${Math.round(pct)}%</span>
            </div>
          </div>
          <span style="color: var(--text-secondary); font-size: 0.8rem; margin-left: 8px;">▼</span>
        </div>
        <div id="mil-${milestone.id}" class="milestone-tasks">
          ${resourcesHtml}
          ${checkpointHtml}
          ${tipsHtml}
          ${warningsHtml}
          <div style="margin-top: 16px;">
            <h5 style="color: var(--text-primary); font-size: 0.95rem; font-weight: 700; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
              📋 Tasks for this phase
            </h5>
            ${milestoneTasks.map(task => renderMiniTask(task)).join('')}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderMiniTask(task) {
  const statusClass = task.status === 'completed' ? 'completed' : '';
  const checkmark = task.status === 'completed' ? '✓' : '';

  return `
    <div class="task-item ${statusClass} task-complete-effect" id="task-${task.id}" style="color: var(--text-primary); flex-direction: column; align-items: stretch; gap: 8px; padding: 14px;">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div class="task-checkbox ${task.status === 'completed' ? 'checked' : ''}"
               onclick="toggleTask('${task.id}', '${task.status}')">
            ${checkmark}
          </div>
          <div class="task-name" style="color: var(--text-primary); font-weight: 600; font-size: 0.95rem;">${task.name}</div>
        </div>
        <div class="task-meta" style="color: var(--text-secondary); display: flex; align-items: center; gap: 8px;">
          ${window.App.priorityDot(task.priority)}
          <span class="badge badge-muted" style="font-size: 0.75rem; text-transform: uppercase;">${task.priority}</span>
          <span class="text-secondary" style="font-size: 0.8rem; color: var(--text-secondary);">⏱ ${task.duration_minutes}m</span>
          <span class="text-secondary" style="font-size: 0.8rem; color: var(--text-secondary);">📅 ${window.App.formatDate(task.due_date)}</span>
        </div>
      </div>
      ${task.description ? `
        <div style="padding-left: 36px; font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4;">
          ${task.description}
        </div>
      ` : ''}
      ${task.resource_url ? `
        <div style="padding-left: 36px;">
          <a href="${task.resource_url}" target="_blank" rel="noopener noreferrer" class="btn-open-resource" style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 0.85rem; font-weight: 600; color: #3B82F6; text-decoration: none;">
            🔗 Open Resource →
          </a>
        </div>
      ` : ''}
    </div>
  `;
}


function toggleMilestone(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('open');
}

function renderCoachMessage() {
  const stats = currentStats;
  const { status } = currentProject;
  const container = document.getElementById('coach-message');
  if (!container) return;

  let messageText = '';
  if (stats.tasks_per_day_actual === 0 || stats.completed_tasks === 0) {
    messageText = "Pehla task shuru karo — bas ek kadam! 💪";
  } else if (status === 'on_track') {
    messageText = "Acha pace hai! Isi tarah chalo. 🌟";
  } else if (status === 'at_risk') {
    messageText = `⚡ You're a bit behind pace. You need ${stats.tasks_per_day_required} tasks/day but averaging ${stats.tasks_per_day_actual}. Focus on high-priority tasks this week to recover.`;
  } else if (status === 'behind') {
    messageText = `🔴 This project needs attention. You're currently ${Math.abs(stats.days_difference)} days behind schedule. Consider using AI re-planning to redistribute your remaining tasks.`;
  } else {
    messageText = "Acha pace hai! Isi tarah chalo. 🌟";
  }

  container.innerHTML = `
    <div class="coach-card">
      <div class="coach-avatar">🤖</div>
      <div>
        <div style="font-size: 0.8rem; font-weight: 600; color: var(--secondary); margin-bottom: 8px;">AI COACH</div>
        <p style="color: var(--text-primary); line-height: 1.6; margin: 0">${messageText}</p>
      </div>
    </div>
  `;
}

function renderNextAction() {
  const pending = currentTasks.filter(t => t.status === 'pending' || t.status === 'delayed');
  if (!pending.length) return;

  pending.sort((a, b) => {
    const priorityScore = { high: 0, medium: 1, low: 2 };
    return (priorityScore[a.priority] - priorityScore[b.priority]) ||
           (new Date(a.due_date) - new Date(b.due_date));
  });

  const next = pending[0];
  const container = document.getElementById('next-action-container');
  if (!container) return;

  container.innerHTML = `
    <div class="next-action-card">
      <div style="font-size: 0.8rem; font-weight: 700; color: var(--primary); margin-bottom: 12px; letter-spacing: 0.05em;">→ YOUR NEXT ACTION</div>
      <div style="font-size: 1.2rem; font-weight: 700; color: var(--text-primary); margin-bottom: 12px;">${next.name}</div>
      <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px;">
        ${window.App.priorityDot(next.priority)}
        <span class="badge badge-muted">${next.priority} priority</span>
        <span class="badge badge-info">⏱ ${next.duration_minutes} min</span>
        <span class="badge badge-muted">📅 ${window.App.formatDate(next.due_date)}</span>
      </div>
      ${next.description ? `
        <details style="cursor: pointer">
          <summary style="font-size: 0.875rem; color: var(--primary); font-weight: 600">Why this task? ▼</summary>
          <p style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 8px; padding-left: 12px; border-left: 2px solid var(--border)">${next.description}</p>
        </details>
      ` : ''}
      <button class="btn btn-primary btn-sm mt-16" onclick="markTaskDone('${next.id}')">
        ✅ Mark as Done
      </button>
    </div>
  `;
}

// ─── TASKS TAB ───────────────────────────────────────────────────────────────

function renderTasksTab(filter = 'all') {
  const container = document.getElementById('tasks-container');
  if (!container) return;

  const today = new Date().toISOString().split('T')[0];
  const weekEnd = new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];

  let filtered = currentTasks;
  if (filter === 'today') filtered = currentTasks.filter(t => t.due_date?.startsWith(today));
  else if (filter === 'week') filtered = currentTasks.filter(t => t.due_date >= today && t.due_date <= weekEnd);
  else if (filter === 'completed') filtered = currentTasks.filter(t => t.status === 'completed');
  else if (filter === 'skipped') filtered = currentTasks.filter(t => t.status === 'skipped' || t.status === 'delayed');

  if (!filtered.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📭</div>
        <div class="empty-state-title">No tasks found</div>
        <p class="empty-state-subtitle">No tasks match this filter.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(task => `
    <div class="task-item ${task.status}" id="task-row-${task.id}" style="flex-direction: column; align-items: stretch; gap: 8px; padding: 16px;">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div class="task-checkbox ${task.status === 'completed' ? 'checked' : ''}"
               onclick="toggleTask('${task.id}', '${task.status}')">
            ${task.status === 'completed' ? '✓' : ''}
          </div>
          <div class="task-name" style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary);">${task.name}</div>
        </div>
        <div class="task-meta" style="display: flex; align-items: center; gap: 8px;">
          ${window.App.priorityDot(task.priority)}
          <span class="badge badge-muted">${task.priority}</span>
          <span class="text-muted" style="font-size: 0.8rem">⏱ ${task.duration_minutes}m</span>
          <span class="text-muted" style="font-size: 0.8rem">📅 ${window.App.formatDate(task.due_date)}</span>
        </div>
      </div>
      ${task.description ? `
        <div style="padding-left: 36px; font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4;">
          ${task.description}
        </div>
      ` : ''}
      ${task.resource_url ? `
        <div style="padding-left: 36px;">
          <a href="${task.resource_url}" target="_blank" rel="noopener noreferrer" class="btn-open-resource" style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 0.85rem; font-weight: 600; color: #3B82F6; text-decoration: none;">
            🔗 Open Resource →
          </a>
        </div>
      ` : ''}
      ${task.status === 'pending' || task.status === 'delayed' ? `
        <div class="task-actions" style="padding-left: 36px; margin-top: 4px;">
          <button class="task-action-btn done" onclick="markTaskDone('${task.id}')">✅ Done</button>
          <button class="task-action-btn skip" onclick="markTaskSkip('${task.id}')">⏭️</button>
          <button class="task-action-btn delay" onclick="markTaskDelay('${task.id}')">⏰</button>
        </div>
      ` : ''}
    </div>
  `).join('');
}

// ─── TIMELINE TAB ────────────────────────────────────────────────────────────

function renderTimelineTab() {
  const container = document.getElementById('timeline-container');
  if (!container || !currentProject.milestones) return;

  const today = new Date().toISOString().split('T')[0];

  const items = currentProject.milestones.map((m, i) => {
    const milestoneTasks = currentTasks.filter(t => t.milestone_id === m.id);
    const completed = milestoneTasks.filter(t => t.status === 'completed').length;
    const isPast = m.target_date < today;
    const isCurrent = !isPast && (i === 0 || currentProject.milestones[i - 1]?.target_date < today);

    return `
      <div class="timeline-item">
        <div class="timeline-dot ${isPast ? 'completed' : isCurrent ? 'active' : ''}"></div>
        <div class="glass-card-sm">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px">
            <div>
              <div style="font-weight: 700; margin-bottom: 4px">${m.name}</div>
              <div class="text-muted" style="font-size: 0.85rem">${m.description || ''}</div>
            </div>
            <div style="text-align: right; flex-shrink: 0">
              <div style="font-size: 0.8rem; color: var(--text-muted)">Target</div>
              <div style="font-weight: 600; font-size: 0.9rem">${window.App.formatDate(m.target_date)}</div>
            </div>
          </div>
          <div style="margin-top: 12px">
            <div class="progress-bar-container">
              <div class="progress-bar-fill" style="width: ${milestoneTasks.length ? (completed / milestoneTasks.length * 100) : 0}%"></div>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px">${completed}/${milestoneTasks.length} tasks complete</div>
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = `<div class="timeline stagger">${items.join('')}</div>`;
}

// ─── INSIGHTS TAB ────────────────────────────────────────────────────────────

async function loadInsightsTab() {
  const container = document.getElementById('insights-container');
  if (!container) return;

  container.innerHTML = `
    <div class="glass-card mb-24">
      <div style="font-weight: 700; margin-bottom: 20px; font-size: 1.1rem">📊 Progress Analysis</div>
      <div class="grid-2 gap-16">
        <div>
          <div class="text-muted" style="font-size: 0.85rem; margin-bottom: 4px">Current Pace</div>
          <div style="font-size: 1.5rem; font-weight: 800">${currentStats.tasks_per_day_actual} <span style="font-size: 0.9rem; color: var(--text-muted)">tasks/day</span></div>
        </div>
        <div>
          <div class="text-muted" style="font-size: 0.85rem; margin-bottom: 4px">Required Pace</div>
          <div style="font-size: 1.5rem; font-weight: 800">${currentStats.tasks_per_day_required} <span style="font-size: 0.9rem; color: var(--text-muted)">tasks/day</span></div>
        </div>
        <div>
          <div class="text-muted" style="font-size: 0.85rem; margin-bottom: 4px">Predicted Finish</div>
          <div style="font-size: 1.2rem; font-weight: 700">${window.App.formatDate(currentStats.predicted_finish)}</div>
        </div>
        <div>
          <div class="text-muted" style="font-size: 0.85rem; margin-bottom: 4px">Deadline</div>
          <div style="font-size: 1.2rem; font-weight: 700">${window.App.formatDate(currentProject.deadline)}</div>
        </div>
      </div>
      <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border)">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
          <span class="text-muted" style="font-size: 0.85rem">Progress (Expected)</span>
          <span style="font-weight: 600">${currentStats.expected_percent}%</span>
        </div>
        <div class="progress-bar-container mb-8">
          <div class="progress-bar-fill" style="width: ${currentStats.expected_percent}%; background: var(--border); opacity: 0.5"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
          <span class="text-muted" style="font-size: 0.85rem">Progress (Actual)</span>
          <span style="font-weight: 600; color: var(--primary)">${currentStats.actual_percent}%</span>
        </div>
        <div class="progress-bar-container">
          <div class="progress-bar-fill ${window.App.progressColor(currentStats.actual_percent)}" style="width: ${currentStats.actual_percent}%"></div>
        </div>
      </div>
    </div>

    ${currentProject.replan_history?.length ? renderReplanHistory() : ''}

    ${currentProject.risks?.length ? `
      <div class="glass-card mb-24">
        <div style="font-weight: 700; margin-bottom: 16px">⚠️ Risk Factors</div>
        <ul style="padding-left: 20px; display: flex; flex-direction: column; gap: 8px">
          ${currentProject.risks.map(r => `<li style="color: var(--text-secondary); font-size: 0.9rem">${r}</li>`).join('')}
        </ul>
      </div>
    ` : ''}

    ${currentProject.success_tips?.length ? `
      <div class="glass-card">
        <div style="font-weight: 700; margin-bottom: 16px">💡 Success Tips</div>
        <ul style="padding-left: 20px; display: flex; flex-direction: column; gap: 8px">
          ${currentProject.success_tips.map(t => `<li style="color: var(--text-secondary); font-size: 0.9rem">${t}</li>`).join('')}
        </ul>
      </div>
    ` : ''}
  `;

  // Show replan section if project is behind
  if (currentStats.status !== 'on_track') {
    showReplanSection(container);
  }
}

function renderReplanHistory() {
  const history = currentProject.replan_history;
  if (!history?.length) return '';

  return `
    <div class="glass-card mb-24">
      <div style="font-weight: 700; margin-bottom: 16px">📋 Re-plan History</div>
      <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center">
        <span class="badge badge-muted">Original Plan</span>
        ${history.map((h, i) => `
          <span style="color: var(--text-muted)">→</span>
          <span class="badge badge-info">Re-plan ${i + 1} (${h.date}) — ${h.reason}</span>
        `).join('')}
      </div>
    </div>
  `;
}

function showReplanSection(container) {
  const section = document.createElement('div');
  section.className = 'replan-card mb-24';
  section.id = 'replan-section';
  section.innerHTML = `
    <div style="display: flex; align-items: flex-start; gap: 16px; flex-wrap: wrap">
      <div style="flex: 1">
        <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 8px">🔄 AI Recovery Plan Available</div>
        <p style="color: var(--text-secondary); font-size: 0.9rem; margin: 0">
          Your project is ${currentStats.status === 'behind' ? 'behind schedule' : 'at risk'}. 
          AI can reschedule your remaining ${currentStats.remaining_tasks} tasks to meet your deadline.
        </p>
      </div>
      <div style="display: flex; gap: 8px; flex-shrink: 0">
        <button class="btn btn-primary btn-sm" onclick="triggerReplan('delayed')">🔄 Auto Re-plan</button>
        <button class="btn btn-ghost btn-sm" onclick="document.getElementById('replan-section').remove()">Dismiss</button>
      </div>
    </div>
  `;
  container.insertBefore(section, container.firstChild);
}

// ─── TASK ACTIONS ────────────────────────────────────────────────────────────

async function markTaskDone(taskId) {
  const taskEls = document.querySelectorAll(`#task-${taskId}, #task-row-${taskId}`);
  taskEls.forEach(el => el.classList.add('completed'));

  try {
    const result = await window.API.completeTask(taskId);
    currentTasks = currentTasks.map(t => t.id === taskId ? { ...t, status: 'completed' } : t);
    currentStats = result.project_status;

    window.App.showToast('Task complete! ✅', 'Keep it up!', 'success');
    refreshPage();
  } catch (err) {
    window.App.showToast('Failed to update task', err.message, 'error');
  }
}

async function markTaskSkip(taskId) {
  try {
    const result = await window.API.skipTask(taskId);
    currentTasks = currentTasks.map(t => t.id === taskId ? { ...t, status: 'skipped' } : t);

    if (result.needs_replan) {
      window.App.showToast('Task skipped', result.replan_suggestion || '', 'warning');
    } else {
      window.App.showToast('Task skipped', '', 'info');
    }
    refreshPage();
  } catch (err) {
    window.App.showToast('Failed to skip task', err.message, 'error');
  }
}

async function markTaskDelay(taskId) {
  try {
    const result = await window.API.delayTask(taskId);
    currentTasks = currentTasks.map(t => t.id === taskId ? { ...t, status: 'delayed' } : t);

    if (result.needs_replan) {
      window.App.showToast('Task delayed', 'AI can re-plan your project.', 'warning');
    } else {
      window.App.showToast('Task delayed', '', 'info');
    }
    refreshPage();
  } catch (err) {
    window.App.showToast('Failed to delay task', err.message, 'error');
  }
}

async function toggleTask(taskId, currentStatus) {
  if (currentStatus === 'completed') return;
  await markTaskDone(taskId);
}

// ─── REPLAN ──────────────────────────────────────────────────────────────────

async function triggerReplan(reason = 'manual') {
  const btn = event.target;
  window.App.setButtonLoading(btn, true);

  try {
    const result = await window.API.replanProject(currentProject.id, reason);
    window.App.showToast('🔄 Re-planned!', result.replan?.replan_summary || 'Your schedule has been updated.', 'success');

    // Reload page data
    const data = await window.API.getProject(currentProject.id);
    currentProject = data.project;
    currentTasks = data.tasks;
    currentStats = data.stats;
    renderProjectHeader();
    renderOverviewTab();
    renderTasksTab();
    loadInsightsTab();
  } catch (err) {
    window.App.showToast('Re-plan failed', err.message, 'error');
  } finally {
    window.App.setButtonLoading(btn, false);
  }
}

// ─── TAB SWITCHING ───────────────────────────────────────────────────────────

function switchTab(tabName) {
  activeTab = tabName;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  const btn = document.getElementById(`tab-${tabName}`);
  const panel = document.getElementById(`panel-${tabName}`);
  if (btn) btn.classList.add('active');
  if (panel) panel.classList.add('active');

  if (tabName === 'insights') loadInsightsTab();
}

// ─── AUTO DETECT DELAYS ──────────────────────────────────────────────────────

async function autoDetectDelays(projectId) {
  try {
    const result = await window.API.detectDelays(projectId);
    const insights = result.insights;

    // Update AI insights if insights tab is open
    if (activeTab === 'insights') loadInsightsTab();

    // Show banner if project is behind
    if (insights.status === 'behind' || insights.status === 'at_risk') {
      const banner = document.getElementById('delay-banner');
      if (banner) {
        banner.style.display = 'flex';
        banner.querySelector('.banner-msg').textContent =
          `${insights.status === 'behind' ? '🔴' : '⚠️'} ${insights.coach_message}`;
      }
    }
  } catch (err) {
    console.log('[FinishAI] Delay detection skipped:', err.message);
  }
}

// ─── SKELETON LOADING ────────────────────────────────────────────────────────

function showProjectSkeleton() {
  document.getElementById('project-title').innerHTML = '<div class="skeleton" style="width: 300px; height: 32px;"></div>';
}

// ─── REFRESH ─────────────────────────────────────────────────────────────────

function refreshPage() {
  renderProjectHeader();
  if (activeTab === 'overview') renderOverviewTab();
  if (activeTab === 'tasks') renderTasksTab();
  if (activeTab === 'timeline') renderTimelineTab();
}

// ─── PAGE INIT ───────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', initProjectPage);

// Expose for inline onclick handlers
window.switchTab = switchTab;
window.toggleMilestone = toggleMilestone;
window.markTaskDone = markTaskDone;
window.markTaskSkip = markTaskSkip;
window.markTaskDelay = markTaskDelay;
window.toggleTask = toggleTask;
window.triggerReplan = triggerReplan;
window.renderTasksTab = renderTasksTab;
