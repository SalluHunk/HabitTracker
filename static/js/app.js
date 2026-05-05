/* ── HabitFlow — frontend JS ─────────────────────────────── */

/* ── Date display ───────────────────────────────────────── */
(function updateSidebarDate() {
  const now   = new Date();
  const days  = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  const months= ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const el1   = document.getElementById('sb-day');
  const el2   = document.getElementById('sb-date');
  if (el1) el1.textContent = days[now.getDay()];
  if (el2) el2.textContent = `${months[now.getMonth()]} ${now.getDate()}, ${now.getFullYear()}`;
})();

/* ── Modal helpers ──────────────────────────────────────── */
function openModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.add('open'); document.body.style.overflow = 'hidden'; }
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.remove('open'); document.body.style.overflow = ''; }
}
function backdropClose(event, id) {
  if (event.target.id === id) closeModal(id);
}

/* ── One-tap log toggle (AJAX) ──────────────────────────── */
async function toggleLog(habitId, btn) {
  btn.disabled = true;
  const card = document.getElementById(`card-${habitId}`);

  try {
    const resp = await fetch(`/habits/${habitId}/log`, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
    });
    const data = await resp.json();

    if (data.logged) {
      btn.classList.add('logged');
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Done Today';
      card && card.classList.add('done');
      // Update streak display
      const streakEl = card && card.querySelector('.streak-num');
      if (streakEl) { streakEl.textContent = data.streak; }
      const zeroEl = card && card.querySelector('.streak-zero');
      if (data.streak > 0 && zeroEl) {
        const streakWrap = zeroEl.closest('.hcard-streak');
        if (streakWrap) {
          streakWrap.innerHTML =
            `<span class="streak-num">${data.streak}</span><span class="streak-fire">🔥</span>`;
          if (data.streak >= 3) streakWrap.classList.add('hot');
        }
      }
      btn.classList.add('pulse');
      if (data.streak > 0 && data.streak % 7 === 0) spawnConfetti(btn);
      updateRing();
    } else {
      btn.classList.remove('logged');
      btn.innerHTML = '<i class="fa-regular fa-circle"></i> Log Today';
      card && card.classList.remove('done');
      // Reset streak if 0
      if (data.streak === 0) {
        const streakWrap = card && card.querySelector('.hcard-streak');
        if (streakWrap) {
          streakWrap.classList.remove('hot');
          streakWrap.innerHTML = '<span class="streak-zero">—</span>';
        }
      }
      updateRing();
    }
  } catch (e) {
    console.error('Log toggle failed:', e);
  } finally {
    btn.disabled = false;
    setTimeout(() => btn.classList.remove('pulse'), 500);
  }
}

/* ── Update completion ring after log ───────────────────── */
function updateRing() {
  const cards     = document.querySelectorAll('.habit-card');
  const total     = cards.length;
  const completed = document.querySelectorAll('.habit-card.done').length;
  const pct       = total ? Math.round(completed / total * 100) : 0;
  const ring      = document.getElementById('ringFg');
  const pctEl     = document.querySelector('.ring-pct');
  if (ring) {
    const circ = 2 * Math.PI * 34;
    ring.style.strokeDashoffset = circ * (1 - pct / 100);
  }
  if (pctEl) pctEl.textContent = `${pct}%`;
}

/* ── Confetti burst on milestone ────────────────────────── */
function spawnConfetti(anchor) {
  const colors = ['#6366f1','#10b981','#f59e0b','#ec4899','#3b82f6','#a855f7'];
  const rect   = anchor.getBoundingClientRect();
  for (let i = 0; i < 20; i++) {
    const el = document.createElement('div');
    el.className = 'confetti-piece';
    el.style.cssText = `
      left: ${rect.left + Math.random() * rect.width}px;
      top: ${rect.top}px;
      background: ${colors[Math.floor(Math.random() * colors.length)]};
      transform: rotate(${Math.random() * 360}deg);
      animation-delay: ${Math.random() * .3}s;
    `;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1600);
  }
}

/* ── Category defaults in Add Habit form ────────────────── */
const CAT_COLORS = {
  general: '#64748b', health: '#10b981', fitness: '#f59e0b',
  work: '#6366f1', learning: '#3b82f6', mindfulness: '#8b5cf6',
  social: '#ec4899', finance: '#14b8a6',
};
const CAT_ICONS = {
  general: '✨', health: '💊', fitness: '💪',
  work: '💼', learning: '📚', mindfulness: '🧘',
  social: '👥', finance: '💰',
};

