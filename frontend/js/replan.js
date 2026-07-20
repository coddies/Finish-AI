/**
 * FinishAI — replan.js
 * Re-planning UI logic. Shows re-plan results, accepts/dismisses changes,
 * and provides a summary of what the AI changed.
 */

// ─── SHOW REPLAN RESULTS ─────────────────────────────────────────────────────

function showReplanResults(replanData, tasksUpdated) {
  const container = document.getElementById('replan-results');
  if (!container) return;

  const { replan_summary, tasks_removed, tasks_deprioritized, recovery_message } = replanData;

  container.innerHTML = `
    <div class="replan-card scale-in">
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px">
        <div style="font-size: 2rem">🔄</div>
        <div>
          <div style="font-weight: 700; font-size: 1.1rem">AI Recovery Plan Applied</div>
          <div style="color: var(--text-muted); font-size: 0.875rem">${tasksUpdated} tasks rescheduled</div>
        </div>
      </div>

      <div style="background: var(--bg-card); border-radius: 10px; padding: 16px; margin-bottom: 16px">
        <div style="font-weight: 600; margin-bottom: 8px; font-size: 0.875rem; color: var(--text-muted)">WHAT CHANGED</div>
        <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; margin: 0">${replan_summary}</p>
      </div>

      ${tasks_removed?.length ? `
        <div style="margin-bottom: 12px">
          <div style="font-size: 0.8rem; font-weight: 700; color: var(--error); margin-bottom: 8px">❌ REMOVED (low priority, insufficient time)</div>
          ${tasks_removed.map(t => `<div style="padding: 6px 12px; background: var(--error-bg); border-radius: 6px; font-size: 0.875rem; margin-bottom: 4px; color: var(--text-secondary)">${t}</div>`).join('')}
        </div>
      ` : ''}

      ${tasks_deprioritized?.length ? `
        <div style="margin-bottom: 16px">
          <div style="font-size: 0.8rem; font-weight: 700; color: var(--warning); margin-bottom: 8px">⬇️ DEPRIORITIZED</div>
          ${tasks_deprioritized.map(t => `<div style="padding: 6px 12px; background: var(--warning-bg); border-radius: 6px; font-size: 0.875rem; margin-bottom: 4px; color: var(--text-secondary)">${t}</div>`).join('')}
        </div>
      ` : ''}

      <div style="background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2); border-radius: 10px; padding: 16px">
        <div style="font-weight: 600; margin-bottom: 8px; font-size: 0.875rem; color: var(--success)">💪 RECOVERY PLAN</div>
        <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; margin: 0">${recovery_message}</p>
      </div>
    </div>
  `;
}

// ─── DISMISS REPLAN ──────────────────────────────────────────────────────────

function dismissReplanSection() {
  const section = document.getElementById('replan-section');
  if (section) {
    section.style.animation = 'fadeOut 0.3s ease forwards';
    setTimeout(() => section.remove(), 300);
  }
}

// ─── REPLAN HISTORY ITEM ─────────────────────────────────────────────────────

function renderReplanHistoryItem(item, index) {
  return `
    <div style="padding: 14px 16px; background: var(--bg-card); border-radius: 10px; margin-bottom: 8px">
      <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
        <span class="badge badge-info">Re-plan ${index + 1}</span>
        <span style="font-size: 0.8rem; color: var(--text-muted)">${item.date}</span>
      </div>
      <div style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 8px">${item.summary}</div>
      <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px">
        Reason: ${item.reason} · ${item.tasks_updated || 0} tasks rescheduled
      </div>
    </div>
  `;
}

// Expose globals
window.showReplanResults = showReplanResults;
window.dismissReplanSection = dismissReplanSection;
window.renderReplanHistoryItem = renderReplanHistoryItem;
