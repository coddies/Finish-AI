/**
 * FinishAI — Roadmap & Resources Visualizer Logic
 * Handles interactive timeline, phase resource panels, and full resource library filtering.
 */

let currentProject = null;
let currentTasks = [];
let selectedPhaseId = null;
let currentResourceFilter = 'all';

document.addEventListener('DOMContentLoaded', initRoadmapPage);

async function initRoadmapPage() {
  const params = new URLSearchParams(window.location.search);
  const projectId = params.get('id');

  if (!projectId) {
    document.getElementById('roadmap-content').innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">No Project Specified</div>
        <p class="empty-state-subtitle">Please select a project from your dashboard to view its roadmap.</p>
        <a href="dashboard.html" class="btn btn-primary mt-16">← Back to Dashboard</a>
      </div>
    `;
    return;
  }

  try {
    const data = await window.API.getProject(projectId);
    currentProject = data.project;
    currentTasks = data.tasks || [];

    // Set navigation back links
    const backBtn = document.getElementById('back-to-project');
    if (backBtn) backBtn.href = `project.html?id=${currentProject.id}`;
    const overviewBtn = document.getElementById('btn-project-overview');
    if (overviewBtn) overviewBtn.href = `project.html?id=${currentProject.id}`;

    // Select first milestone by default if available
    if (currentProject.milestones && currentProject.milestones.length > 0) {
      selectedPhaseId = currentProject.milestones[0].id;
    }

    renderRoadmapPage();
  } catch (err) {
    console.error('[FinishAI Roadmap Error]:', err);
    document.getElementById('roadmap-content').innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">❌</div>
        <div class="empty-state-title">Failed to load roadmap</div>
        <p class="empty-state-subtitle">${err.message}</p>
        <a href="dashboard.html" class="btn btn-primary mt-16">← Back to Dashboard</a>
      </div>
    `;
  }
}

function renderRoadmapPage() {
  renderTopSection();
  renderTimelineNodes();
  if (selectedPhaseId) {
    const selectedMilestone = currentProject.milestones.find(m => m.id === selectedPhaseId);
    if (selectedMilestone) renderPhaseResourcesPanel(selectedMilestone);
  }
  renderAllResourcesLibrary();
}

function renderTopSection() {
  const { name, description, type, emoji, deadline, status, tools_needed, total_resources, milestones } = currentProject;
  const days = window.App.daysRemaining(deadline);

  document.getElementById('roadmap-top-title').textContent = `${emoji || '📋'} ${name} — Roadmap`;
  document.getElementById('roadmap-project-title').textContent = `${emoji || '📋'} ${name}`;
  document.getElementById('roadmap-project-desc').textContent = description || 'No description provided.';
  
  document.getElementById('project-type-badge').innerHTML = `<span class="badge badge-info">${type}</span>`;
  document.getElementById('project-status-badge').innerHTML = window.App.statusBadge(status);
  document.getElementById('project-deadline').textContent = `${days > 0 ? days : 0} days remaining`;

  // Stats counters
  let totalResCount = total_resources || 0;
  if (!totalResCount && milestones) {
    totalResCount = milestones.reduce((sum, m) => sum + (m.resources ? m.resources.length : 0), 0);
  }
  document.getElementById('stat-resources-count').textContent = totalResCount;
  document.getElementById('stat-phases-count').textContent = milestones ? milestones.length : 0;

  // Tools needed
  if (tools_needed && tools_needed.length > 0) {
    const toolsContainer = document.getElementById('tools-needed-container');
    const toolsList = document.getElementById('tools-needed-list');
    if (toolsContainer && toolsList) {
      toolsContainer.style.display = 'block';
      toolsList.innerHTML = tools_needed.map(tool => `
        <span style="background: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.35); color: #C4B5FD; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">
          🛠️ ${tool}
        </span>
      `).join('');
    }
  }
}

