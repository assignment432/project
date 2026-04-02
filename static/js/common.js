// common.js - Shared utilities for all pages

function showToast(message, type = 'success') {
  let toast = document.getElementById('globalToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'globalToast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  const icons = { success: '✓', error: '✕', warning: '⚠' };
  toast.innerHTML = `<span>${icons[type] || '✓'}</span><span>${message}</span>`;
  toast.className = `toast ${type} show`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('show'), 3500);
}

function openModal(id) {
  document.getElementById(id).classList.add('open');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

function formatDeadline(isoStr) {
  if (!isoStr) return 'No deadline';
  const d = new Date(isoStr);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true
  });
}

function getDeadlineStatus(isoStr) {
  if (!isoStr) return { label: 'No deadline', cls: '' };
  const now = new Date();
  const d = new Date(isoStr);
  const diff = d - now;
  const hours = diff / 3600000;
  if (diff < 0) return { label: 'Expired', cls: 'deadline-urgent' };
  if (hours <= 1) return { label: `${Math.round(hours * 60)}m left`, cls: 'deadline-urgent' };
  if (hours <= 24) return { label: `${Math.round(hours)}h left`, cls: 'deadline-warning' };
  return { label: formatDeadline(isoStr), cls: '' };
}

async function apiCall(url, options = {}) {
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    });
    return await res.json();
  } catch (e) {
    return { success: false, message: 'Network error' };
  }
}

// Close modal on overlay click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

// Logout
function logout() {
  window.location.href = '/logout';
}