function syncCategoryDefaults() {
  const cat   = document.getElementById('newCat');
  const color = document.getElementById('newColor');
  const icon  = document.getElementById('newIcon');
  if (!cat) return;
  const c = cat.value;
  if (color && !color._userEdited) color.value = CAT_COLORS[c] || '#64748b';
  if (icon  && !icon._userEdited)  icon.value  = CAT_ICONS[c]  || '✨';
}

document.addEventListener('DOMContentLoaded', () => {
  const color = document.getElementById('newColor');
  const icon  = document.getElementById('newIcon');
  if (color) color.addEventListener('input', () => { color._userEdited = true; });
  if (icon)  icon.addEventListener('input',  () => { icon._userEdited  = true; });
});

/* ── Calendar heatmap (habit detail) ───────────────────── */
function renderCalendarHeatmap(containerId, cells, color) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = '';

  cells.forEach(cell => {
    const el = document.createElement('div');
    el.className = 'hm-cell';
    el.title = cell.date;
    el.style.background = cell.done ? color : '#e2e8f0';
    if (cell.done) {
      el.style.boxShadow = `0 0 0 1px ${color}44`;
    }
    container.appendChild(el);
  });
}

/* ── Annual heatmap (analytics) ────────────────────────── */
function renderAnnualHeatmap(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = '';

  const maxCount = Math.max(1, ...data.map(d => d.count));
  const thresholds = [0, maxCount * .25, maxCount * .5, maxCount * .75];
  const colors = ['#e2e8f0', '#a7f3d0', '#34d399', '#059669'];

  data.forEach(item => {
    const el = document.createElement('div');
    el.className = 'hm-cell';
    el.style.width = '12px';
    el.style.height = '12px';
    el.title = `${item.date}: ${item.count} completion${item.count !== 1 ? 's' : ''}`;

    const idx = thresholds.filter(t => item.count > t).length - 1;
    el.style.background = item.count === 0 ? colors[0] : colors[Math.min(idx + 1, 3)];
    container.appendChild(el);
  });
}

/* ── Trend chart (habit detail) ─────────────────────────── */
function renderTrendChart(canvasId, trendData, color) {
  const ctx = document.getElementById(canvasId);
  if (!ctx || !trendData || !trendData.length) return;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: trendData.map(d => d.label),
      datasets: [{
        label: 'Completions',
        data: trendData.map(d => d.count),
        backgroundColor: trendData.map((_, i) =>
          i === trendData.length - 1
            ? color
            : color + '66'
        ),
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.raw} day${ctx.raw !== 1 ? 's' : ''}` },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: { stepSize: 1, font: { size: 11 } },
          beginAtZero: true,
        },
      },
    },
  });
}

/* ── Category donut chart (analytics) ───────────────────── */
function renderCategoryChart(canvasId, catData) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const labels = Object.keys(catData);
  const values = Object.values(catData);
  const palette = {
    general: '#94a3b8', health: '#10b981', fitness: '#f59e0b',
    work: '#6366f1', learning: '#3b82f6', mindfulness: '#8b5cf6',
    social: '#ec4899', finance: '#14b8a6',
  };
  const colors = labels.map(l => palette[l] || '#94a3b8');

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }],
    },
    options: {
      responsive: true,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'right',
          labels: { font: { size: 11 }, boxWidth: 12, padding: 10 },
        },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw} habit${ctx.raw !== 1 ? 's' : ''}` },
        },
      },
    },
  });
}

/* ── Weekly bar chart (analytics) ───────────────────────── */
function renderWeeklyChart(canvasId, weeklyData) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const entries = Object.entries(weeklyData);
  const labels  = entries.map(([d]) => {
    const date = new Date(d);
    return date.toLocaleDateString('en', { weekday: 'short' });
  });
  const values = entries.map(([, v]) => v);
  const maxVal = Math.max(1, ...values);

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Completions',
        data: values,
        backgroundColor: values.map(v => {
          const intensity = v / maxVal;
          return `rgba(99,102,241,${0.25 + intensity * 0.75})`;
        }),
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: { stepSize: 1, font: { size: 11 } },
          beginAtZero: true,
        },
      },
    },
  });
}
