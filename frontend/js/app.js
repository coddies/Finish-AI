/**
 * FinishAI — app.js
 * Main application logic: toast notifications, scroll reveal,
 * sidebar navigation, user state, shared utilities.
 */

// ─── TOAST NOTIFICATIONS ─────────────────────────────────────────────────────

function showToast(title, message = '', type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const container = document.getElementById('toast-container') || createToastContainer();

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || '🔔'}</span>
    <div class="toast-text">
      <div class="toast-title">${title}</div>
      ${message ? `<div class="toast-msg">${message}</div>` : ''}
    </div>
    <button onclick="this.closest('.toast').remove()" style="
      background: none; border: none; color: var(--text-muted);
      cursor: pointer; font-size: 1rem; margin-left: 8px; padding: 0;
    ">✕</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.className = 'toast-container';
  document.body.appendChild(container);
  return container;
}

// ─── SCROLL REVEAL ───────────────────────────────────────────────────────────

function initScrollReveal() {
  const reveals = document.querySelectorAll('.reveal');
  if (!reveals.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  reveals.forEach(el => observer.observe(el));
}

// ─── DOCK NAVIGATION ─────────────────────────────────────────────────────────

function initDock() {
  const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
  const dockItems = document.querySelectorAll('.dock-item');

  dockItems.forEach(item => {
    const href = item.getAttribute('href') || '';
    if (href && currentPage.includes(href.replace('.html', ''))) {
      item.classList.add('active');
    } else if (href && !currentPage.includes(href.replace('.html', ''))) {
      item.classList.remove('active');
    }
  });
}

// ─── DATE UTILITIES ──────────────────────────────────────────────────────────

function formatDate(dateStr) {
  if (!dateStr) return 'No date';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function daysRemaining(deadlineStr) {
  if (!deadlineStr) return 0;
  const now = new Date();
  const deadline = new Date(deadlineStr);
  const diff = Math.ceil((deadline - now) / (1000 * 60 * 60 * 24));
  return diff;
}

function todayStr() {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });
}

function greetingByTime() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

// ─── STATUS HELPERS ──────────────────────────────────────────────────────────

function statusBadge(status) {
  const map = {
    on_track: '<span class="badge badge-success">✅ On Track</span>',
    at_risk: '<span class="badge badge-warning">⚠️ At Risk</span>',
    behind: '<span class="badge badge-error">🔴 Behind</span>',
  };
  return map[status] || '<span class="badge badge-muted">Unknown</span>';
}

function priorityDot(priority) {
  const colors = { high: 'var(--error)', medium: 'var(--warning)', low: 'var(--success)' };
  return `<span class="priority-dot ${priority}" title="${priority} priority"></span>`;
}

function progressColor(pct) {
  if (pct >= 70) return 'success';
  if (pct >= 40) return '';  // Default gradient
  return 'warning';
}

// ─── PROGRESS CIRCLE ─────────────────────────────────────────────────────────

function renderProgressCircle(container, percent, size = 120) {
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  container.innerHTML = `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <defs>
        <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" style="stop-color:#3B82F6" />
          <stop offset="100%" style="stop-color:#8B5CF6" />
        </linearGradient>
      </defs>
      <circle class="progress-circle-bg" cx="${size/2}" cy="${size/2}" r="${radius}" />
      <circle
        class="progress-circle-fill"
        cx="${size/2}" cy="${size/2}" r="${radius}"
        stroke-dasharray="${circumference}"
        stroke-dashoffset="${offset}"
        style="stroke: url(#progressGradient)"
      />
    </svg>
    <div class="progress-circle-text">
      <span style="font-size: ${size > 100 ? '1.4rem' : '1rem'}; font-weight: 800; color: var(--text-primary)">${Math.round(percent)}%</span>
      <span style="font-size: 0.7rem; color: var(--text-muted)">done</span>
    </div>
  `;
}

// ─── CONFETTI ────────────────────────────────────────────────────────────────

function launchConfetti() {
  const colors = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#F8FAFC'];
  const container = document.createElement('div');
  container.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:9999;overflow:hidden;';
  document.body.appendChild(container);

  for (let i = 0; i < 80; i++) {
    const piece = document.createElement('div');
    const size = Math.random() * 10 + 6;
    const color = colors[Math.floor(Math.random() * colors.length)];
    const left = Math.random() * 100;
    const delay = Math.random() * 0.8;
    const duration = Math.random() * 2 + 2;
    piece.style.cssText = `
      position: absolute;
      width: ${size}px; height: ${size}px;
      background: ${color};
      border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
      left: ${left}%;
      top: -20px;
      animation: confettiFall ${duration}s ${delay}s ease forwards;
    `;
    container.appendChild(piece);
  }

  setTimeout(() => container.remove(), 4000);
}

// ─── LOADING STATE ───────────────────────────────────────────────────────────

function setButtonLoading(btn, loading = true, originalText = '') {
  if (loading) {
    btn.dataset.originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<div class="loader" style="width:18px;height:18px;"></div> Loading...`;
  } else {
    btn.disabled = false;
    btn.innerHTML = btn.dataset.originalText || originalText;
  }
}

// ─── INIT ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initScrollReveal();
  initDock();
});

// Make everything global
window.App = {
  showToast,
  formatDate,
  daysRemaining,
  todayStr,
  greetingByTime,
  statusBadge,
  priorityDot,
  progressColor,
  renderProgressCircle,
  launchConfetti,
  setButtonLoading,
};