function renderTimelineNodes() {
  const container = document.getElementById('timeline-nodes-container');
  if (!container || !currentProject.milestones) return;

  const today = new Date().toISOString().split('T')[0];
  let firstPendingFound = false;

  container.innerHTML = currentProject.milestones.map((m, i) => {
    const milestoneTasks = currentTasks.filter(t => t.milestone_id === m.id);
    const completed = milestoneTasks.filter(t => t.status === 'completed').length;
    const pct = milestoneTasks.length ? (completed / milestoneTasks.length) * 100 : 0;

    // Determine status: completed / current / future
    let nodeStatus = 'future';
    let statusText = '⏳ Future Phase';
    let dotClass = '';
    let dotContent = i + 1;

    if (pct === 100 || (completed > 0 && completed === milestoneTasks.length)) {
      nodeStatus = 'completed';
      statusText = '✅ Completed';
      dotClass = 'completed';
      dotContent = '✓';
    } else if (!firstPendingFound) {
      nodeStatus = 'current';
      statusText = '🔄 Current Active Phase';
      dotClass = 'current';
      firstPendingFound = true;
    }

    const isActiveNode = selectedPhaseId === m.id ? 'active-node' : '';
    const resCount = m.resources ? m.resources.length : 0;

    return `
      <div class="roadmap-timeline-node ${isActiveNode}" onclick="selectPhase('${m.id}')">
        <!-- Connecting line (except last item) -->
        ${i < currentProject.milestones.length - 1 ? '<div class="roadmap-timeline-line"></div>' : ''}
        
        <!-- Timeline Dot -->
        <div class="roadmap-timeline-dot ${dotClass}">${dotContent}</div>

        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
          <div>
            <div style="font-size: 0.78rem; font-weight: 700; color: ${nodeStatus === 'current' ? '#3B82F6' : nodeStatus === 'completed' ? '#10B981' : 'var(--text-secondary)'}; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">
              Phase ${i + 1} • ${statusText}
            </div>
            <div style="font-weight: 700; font-size: 1.1rem; color: var(--text-primary);">${m.name}</div>
            ${m.description ? `<div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">${m.description}</div>` : ''}
          </div>
          <div style="text-align: right; flex-shrink: 0;">
            <div style="font-size: 0.78rem; color: var(--text-secondary);">Target Date</div>
            <div style="font-weight: 600; font-size: 0.9rem; color: var(--text-primary);">${window.App.formatDate(m.target_date)}</div>
          </div>
        </div>

        <!-- Progress and resource count -->
        <div style="margin-top: 14px;">
          <div class="progress-bar-container" style="height: 6px;">
            <div class="progress-bar-fill ${window.App.progressColor(pct)}" style="width: ${pct}%"></div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
            <span style="font-size: 0.8rem; color: var(--text-secondary);">
              ${completed}/${milestoneTasks.length} tasks complete
            </span>
            <span class="badge badge-primary" style="font-size: 0.75rem; background: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3);">
              📚 ${resCount} resources
            </span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function selectPhase(phaseId) {
  selectedPhaseId = phaseId;
  renderTimelineNodes();
  const selectedMilestone = currentProject.milestones.find(m => m.id === phaseId);
  if (selectedMilestone) renderPhaseResourcesPanel(selectedMilestone);
}

function renderPhaseResourcesPanel(milestone) {
  const panel = document.getElementById('phase-resources-panel');
  const badge = document.getElementById('selected-phase-badge');
  if (!panel) return;

  if (badge) {
    const idx = currentProject.milestones.findIndex(m => m.id === milestone.id);
    badge.textContent = `Viewing Phase ${idx + 1}: ${milestone.name}`;
  }

  const resources = milestone.resources || [];
  const videos = resources.filter(r => r.type === 'youtube');
  const websites = resources.filter(r => r.type === 'website');
  const tools = resources.filter(r => r.type === 'tool');
  const articles = resources.filter(r => r.type === 'article');

  const renderResourceGroup = (title, icon, list) => {
    if (!list || list.length === 0) return '';
    return `
      <div class="resource-group-title">${icon} ${title} (${list.length})</div>
      <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px;">
        ${list.map(res => `
          <div class="resource-card">
            <div style="display: flex; align-items: flex-start; gap: 12px; flex: 1;">
              <span style="font-size: 1.4rem;">${icon}</span>
              <div>
                <div style="font-weight: 700; font-size: 0.95rem; color: var(--text-primary);">${res.title}</div>
                ${res.description ? `<div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 3px; line-height: 1.4;">${res.description}</div>` : ''}
              </div>
            </div>
            ${res.url ? `
              <a href="${res.url}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="flex-shrink: 0; padding: 6px 14px; font-size: 0.8rem; text-decoration: none;">
                Open →
              </a>
            ` : ''}
          </div>
        `).join('')}
      </div>
    `;
  };

  const checkpointHtml = milestone.checkpoint ? `
    <div style="margin-top: 24px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 18px;">
      <h5 style="color: var(--text-primary); font-size: 0.95rem; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
        ✅ How to know you're ready (Checkpoint)
      </h5>
      <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; padding: 14px 18px; color: #10B981; font-size: 0.9rem; font-weight: 500; line-height: 1.5;">
        ${milestone.checkpoint}
      </div>
    </div>
  ` : '';

  const tipsHtml = (milestone.tips && milestone.tips.length > 0) ? `
    <div style="margin-top: 20px;">
      <h5 style="color: var(--text-primary); font-size: 0.95rem; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
        💡 Phase Study / Execution Tips
      </h5>
      <div style="display: flex; flex-wrap: wrap; gap: 8px;">
        ${milestone.tips.map(tip => `
          <span style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60A5FA; padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 500;">
            💡 ${tip}
          </span>
        `).join('')}
      </div>
    </div>
  ` : '';

  const warningsHtml = (milestone.warnings && milestone.warnings.length > 0) ? `
    <div style="margin-top: 20px;">
      <h5 style="color: var(--text-primary); font-size: 0.95rem; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
        ⚠️ Common Mistakes to Avoid
      </h5>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${milestone.warnings.map(warn => `
          <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); color: #FBBF24; padding: 12px 16px; border-radius: 8px; font-size: 0.88rem; font-weight: 500;">
            ⚠️ ${warn}
          </div>
        `).join('')}
      </div>
    </div>
  ` : '';

  if (resources.length === 0 && !milestone.checkpoint && (!milestone.tips || !milestone.tips.length)) {
    panel.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📚</div>
        <div class="empty-state-title">No Resources listed for this phase</div>
        <p class="empty-state-subtitle">Check the Tasks tab on the Project Overview page for specific daily instructions.</p>
      </div>
    `;
    return;
  }

  panel.innerHTML = `
    <div style="margin-bottom: 18px;">
      <h4 style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary); margin-bottom: 4px;">${milestone.name}</h4>
      <p style="font-size: 0.9rem; color: var(--text-secondary);">${milestone.description || 'Complete these resources and tasks to finish the phase.'}</p>
    </div>
    ${renderResourceGroup('Videos & Channels', '📺', videos)}
    ${renderResourceGroup('Websites & Platforms', '🌐', websites)}
    ${renderResourceGroup('Recommended Tools', '🛠️', tools)}
    ${renderResourceGroup('Guides & Articles', '📄', articles)}
    ${checkpointHtml}
    ${tipsHtml}
    ${warningsHtml}
  `;
}

function renderAllResourcesLibrary() {
  const grid = document.getElementById('all-resources-grid');
  if (!grid || !currentProject.milestones) return;

  // Collect all resources across all phases
  let allResources = [];
  currentProject.milestones.forEach((m, idx) => {
    if (m.resources && m.resources.length > 0) {
      m.resources.forEach(res => {
        allResources.push({
          ...res,
          phaseName: m.name,
          phaseNumber: idx + 1
        });
      });
    }
  });

  // Filter
  let filtered = allResources;
  if (currentResourceFilter !== 'all') {
    filtered = allResources.filter(r => r.type === currentResourceFilter);
  }

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1; padding: 40px 0;">
        <div class="empty-state-icon">📭</div>
        <div class="empty-state-title">No resources found</div>
        <p class="empty-state-subtitle">No resources match the selected filter category.</p>
      </div>
    `;
    return;
  }

  const icons = { youtube: '📺', website: '🌐', tool: '🛠️', article: '📄' };

  grid.innerHTML = filtered.map(res => {
    const icon = icons[res.type] || '🌐';
    return `
      <div class="glass-card-sm" style="padding: 16px; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; border-radius: 12px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); transition: all 0.2s ease;">
        <div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <span class="badge badge-muted" style="font-size: 0.72rem; color: var(--secondary); background: rgba(139, 92, 246, 0.12); border: 1px solid rgba(139, 92, 246, 0.25);">
              Phase ${res.phaseNumber}: ${res.phaseName}
            </span>
            <span style="font-size: 1.2rem;">${icon}</span>
          </div>
          <div style="font-weight: 700; font-size: 0.98rem; color: var(--text-primary); margin-bottom: 4px;">${res.title}</div>
          ${res.description ? `<div style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.4;">${res.description}</div>` : ''}
        </div>
        <div style="display: flex; justify-content: flex-end; margin-top: 8px;">
          ${res.url ? `
            <a href="${res.url}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="padding: 6px 14px; font-size: 0.8rem; text-decoration: none; width: 100%; text-align: center;">
              Open Resource →
            </a>
          ` : `
            <span style="font-size: 0.78rem; color: var(--text-muted); font-style: italic;">No direct link available</span>
          `}
        </div>
      </div>
    `;
  }).join('');
}

function filterResources(type) {
  currentResourceFilter = type;
  document.querySelectorAll('#resource-filters .filter-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = Array.from(document.querySelectorAll('#resource-filters .filter-btn')).find(b => {
    if (type === 'all' && b.textContent.includes('All')) return true;
    if (type === 'youtube' && b.textContent.includes('Videos')) return true;
    if (type === 'website' && b.textContent.includes('Websites')) return true;
    if (type === 'tool' && b.textContent.includes('Tools')) return true;
    if (type === 'article' && b.textContent.includes('Articles')) return true;
    return false;
  });
  if (activeBtn) activeBtn.classList.add('active');

  renderAllResourcesLibrary();
}

window.selectPhase = selectPhase;
window.filterResources = filterResources;
