/* ─── Lumora Dev · Frontend Script ─────────────────────────────── */
'use strict';

// ── DOM refs ────────────────────────────────────────────────────────
const sidebar        = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const menuBtn        = document.getElementById('menuBtn');
const sidebarClose   = document.getElementById('sidebarClose');
const messageInput   = document.getElementById('messageInput');
const sendBtn        = document.getElementById('sendBtn');
const messagesEl     = document.getElementById('messages');
const welcomeEl      = document.getElementById('welcome');
const chatArea       = document.getElementById('chatArea');
const newChatBtn     = document.getElementById('newChatBtn');
const settingsBtn    = document.getElementById('settingsBtn');
const navSettingsBtn = document.getElementById('navSettingsBtn');
const settingsModal  = document.getElementById('settingsModal');
const modalClose     = document.getElementById('modalClose');
const chatList       = document.getElementById('chatList');
const attachBtn      = document.getElementById('attachBtn');

// ── State ────────────────────────────────────────────────────────────
let isTyping     = false;
let messageCount = 0;

// ── API base URL ─────────────────────────────────────────────────────
const API_BASE = window.location.origin;

// ── Active user project (isolated from Lumora source) ─────────────────
const WS_KEY = 'lumora_active_workspace';
let currentWorkspace = null; // { id, name, ... }

function loadStoredWorkspace() {
  try {
    const raw = localStorage.getItem(WS_KEY);
    if (raw) currentWorkspace = JSON.parse(raw);
  } catch (_) { currentWorkspace = null; }
}
function persistWorkspace(ws) {
  currentWorkspace = ws;
  try {
    if (ws) localStorage.setItem(WS_KEY, JSON.stringify(ws));
    else localStorage.removeItem(WS_KEY);
  } catch (_) {}
  updateProjectBadge();
}
function apiHeaders(extra = {}) {
  const h = { ...extra };
  if (currentWorkspace && currentWorkspace.id) {
    h['X-Lumora-Workspace'] = currentWorkspace.id;
  }
  return h;
}
function updateProjectBadge() {
  const el = document.getElementById('projectBadge');
  const nameEl = document.getElementById('projectBadgeName');
  const gen = document.getElementById('genProject');
  if (currentWorkspace && currentWorkspace.name) {
    if (el) el.hidden = false;
    if (nameEl) nameEl.textContent = currentWorkspace.name;
    if (gen) gen.textContent = currentWorkspace.name;
  } else {
    if (el) el.hidden = true;
    if (nameEl) nameEl.textContent = 'No project';
    if (gen) gen.textContent = 'None selected';
  }
}
loadStoredWorkspace();



// ── Sidebar ──────────────────────────────────────────────────────────
function openSidebar() {
  sidebar.classList.add('open');
  sidebarOverlay.classList.add('visible');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  sidebar.classList.remove('open');
  sidebarOverlay.classList.remove('visible');
  document.body.style.overflow = '';
}

menuBtn.addEventListener('click', openSidebar);
sidebarClose.addEventListener('click', closeSidebar);
sidebarOverlay.addEventListener('click', closeSidebar);

// ── Settings Modal ────────────────────────────────────────────────────
function openSettings() { settingsModal.classList.add('open'); }
function closeSettings() { settingsModal.classList.remove('open'); }

settingsBtn.addEventListener('click', openSettings);
navSettingsBtn.addEventListener('click', openSettings);
modalClose.addEventListener('click', closeSettings);
settingsModal.addEventListener('click', e => {
  if (e.target === settingsModal) closeSettings();
});

// ── Settings: tab switching ──────────────────────────────────────────
document.querySelectorAll('.settings-nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.settings-nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.settings-panel').forEach(p => p.classList.remove('active'));
    const panelId = 'panel' + btn.dataset.panel.charAt(0).toUpperCase() + btn.dataset.panel.slice(1);
    document.getElementById(panelId)?.classList.add('active');
    if (btn.dataset.panel === 'providers') loadProviderSettings();
  });
});

// ── Tab switching: also handle SCM lazy load ────────────────────────
const scmTab = document.querySelector('.sidebar-tab[data-tab="scm"]');
if (scmTab) {
  scmTab.addEventListener('click', () => {
    if (!document.getElementById('scmPanel').dataset.loaded) {
      loadSCM();
    }
  });
}

// ── Input auto-resize ─────────────────────────────────────────────────
messageInput.addEventListener('input', () => {
  messageInput.style.height = 'auto';
  messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
  sendBtn.disabled = !messageInput.value.trim();
});

// ── Send on Enter (Shift+Enter = newline) ──────────────────────────────
messageInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendBtn.disabled && !isTyping) sendMessage();
  }
});

sendBtn.addEventListener('click', () => {
  if (!sendBtn.disabled && !isTyping) sendMessage();
});

// ── Suggestion chips ──────────────────────────────────────────────────
document.querySelectorAll('.suggestion-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const prompt = chip.dataset.prompt;
    messageInput.value = prompt;
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
    sendBtn.disabled = false;
    sendMessage();
  });
});

// ── New Chat ───────────────────────────────────────────────────────────
newChatBtn.addEventListener('click', () => {
  clearChat();
  closeSidebar();
});

// ── Chat list items ────────────────────────────────────────────────────
chatList.addEventListener('click', e => {
  const item = e.target.closest('.chat-item');
  if (!item) return;
  document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
  item.classList.add('active');
  closeSidebar();
});

// ── Attach button (placeholder) ────────────────────────────────────────
attachBtn.addEventListener('click', () => {
  showToast('File attachment coming soon ✨');
});

// ── Core chat functions ─────────────────────────────────────────────────
function clearChat() {
  messagesEl.innerHTML = '';
  welcomeEl.style.display = '';
  messageCount = 0;
  messageInput.value = '';
  messageInput.style.height = 'auto';
  sendBtn.disabled = true;
}

function hideWelcome() {
  if (welcomeEl.style.display === 'none') return;
  welcomeEl.style.display = 'none';
}

function formatTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHTML(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderMarkdown(text) {
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code class="lang-${lang}">${escapeHTML(code.trim())}</code></pre>`
  );
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
  text = text.replace(/^\d+\.\s+(.+)/gm, '<li>$1</li>');
  text = text.replace(/(<li>.*<\/li>)/s, '<ol>$1</ol>');
  text = text.replace(/^[-•]\s+(.+)/gm, '<li>$1</li>');
  text = text.split(/\n{2,}/).map(block => {
    if (block.startsWith('<pre>') || block.startsWith('<ol>') || block.startsWith('<ul>') || block.startsWith('<li>')) return block;
    const lines = block.split('\n').map(l => l.trim()).filter(Boolean);
    return lines.length ? `<p>${lines.join('<br>')}</p>` : '';
  }).join('');
  return text;
}

function appendMessage(role, text) {
  hideWelcome();
  messageCount++;
  const row = document.createElement('div');
  row.className = `message-row ${role}`;
  if (role === 'ai') {
    row.innerHTML = `
      <div class="msg-avatar ai">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#A78BFA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div>
        <div class="msg-bubble">${renderMarkdown(text)}</div>
        <div class="msg-meta">${formatTime()}</div>
      </div>
    `;
  } else {
    row.innerHTML = `
      <div>
        <div class="msg-bubble">${escapeHTML(text).replace(/\n/g, '<br>')}</div>
        <div class="msg-meta">${formatTime()}</div>
      </div>
      <div class="msg-avatar user-av">Y</div>
    `;
  }
  messagesEl.appendChild(row);
  scrollToBottom();
  return row;
}

function showTypingIndicator() {
  const row = document.createElement('div');
  row.className = 'typing-row';
  row.id = 'typingIndicator';
  row.innerHTML = `
    <div class="msg-avatar ai">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#A78BFA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    <div class="typing-bubble">
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    </div>
  `;
  messagesEl.appendChild(row);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function scrollToBottom() {
  chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'smooth' });
}

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || isTyping) return;
  isTyping = true;
  sendBtn.disabled = true;
  messageInput.value = '';
  messageInput.style.height = 'auto';
  appendMessage('user', text);
  await delay(300);
  showTypingIndicator();
  try {
    const longTask = /build me|landing page|website|scaffold|full stack|create an app|make a website/i.test(text);
    // Auto-create a project when user asks to build something and none is selected
    if (longTask && !currentWorkspace) {
      const nameMatch = text.match(/(?:named|called|for)\s+([A-Za-z0-9][A-Za-z0-9 \-]{1,40})/i);
      const pname = (nameMatch ? nameMatch[1] : 'New Project').trim().slice(0, 40);
      try {
        const cr = await fetch(`${API_BASE}/workspaces`, {
          method: 'POST',
          headers: apiHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ name: pname, description: text.slice(0, 120), template: 'html', framework: 'html' }),
        });
        if (cr.ok) {
          const created = await cr.json();
          persistWorkspace({ id: created.id, name: pname });
        }
      } catch (_) {}
    }
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: apiHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        message: text,
        async_mode: longTask,
        plan: true,
        workspace_id: currentWorkspace?.id || '',
        thread_id: currentWorkspace?.id ? `ws-${currentWorkspace.id}` : 'lumora-api-session',
      }),
    });
    removeTypingIndicator();
    if (!res.ok) {
      const detail = await res.text().catch(() => res.statusText);
      throw new Error(`${res.status}: ${detail}`);
    }
    const data = await res.json();
    let reply = data.response ?? '(empty response)';
    if (data.partial || data.status === 'timed_out') {
      reply += '\n\n_Partial result (time budget). Send a follow-up to continue._';
    }
    appendMessage('ai', reply);
    if (data.activity) renderActivity(data.activity);
    // Refresh project files after agent work
    try { if (currentWorkspace) loadFileTree(); } catch (_) {}
    if (data.task_id) {
      const titleEl = document.getElementById('activityTaskTitle');
      if (titleEl) titleEl.textContent = 'Task: ' + (text || '').substring(0, 60);
    }
    // Async project generation: drive bounded ticks (no single long HTTP call)
    if (data.job_id && (data.status === 'queued' || data.partial)) {
      if (data.workspace_id && !currentWorkspace) {
        persistWorkspace({ id: data.workspace_id, name: data.workspace_id });
      }
      try { localStorage.setItem('lumora_active_job', data.job_id); } catch (_) {}
      await driveJobTicks(data.job_id);
    }
  } catch (err) {
    removeTypingIndicator();
    console.error('[Lumora Dev API]', err);
    showToast('Could not reach the Lumora Dev API — is the backend running?');
    appendMessage('ai', `\u26a0\ufe0f Failed to get a response from the agent.\n\n${err.message}\n\nMake sure the API is reachable at the same origin as this page (Vercel / local server).`);
  }
  isTyping = false;
  sendBtn.disabled = messageInput.value.trim() === '';
  messageInput.focus();
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Toast notification ─────────────────────────────────────────────────
let _toastEl = null;
function showToast(msg) {
  if (_toastEl) _toastEl.remove();
  _toastEl = document.createElement('div');
  _toastEl.className = 'toast';
  _toastEl.textContent = msg;
  _toastEl.setAttribute('role', 'status');
  _toastEl.setAttribute('aria-live', 'polite');
  document.body.appendChild(_toastEl);
  setTimeout(() => { if (_toastEl) { _toastEl.remove(); _toastEl = null; } }, 3000);
}

// ═══════════════════════════════════════════════════════════════════════
//  FILE EXPLORER v2
// ═══════════════════════════════════════════════════════════════════════

const fileTreeEl      = document.getElementById('fileTree');
const codeViewer      = document.getElementById('codeViewer');
const editorTabBar    = document.getElementById('editorTabBar');
const editorTextarea  = document.getElementById('editorTextarea');
const editorGutter    = document.getElementById('editorGutter');
const editorStatusbar = document.getElementById('editorStatusbar');
const editorStatusLang  = document.getElementById('editorStatusLang');
const editorStatusLines = document.getElementById('editorStatusLines');
const editorStatusSave  = document.getElementById('editorStatusSave');
const editorFind      = document.getElementById('editorFind');
const editorFindInput = document.getElementById('editorFindInput');
const editorFindCount = document.getElementById('editorFindCount');

// ── Tab switching ───────────────────────────────────────────────────────
document.querySelectorAll('.sidebar-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    document.getElementById(`${tab.dataset.tab}Tab`).classList.remove('hidden');
    if (tab.dataset.tab === 'files' && fileTreeEl.querySelector('.ft-loading')) {
      loadFileTree();
    }
  });
});

// ── Language detection ──────────────────────────────────────────────────
const LANG_MAP = {
  py:'python', js:'javascript', ts:'typescript', jsx:'javascript', tsx:'typescript',
  html:'html', css:'css', json:'json', md:'markdown', sh:'shell', bash:'shell',
  yaml:'yaml', yml:'yaml', toml:'toml', txt:'text', env:'shell',
  gitignore:'text', prettierrc:'json', eslintrc:'json', sql:'sql', xml:'html',
  svg:'html', ini:'text', cfg:'text', makefile:'text', dockerfile:'text',
};

function detectLang(filename) {
  const ext = filename.includes('.') ? filename.split('.').pop().toLowerCase() : '';
  return LANG_MAP[ext] ?? 'text';
}

// ── File-type icons ─────────────────────────────────────────────────────
function fileIconSVG(name, isFolder) {
  if (isFolder) return folderIconSVG(false);
  const ext = name.split('.').pop()?.toLowerCase();
  const colors = { py:'#C084FC', js:'#FDE68A', ts:'#60A5FA', jsx:'#FDE68A', tsx:'#60A5FA', html:'#FB923C', css:'#22D3EE', json:'#A3E635', md:'#94A3B8', sh:'#86EFAC', bash:'#86EFAC', sql:'#38BDF8', xml:'#FB923C', svg:'#FB923C', dockerfile:'#38BDF8' };
  const c = colors[ext] ?? '#71717A';
  return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
}

function folderIconSVG(isOpen) {
  if (isOpen) {
    return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#A78BFA" stroke-width="2" stroke-linecap="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><path d="M22 10H2"/></svg>`;
  }
  return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8B5CF6" stroke-width="2" stroke-linecap="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`;
}

// ── Render tree HTML ────────────────────────────────────────────────────
function renderTree(nodes, depth = 0) {
  if (!nodes.length) return '';
  const indent = depth * 14;
  return `<ul class="ft-list">${nodes.map(n => {
    if (n.type === 'folder') {
      return `<li class="ft-item">
        <div class="ft-row ft-folder" data-path="${escapeHTML(n.path)}" style="padding-left:${indent + 6}px">
          <span class="ft-chevron"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg></span>
          <span class="ft-icon">${folderIconSVG(false)}</span>
          <span class="ft-name">${escapeHTML(n.name)}</span>
        </div>
        <div class="ft-children collapsed">${renderTree(n.children ?? [], depth + 1)}</div>
      </li>`;
    }
    return `<li class="ft-item">
      <div class="ft-row ft-file" data-path="${escapeHTML(n.path)}" style="padding-left:${indent + 24}px">
        <span class="ft-icon">${fileIconSVG(n.name, false)}</span>
        <span class="ft-name">${escapeHTML(n.name)}</span>
      </div>
    </li>`;
  }).join('')}</ul>`;
}

// ── Fetch + render the tree ─────────────────────────────────────────────
async function loadFileTree() {
  fileTreeEl.innerHTML = `<div class="ft-loading"><svg class="ft-spinner" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>Loading\u2026</div>`;
  try {
    const res = await fetch(`${API_BASE}/files`, { headers: apiHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const files = data.files || [];
    if (!currentWorkspace) {
      fileTreeEl.innerHTML = `<div class="ft-empty ft-empty-project">
        <strong>No project selected</strong>
        <p>Create or open a project to see its files. Lumora Dev source files are not shown here.</p>
        <button type="button" class="pv-btn primary" id="ftOpenProjects">Open Projects</button>
      </div>`;
      document.getElementById('ftOpenProjects')?.addEventListener('click', () => {
        document.querySelector('.sidebar-tab[data-tab="chat"]')?.click();
        showCreateProject?.();
      });
      return;
    }
    if (!files.length) {
      fileTreeEl.innerHTML = `<div class="ft-empty">Project is empty. Ask Lumora in Chat to generate files, or create a file.</div>`;
      return;
    }
    fileTreeEl.innerHTML = renderTree(files);
    attachTreeListeners();
    setupFileActionBar();
  } catch (err) {
    fileTreeEl.innerHTML = `<div class="ft-error">Could not load files<br><small>${escapeHTML(err.message)}</small></div>`;
  }
}

// ── Wire folder toggle + file click + context menu ──────────────────────
function attachTreeListeners() {
  fileTreeEl.querySelectorAll('.ft-folder').forEach(row => {
    row.addEventListener('click', toggleFolder);
    row.addEventListener('contextmenu', onContextMenu);
  });
  fileTreeEl.querySelectorAll('.ft-file').forEach(row => {
    row.addEventListener('click', e => openFile(row.dataset.path));
    row.addEventListener('contextmenu', onContextMenu);
  });
}

function toggleFolder(e) {
  const row = e.currentTarget;
  const kids    = row.nextElementSibling;
  const chevron = row.querySelector('.ft-chevron');
  const icon    = row.querySelector('.ft-icon');
  const wasCollapsed = kids.classList.contains('collapsed');
  kids.classList.toggle('collapsed');
  chevron.classList.toggle('open');
  if (icon) icon.innerHTML = folderIconSVG(!wasCollapsed);
}

// ── Action bar (search + refresh + new file/folder buttons) ─────────────
function setupFileActionBar() {
  const tab = document.getElementById('filesTab');
  if (tab.querySelector('.fe-action-bar')) return;

  const bar = document.createElement('div');
  bar.className = 'fe-action-bar';
  bar.innerHTML = `
    <div class="fe-search-wrap">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" class="fe-search-input" placeholder="Filter files\u2026" />
    </div>
    <div class="fe-actions">
      <button class="fe-btn" id="feRefresh" title="Refresh">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
      </button>
      <button class="fe-btn" id="feNewFile" title="New File">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
      </button>
      <button class="fe-btn" id="feNewFolder" title="New Folder">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/></svg>
      </button>
    </div>
  `;
  tab.insertBefore(bar, tab.firstChild);

  bar.querySelector('#feRefresh').addEventListener('click', loadFileTree);
  bar.querySelector('#feNewFile').addEventListener('click', () => showCreateDialog('file'));
  bar.querySelector('#feNewFolder').addEventListener('click', () => showCreateDialog('folder'));
  bar.querySelector('.fe-search-input').addEventListener('input', e => filterTree(e.target.value));
}

// ── Search / filter ─────────────────────────────────────────────────────
function filterTree(query) {
  const term = query.toLowerCase().trim();
  fileTreeEl.querySelectorAll('.ft-item').forEach(item => {
    const nameEl = item.querySelector('.ft-name');
    if (!nameEl) return;
    const name = nameEl.textContent.toLowerCase();
    item.style.display = (!term || name.includes(term)) ? '' : 'none';
  });
  if (term) {
    fileTreeEl.querySelectorAll('.ft-children.collapsed').forEach(ch => {
      if (ch.textContent.toLowerCase().includes(term)) {
        ch.classList.remove('collapsed');
        const parent = ch.previousElementSibling;
        if (parent) {
          parent.querySelector('.ft-chevron')?.classList.add('open');
          const icon = parent.querySelector('.ft-icon');
          if (icon) icon.innerHTML = folderIconSVG(true);
        }
      }
    });
  }
}

// ── Context menu ────────────────────────────────────────────────────────
let _ctxTargetPath = null;
let _ctxTargetType = null;

function onContextMenu(e) {
  e.preventDefault();
  e.stopPropagation();
  const row = e.currentTarget;
  _ctxTargetPath = row.dataset.path;
  _ctxTargetType = row.classList.contains('ft-folder') ? 'folder' : 'file';
  removeContextMenu();

  const menu = document.createElement('div');
  menu.className = 'fe-context-menu';
  menu.id = 'feContextMenu';
  menu.style.left = e.clientX + 'px';
  menu.style.top  = Math.min(e.clientY, window.innerHeight - 220) + 'px';
  menu.innerHTML = `
    <div class="fe-cm-item" data-action="new-file">\uD83D\uDCC4 New File</div>
    <div class="fe-cm-item" data-action="new-folder">\uD83D\uDCC1 New Folder</div>
    <div class="fe-cm-sep"></div>
    <div class="fe-cm-item" data-action="rename">\u270F\uFE0F Rename</div>
    <div class="fe-cm-item fe-cm-danger" data-action="delete">\uD83D\uDDD1 Delete</div>
  `;
  document.body.appendChild(menu);

  menu.querySelectorAll('.fe-cm-item').forEach(item => {
    item.addEventListener('click', () => {
      const action = item.dataset.action;
      removeContextMenu();
      const parentPath = _ctxTargetType === 'folder' ? _ctxTargetPath : getParentPath(_ctxTargetPath);
      if (action === 'new-file') showCreateDialog('file', parentPath);
      else if (action === 'new-folder') showCreateDialog('folder', parentPath);
      else if (action === 'rename') startRename(_ctxTargetPath, _ctxTargetType);
      else if (action === 'delete') confirmDelete(_ctxTargetPath, _ctxTargetType);
    });
  });

  setTimeout(() => document.addEventListener('click', removeContextMenu, { once: true }), 0);
}

function removeContextMenu() {
  const m = document.getElementById('feContextMenu');
  if (m) m.remove();
}

function getParentPath(filePath) {
  const parts = filePath.split('/');
  parts.pop();
  return parts.join('/') || '.';
}

// ── Create dialog ───────────────────────────────────────────────────────
function showCreateDialog(type, parentPath) {
  const name = prompt(`${type === 'folder' ? 'Folder' : 'File'} name:`);
  if (!name || !name.trim()) return;
  const cleanName = name.trim().replace(/[<>:"|?*\\]/g, '');
  if (!cleanName) { showToast('Invalid name'); return; }
  const targetParent = parentPath && parentPath !== '.' ? parentPath : '';
  const fullPath = targetParent ? `${targetParent}/${cleanName}` : cleanName;
  doCreateItem(fullPath, type);
}

async function doCreateItem(fullPath, type) {
  try {
    const res = await fetch(`${API_BASE}/files/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: fullPath, type, content: '' }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? res.statusText);
    }
    showToast(`${type === 'folder' ? '\uD83D\uDCC1' : '\uD83D\uDCC4'} Created "${fullPath}"`);
    await loadFileTree();
  } catch (err) {
    showToast(`Failed to create: ${err.message}`);
  }
}

// ── Rename ──────────────────────────────────────────────────────────────
function startRename(oldPath, type) {
  const row = fileTreeEl.querySelector(`.ft-row[data-path="${CSS.escape(oldPath)}"]`);
  if (!row) return;
  const nameEl = row.querySelector('.ft-name');
  if (!nameEl) return;
  const oldName = nameEl.textContent;

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'fe-rename-input';
  input.value = oldName;
  nameEl.replaceWith(input);
  input.focus();
  input.select();

  async function finishRename() {
    const newName = input.value.trim().replace(/[<>:"|?*\\]/g, '');
    if (!newName || newName === oldName) { cancelRename(); return; }
    const parent = getParentPath(oldPath);
    const newPath = parent && parent !== '.' ? `${parent}/${newName}` : newName;
    cancelRename(); // restore span before async
    await doRename(oldPath, newPath, type);
  }

  function cancelRename() {
    const s = document.createElement('span');
    s.className = 'ft-name';
    s.textContent = oldName;
    if (input.parentNode) input.replaceWith(s);
  }

  input.addEventListener('blur', finishRename);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
    if (e.key === 'Escape') { cancelRename(); }
  });
}

async function doRename(oldPath, newPath, type) {
  try {
    const res = await fetch(`${API_BASE}/file`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_path: oldPath, new_path: newPath }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? res.statusText);
    }
    showToast(`Renamed to "${newPath}"`);
    await loadFileTree();
  } catch (err) {
    showToast(`Rename failed: ${err.message}`);
  }
}

// ── Delete ──────────────────────────────────────────────────────────────
function confirmDelete(filePath, type) {
  if (!confirm(`Delete ${type} "${filePath}"?\n\nThis cannot be undone.`)) return;
  doDelete(filePath);
}

async function doDelete(filePath) {
  try {
    const res = await fetch(`${API_BASE}/file`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: filePath }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? res.statusText);
    }
    showToast(`Deleted "${filePath}"`);
    if (codeViewerFname.textContent === filePath.split('/').pop()) {
      codeViewer.classList.remove('open');
    }
    await loadFileTree();
  } catch (err) {
    showToast(`Delete failed: ${err.message}`);
  }
}

// ═══════════════════════════════════════════════════════════════════════
//  EDITOR ENGINE
// ═══════════════════════════════════════════════════════════════════════

// ── Editor State ──────────────────────────────────────────────────────
const editorTabs = [];       // { path, name, lang, content, savedContent, cursorLine, cursorCol, scrollTop, dirty }
let editorActiveIndex = -1;
let editorSuppressUpdate = false;

// ── Open a file in the editor ─────────────────────────────────────────
async function openFile(path) {
  // Highlight in file tree
  fileTreeEl.querySelectorAll('.ft-file').forEach(r => r.classList.remove('active'));
  fileTreeEl.querySelector(`.ft-file[data-path="${CSS.escape(path)}"]`)?.classList.add('active');

  // Check if already open — switch to it
  const existingIdx = editorTabs.findIndex(t => t.path === path);
  if (existingIdx >= 0) {
    switchTab(existingIdx);
    return;
  }

  // Add new tab
  const name = path.split('/').pop();
  const lang = detectLang(name);
  const tab  = { path, name, lang, content: '', savedContent: '', cursorLine: 1, cursorCol: 1, scrollTop: 0, dirty: false };
  editorTabs.push(tab);

  renderTabs();
  switchTab(editorTabs.length - 1);
  codeViewer.classList.add('open');
  if (window.DarkVeil) window.DarkVeil.setMode('coding');

  // Load content
  try {
    const res = await fetch(`${API_BASE}/file?path=${encodeURIComponent(path)}`, { headers: apiHeaders() });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(detail.detail ?? res.statusText);
    }
    const { content } = await res.json();
    tab.content = content;
    tab.savedContent = content;
    setEditorContent(content, true);
    updateStatusBar();
  } catch (err) {
    tab.content = `// Error loading ${name}: ${err.message}`;
    tab.savedContent = tab.content;
    setEditorContent(tab.content, true);
    showToast(`Could not open ${name}`);
  }
}

// ── Tabs ──────────────────────────────────────────────────────────────
function renderTabs() {
  editorTabBar.innerHTML = editorTabs.map((t, i) =>
    `<div class="editor-tab${i === editorActiveIndex ? ' active' : ''}" data-idx="${i}" title="${escapeHTML(t.path)}">
      <span class="editor-tab-name">${escapeHTML(t.name)}</span>
      ${t.dirty ? '<span class="editor-tab-dirty">●</span>' : ''}
      <button class="editor-tab-close" data-close="${i}">&times;</button>
    </div>`
  ).join('');

  // Click handlers
  editorTabBar.querySelectorAll('.editor-tab').forEach(el => {
    el.addEventListener('click', e => {
      if (e.target.closest('.editor-tab-close')) return;
      switchTab(parseInt(el.dataset.idx));
    });
    el.addEventListener('mousedown', e => {
      if (e.button === 1) { e.preventDefault(); closeTab(parseInt(el.dataset.idx)); }
    });
  });
  editorTabBar.querySelectorAll('.editor-tab-close').forEach(btn => {
    btn.addEventListener('click', e => { e.stopPropagation(); closeTab(parseInt(btn.dataset.close)); });
  });
}

function switchTab(idx) {
  if (idx < 0 || idx >= editorTabs.length) return;
  // Save current tab state before switching
  saveCurrentTabState();
  editorActiveIndex = idx;
  const tab = editorTabs[idx];
  setEditorContent(tab.content, true);
  editorTextarea.scrollTop = tab.scrollTop || 0;
  // Restore cursor
  const pos = (tab.cursorLine || 1) > 1
    ? editorTextarea.value.split('\n').slice(0, tab.cursorLine - 1).join('\n').length + (tab.cursorCol || 1)
    : (tab.cursorCol || 1) - 1;
  setTimeout(() => { editorTextarea.setSelectionRange(pos, pos); editorTextarea.focus(); }, 10);
  renderTabs();
  updateStatusBar();
  codeViewer.classList.add('open');
}

async function closeTab(idx) {
  if (idx < 0 || idx >= editorTabs.length) return;
  const tab = editorTabs[idx];
  if (tab.dirty) {
    if (!confirm(`"${tab.name}" has unsaved changes. Close anyway?`)) return;
  }
  editorTabs.splice(idx, 1);
  if (editorTabs.length === 0) {
    editorActiveIndex = -1;
    setEditorContent('', true);
    renderTabs();
    codeViewer.classList.remove('open');
    fileTreeEl.querySelectorAll('.ft-file').forEach(r => r.classList.remove('active'));
    if (window.DarkVeil) window.DarkVeil.setMode('chat');
    updateStatusBar();
    return;
  }
  const newIdx = Math.min(idx, editorTabs.length - 1);
  renderTabs();
  switchTab(newIdx);
}

// ── Editor content ───────────────────────────────────────────────────
function setEditorContent(text, suppressGutter) {
  editorSuppressUpdate = suppressGutter;
  editorTextarea.value = text;
  updateGutter();
  editorSuppressUpdate = false;
}

function saveCurrentTabState() {
  if (editorActiveIndex < 0) return;
  const tab = editorTabs[editorActiveIndex];
  tab.content = editorTextarea.value;
  tab.scrollTop = editorTextarea.scrollTop;
  const before = editorTextarea.value.substring(0, editorTextarea.selectionStart);
  tab.cursorLine = (before.match(/\n/g) || []).length + 1;
  const lastNewline = before.lastIndexOf('\n');
  tab.cursorCol = lastNewline >= 0 ? before.length - lastNewline : before.length + 1;
}

function markDirty() {
  if (editorActiveIndex < 0) return;
  const tab = editorTabs[editorActiveIndex];
  const wasDirty = tab.dirty;
  tab.dirty = (editorTextarea.value !== tab.savedContent);
  if (wasDirty !== tab.dirty) renderTabs();
  updateStatusBar();
}

// ── Save ──────────────────────────────────────────────────────────────
async function saveCurrentFile() {
  if (editorActiveIndex < 0) return;
  const tab = editorTabs[editorActiveIndex];
  const content = editorTextarea.value;
  if (content === tab.savedContent) return;

  editorStatusSave.textContent = 'Saving…';
  try {
    const res = await fetch(`${API_BASE}/file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: tab.path, content }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? res.statusText);
    }
    tab.savedContent = content;
    tab.dirty = false;
    tab.content = content;
    renderTabs();
    showToast(`Saved ${tab.name}`);
  } catch (err) {
    showToast(`Save failed: ${err.message}`);
  }
  updateStatusBar();
}

// ── Gutter ────────────────────────────────────────────────────────────
function updateGutter() {
  const lines = editorTextarea.value.split('\n');
  const count = lines.length;
  // Only update gutter if number of lines changed
  const currentLines = editorGutter.childElementCount;
  if (currentLines === count && !editorSuppressUpdate) return;
  let html = '';
  for (let i = 1; i <= count; i++) html += `<span class="editor-gutter-line">${i}</span>`;
  editorGutter.innerHTML = html;
  editorGutter.scrollTop = editorTextarea.scrollTop;
}

function updateStatusBar() {
  if (editorActiveIndex >= 0) {
    const tab = editorTabs[editorActiveIndex];
    editorStatusLang.textContent = tab.lang;
    const lines = (editorTextarea.value.match(/\n/g) || []).length + 1;
    editorStatusLines.textContent = `Ln 1, Col 1 · ${lines} line${lines !== 1 ? 's' : ''}`;
    editorStatusSave.textContent = tab.dirty ? '● Unsaved' : 'Saved';
    editorStatusSave.style.color = tab.dirty ? '#A78BFA' : '';
    if (editorStatusbar) editorStatusbar.style.display = '';
  } else {
    if (editorStatusbar) editorStatusbar.style.display = 'none';
  }
}

// ── Find ──────────────────────────────────────────────────────────────
function showFind() {
  editorFind.style.display = 'flex';
  editorFindInput.focus();
  editorFindInput.select();
}

function hideFind() {
  editorFind.style.display = 'none';
}

function doFind(dir) {
  const query = editorFindInput.value;
  if (!query) { editorFindCount.textContent = ''; return; }
  const text = editorTextarea.value;
  const pos  = editorTextarea.selectionStart;
  let idx;
  if (dir === 'next') {
    idx = text.indexOf(query, pos);
    if (idx < 0 && pos > 0) idx = text.indexOf(query, 0);
  } else {
    const searchEnd = pos > 0 ? pos - 1 : text.length;
    idx = text.lastIndexOf(query, searchEnd);
    if (idx < 0) idx = text.lastIndexOf(query, text.length);
  }
  if (idx >= 0) {
    editorTextarea.setSelectionRange(idx, idx + query.length);
    editorTextarea.focus();
    // Count total matches
    const total = (text.match(new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
    editorFindCount.textContent = total > 0 ? `1/${total}` : '';
  } else {
    editorFindCount.textContent = '0';
  }
}

// ── Editor events ────────────────────────────────────────────────────
editorTextarea.addEventListener('input', () => {
  updateGutter();
  markDirty();
  updateStatusBar();
});

editorTextarea.addEventListener('scroll', () => {
  editorGutter.scrollTop = editorTextarea.scrollTop;
  if (editorActiveIndex >= 0) editorTabs[editorActiveIndex].scrollTop = editorTextarea.scrollTop;
});

editorTextarea.addEventListener('keydown', e => {
  // Tab → 2 spaces
  if (e.key === 'Tab' && !e.shiftKey) {
    e.preventDefault();
    const s = editorTextarea.selectionStart;
    const val = editorTextarea.value;
    editorTextarea.value = val.substring(0, s) + '  ' + val.substring(editorTextarea.selectionEnd);
    editorTextarea.setSelectionRange(s + 2, s + 2);
    updateGutter();
    markDirty();
    return;
  }
  // Shift+Tab → outdent 2 spaces
  if (e.key === 'Tab' && e.shiftKey) {
    e.preventDefault();
    const s = editorTextarea.selectionStart;
    const val = editorTextarea.value;
    if (val.substring(s - 2, s) === '  ') {
      editorTextarea.value = val.substring(0, s - 2) + val.substring(s);
      editorTextarea.setSelectionRange(s - 2, s - 2);
      updateGutter();
      markDirty();
    }
    return;
  }
  // Enter → auto-indent
  if (e.key === 'Enter') {
    e.preventDefault();
    const s = editorTextarea.selectionStart;
    const val = editorTextarea.value;
    const lineStart = val.lastIndexOf('\n', s - 1) + 1;
    const currentLine = val.substring(lineStart, s);
    const indent = (currentLine.match(/^(\s*)/) || [''])[0];
    // If current line ends with {, [ or (, add extra indent
    const trimmed = currentLine.trimEnd();
    const extra = (trimmed.endsWith('{') || trimmed.endsWith('[') || trimmed.endsWith('(') ||
                   trimmed.endsWith(':') && val.substring(lineStart, lineStart + 4) !== '    ') ? '  ' : '';
    editorTextarea.value = val.substring(0, s) + '\n' + indent + extra + val.substring(editorTextarea.selectionEnd);
    const newPos = s + 1 + indent.length + extra.length;
    editorTextarea.setSelectionRange(newPos, newPos);
    updateGutter();
    markDirty();
    return;
  }
  // Bracket matching — highlight matching pair
  if (e.key === '(' || e.key === ')' || e.key === '{' || e.key === '}' || e.key === '[' || e.key === ']') {
    // Skip: handled by native caret
  }

  updateStatusBar();
});

editorTextarea.addEventListener('click', updateStatusBar);
editorTextarea.addEventListener('keyup', updateStatusBar);

// ── Find bar events ──────────────────────────────────────────────────
editorFindInput.addEventListener('input', () => doFind('next'));
editorFindInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); doFind(e.shiftKey ? 'prev' : 'next'); }
  if (e.key === 'Escape') { hideFind(); editorTextarea.focus(); }
});

document.getElementById('editorFindPrev').addEventListener('click', () => doFind('prev'));
document.getElementById('editorFindNext').addEventListener('click', () => doFind('next'));
document.getElementById('editorFindClose').addEventListener('click', hideFind);

// ── Status bar cursor tracking ───────────────────────────────────────
editorTextarea.addEventListener('selectionchange', () => {
  const val = editorTextarea.value;
  const s = editorTextarea.selectionStart;
  const before = val.substring(0, s);
  const line = (before.match(/\n/g) || []).length + 1;
  const lastNl = before.lastIndexOf('\n');
  const col = lastNl >= 0 ? before.length - lastNl : before.length + 1;
  if (editorActiveIndex >= 0) {
    const tab = editorTabs[editorActiveIndex];
    tab.cursorLine = line;
    tab.cursorCol = col;
    editorStatusLines.textContent = `Ln ${line}, Col ${col} · ${(val.match(/\n/g) || []).length + 1} line${((val.match(/\n/g) || []).length + 1) !== 1 ? 's' : ''}`;
  }
});

// ── Keyboard shortcuts ─────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  const mod = e.metaKey || e.ctrlKey;

  // Global
  if (e.key === 'Escape') {
    closeSettings();
    closeSidebar();
    removeContextMenu();
    hideFind();
  }
  if (mod && e.key === 'k') {
    e.preventDefault();
    messageInput.focus();
  }

  // Editor shortcuts (only when editor is open and focused)
  if (codeViewer.classList.contains('open') && !isTyping) {
    if (mod && e.key === 's') { e.preventDefault(); saveCurrentFile(); return; }
    if (mod && e.key === 'w') { e.preventDefault(); closeTab(editorActiveIndex); return; }
    if (mod && !e.shiftKey && e.key === 'Tab') { e.preventDefault(); switchTab((editorActiveIndex + 1) % editorTabs.length); return; }
    if (mod && e.shiftKey && e.key === 'Tab') { e.preventDefault(); switchTab((editorActiveIndex - 1 + editorTabs.length) % editorTabs.length); return; }
    if (mod && e.key === 'f') { e.preventDefault(); showFind(); return; }
  }
});

// ── Close all tabs when viewer closes via X button in tab ────────────
// (handled by closeTab above; no separate close button needed)

// ═══════════════════════════════════════════════════════════════════════
//  LIVE PREVIEW ENGINE
// ═══════════════════════════════════════════════════════════════════════

const previewPanel   = document.getElementById('previewPanel');
const previewIframe  = document.getElementById('previewIframe');
const previewError    = document.getElementById('previewError');
const previewErrorTtl = document.getElementById('previewErrorTitle');
const previewErrorMsg = document.getElementById('previewErrorMsg');
const pvZoomLabel     = document.getElementById('pvZoomLabel');
let   previewAutoReload = true;
let   previewDevice     = 'desktop';
let   previewZoom       = 100;
let   previewCurrentPath = null;
let   previewReloadDebounce = null;
let   previewBlobUrl     = null;

// ── Tab switching: open preview ──────────────────────────────────────
const previewTab = document.querySelector('.sidebar-tab[data-tab="preview"]');
if (previewTab) {
  const origHandler = previewTab.onclick;
  previewTab.addEventListener('click', () => {
    openPreview();
  });
}

// ── Toolbar buttons ────────────────────────────────────────────────────
document.getElementById('pvReload').addEventListener('click', reloadPreview);
document.getElementById('pvAutoReload').addEventListener('click', toggleAutoReload);
document.getElementById('pvZoomOut').addEventListener('click', () => changeZoom(previewZoom > 50 ? previewZoom - 25 : previewZoom));
document.getElementById('pvZoomIn').addEventListener('click', () => changeZoom(previewZoom < 150 ? previewZoom + 25 : previewZoom));
document.getElementById('pvDesktop').addEventListener('click', () => setDevice('desktop'));
document.getElementById('pvTablet').addEventListener('click', () => setDevice('tablet'));
document.getElementById('pvMobile').addEventListener('click', () => setDevice('mobile'));
document.getElementById('pvExternal').addEventListener('click', openPreviewExternal);
document.getElementById('pvClose').addEventListener('click', closePreview);

// ── Open preview ───────────────────────────────────────────────────────
function openPreview(filePath) {
  const path = filePath || previewCurrentPath;
  if (path) {
    previewPanel.classList.add('open');
    loadPreview(path);
  } else {
    // If no path, try to find the currently active HTML file
    if (editorActiveIndex >= 0) {
      const tab = editorTabs[editorActiveIndex];
      if (isPreviewableFile(tab.path)) {
        loadPreview(tab.path);
        previewPanel.classList.add('open');
        return;
      }
    }
    // Show just the panel with an error message
    previewPanel.classList.add('open');
    showPreviewError('No file selected', 'Open an HTML, CSS or JS file to preview it, or select a file from the explorer.');
  }
}

function closePreview() {
  previewPanel.classList.remove('open');
  // Clean up blob
  if (previewBlobUrl) { URL.revokeObjectURL(previewBlobUrl); previewBlobUrl = null; }
}

function isPreviewableFile(path) {
  const ext = path.split('.').pop()?.toLowerCase();
  return ['html','htm','css','js','json','xml','svg'].includes(ext);
}

function isHTMLFile(path) {
  const ext = path.split('.').pop()?.toLowerCase();
  return ext === 'html' || ext === 'htm';
}

// ── Load preview ───────────────────────────────────────────────────────
async function loadPreview(path) {
  if (!path) return;
  previewCurrentPath = path;
  hidePreviewError();

  try {
    const res = await fetch(`${API_BASE}/file?path=${encodeURIComponent(path)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const { content } = await res.json();

    if (isHTMLFile(path)) {
      // Serve HTML as a full page
      previewIframe.style.display = '';
      loadPreviewHTML(content, path);
    } else if (path.endsWith('.css')) {
      // Inject CSS into current preview
      previewIframe.style.display = '';
      if (previewCurrentPath && isHTMLFile(previewCurrentPath)) {
        // Reload the HTML to apply CSS changes
        const htmlRes = await fetch(`${API_BASE}/file?path=${encodeURIComponent(previewCurrentPath)}`);
        if (htmlRes.ok) {
          const { content: htmlContent } = await htmlRes.json();
          loadPreviewHTML(htmlContent, previewCurrentPath);
        }
      } else {
        showPreviewError('Cannot preview CSS alone', 'Open an HTML file first, then open the CSS file.');
      }
    } else if (path.endsWith('.js')) {
      previewIframe.style.display = '';
      if (previewCurrentPath && isHTMLFile(previewCurrentPath)) {
        const htmlRes = await fetch(`${API_BASE}/file?path=${encodeURIComponent(previewCurrentPath)}`);
        if (htmlRes.ok) {
          const { content: htmlContent } = await htmlRes.json();
          loadPreviewHTML(htmlContent, previewCurrentPath);
        }
      } else {
        showPreviewError('Cannot preview JS alone', 'Open an HTML file first, then open the JS file.');
      }
    } else {
      // Other files — show raw content
      showPreviewError('Not previewable', `${path.split('.').pop()?.toUpperCase()} files cannot be live-previewed. Open an HTML file instead.`);
      previewIframe.style.display = 'none';
    }
  } catch (err) {
    showPreviewError('Failed to load', err.message);
    previewIframe.style.display = 'none';
  }
}

function loadPreviewHTML(htmlContent, basePath) {
  // Strip file tools / non-browser code from the HTML
  let cleaned = htmlContent;

  // Build a blob with the content
  const blob = new Blob([cleaned], { type: 'text/html' });
  if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl);
  previewBlobUrl = URL.createObjectURL(blob);
  previewIframe.src = previewBlobUrl;
}

function reloadPreview() {
  if (!previewCurrentPath) { openPreview(); return; }
  loadPreview(previewCurrentPath);
}

// ── Auto-reload on save ────────────────────────────────────────────────
function notifyPreviewSaved(path) {
  if (!previewAutoReload) return;
  if (!previewPanel.classList.contains('open')) return;
  if (!isPreviewableFile(path)) return;

  // Debounce: wait 500ms after last save before reloading
  if (previewReloadDebounce) clearTimeout(previewReloadDebounce);
  previewReloadDebounce = setTimeout(() => {
    if (isHTMLFile(path)) {
      // HTML file saved — full reload
      loadPreview(path);
    } else if (previewCurrentPath && isHTMLFile(previewCurrentPath)) {
      // CSS/JS file saved — reload the HTML to pick up changes
      const htmlRes = fetch(`${API_BASE}/file?path=${encodeURIComponent(previewCurrentPath)}`)
        .then(res => res.json())
        .then(data => loadPreviewHTML(data.content, previewCurrentPath))
        .catch(() => {});
    }
  }, 500);
}

// Hook into saveCurrentFile to trigger preview reload
const _origSaveCurrentFile = saveCurrentFile;
saveCurrentFile = async function() {
  if (editorActiveIndex >= 0) {
    const path = editorTabs[editorActiveIndex].path;
    await _origSaveCurrentFile();
    notifyPreviewSaved(path);
  } else {
    await _origSaveCurrentFile();
  }
};

// ── Auto-reload toggle ──────────────────────────────────────────────────
function toggleAutoReload() {
  previewAutoReload = !previewAutoReload;
  const btn = document.getElementById('pvAutoReload');
  btn.classList.toggle('active', previewAutoReload);
  showToast(previewAutoReload ? 'Auto-reload on' : 'Auto-reload off');
}

// Initial auto-reload state
(function() {
  const btn = document.getElementById('pvAutoReload');
  if (btn && previewAutoReload) btn.classList.add('active');
})();

// ── Device switch ──────────────────────────────────────────────────────
function setDevice(device) {
  previewDevice = device;
  previewPanel.classList.remove('device-desktop', 'device-tablet', 'device-mobile');
  if (device !== 'desktop') previewPanel.classList.add('device-' + device);
  // Highlight active
  document.querySelectorAll('.preview-device-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('pv' + device.charAt(0).toUpperCase() + device.slice(1));
  if (btn) btn.classList.add('active');
}

// Initial device state
(function() {
  const btn = document.getElementById('pvDesktop');
  if (btn) btn.classList.add('active');
})();

// ── Zoom ────────────────────────────────────────────────────────────────
function changeZoom(zoom) {
  previewZoom = Math.max(25, Math.min(200, zoom));
  previewPanel.classList.remove('zoom-50', 'zoom-75', 'zoom-fit');
  if (previewZoom !== 100) {
    const cls = 'zoom-' + (previewZoom === 50 ? '50' : previewZoom === 75 ? '75' : 'fit');
    if (['50','75','fit'].includes(previewZoom.toString()) || previewZoom === 50 || previewZoom === 75) {
      previewPanel.classList.add(cls);
    }
  }
  pvZoomLabel.textContent = zoom + '%';
}

// ── Open in new tab ─────────────────────────────────────────────────────
function openPreviewExternal() {
  if (!previewCurrentPath) { showToast('No preview to open'); return; }
  const url = `${API_BASE}/file?path=${encodeURIComponent(previewCurrentPath)}`;
  window.open(url, '_blank');
}

// ── Error display ───────────────────────────────────────────────────────
function showPreviewError(title, msg) {
  previewError.style.display = '';
  previewErrorTtl.textContent = title;
  previewErrorMsg.textContent = msg;
}

function hidePreviewError() {
  previewError.style.display = 'none';
}

// ═══════════════════════════════════════════════════════════════════════
//  AI PROVIDER SETTINGS
// ═══════════════════════════════════════════════════════════════════════

let _providersData = {};

async function loadProviderSettings() {
  const grid = document.getElementById('providersGrid');
  if (!grid) return;
  grid.innerHTML = '<div class="ft-loading"><svg class="ft-spinner" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>Loading providers…</div>';
  try {
    const res = await fetch(`${API_BASE}/settings`);
    if (!res.ok) throw new Error('Failed to load');
    const data = await res.json();
    _providersData = data;
    renderProviderCards(data);
    updateGeneralPanel(data);
  } catch (err) {
    grid.innerHTML = '<div class="ft-error">Failed to load settings</div>';
  }
}

function updateGeneralPanel(data) {
  const genModel = document.getElementById('genModel');
  const genProvider = document.getElementById('genProvider');
  if (genModel) genModel.textContent = data.default_model || 'qwen/qwen3-coder:free';
  if (genProvider) {
    const prov = data.providers && data.providers[data.default_provider];
    genProvider.textContent = prov ? prov.name : data.default_provider;
  }
}

function renderProviderCards(data) {
  const grid = document.getElementById('providersGrid');
  if (!grid) return;
  const providers = data.providers || {};
  const entries = Object.entries(providers).sort(([, a], [, b]) => (b.connected ? 1 : 0) - (a.connected ? 1 : 0));

  grid.innerHTML = entries.map(([pid, p]) => {
    const models = p.cached_models || p.models_fixed || [];
    const isDefault = data.default_provider === pid;
    const defaultModel = isDefault ? data.default_model : '';

    return `<div class="provider-card${p.connected ? ' connected' : ''}" data-provider="${pid}">
      <div class="provider-card-top">
        <div class="provider-card-info">
          <span class="provider-card-icon">${escapeHTML(p.icon || '')}</span>
          <span class="provider-card-name">${escapeHTML(p.name)}</span>
          <span class="provider-card-status ${p.connected ? 'on' : 'off'}">${p.connected ? 'Connected' : 'Not Connected'}</span>
        </div>
        <div class="provider-card-actions">
          ${models.length > 0 ? `<select class="pv-select model-select-${pid}" onchange="setDefaultModel('${pid}', this.value)">
            ${models.map(m => `<option value="${escapeHTML(m.id)}"${m.id === defaultModel || m.id === (models[0] && models[0].id) ? ' selected' : ''}>${escapeHTML(m.name || m.id)}</option>`).join('')}
          </select>` : ''}
          ${models.length > 0 && !p.supports_model_list ? `<button class="pv-btn" onclick="setDefaultProvider('${pid}')" ${isDefault ? 'disabled' : ''}>${isDefault ? 'Default' : 'Set Default'}</button>` : ''}
        </div>
      </div>
      <div class="provider-card-row">
        <input type="password" class="provider-key-input" id="keyInput${pid}" placeholder="API Key…" />
        <button class="pv-btn primary" onclick="saveProviderKey('${pid}')">Save</button>
        ${p.key_help_url ? `<a class="pv-btn" href="${escapeHTML(p.key_help_url)}" target="_blank" rel="noopener" style="text-decoration:none;font-size:11px">Get Key</a>` : ''}
        <button class="pv-btn" onclick="testProvider('${pid}')">Test</button>
        <button class="pv-btn danger" onclick="removeProviderKey('${pid}')">Remove</button>
      </div>
      ${p.supports_model_list ? `<div class="provider-card-row">
        <button class="pv-btn" onclick="fetchProviderModels('${pid}')">Fetch Models</button>
        ${isDefault && defaultModel ? `<span class="setting-value" style="margin-left:8px">${escapeHTML(defaultModel)}</span>` : ''}
        ${isDefault ? `<button class="pv-btn primary" onclick="setDefaultProvider('${pid}')" disabled style="margin-left:4px">Default</button>` : `<button class="pv-btn" onclick="setDefaultProvider('${pid}')">Set Default</button>`}
      </div>` : ''}
    </div>`;
  }).join('');
}

async function saveProviderKey(pid) {
  const input = document.getElementById('keyInput' + pid);
  if (!input) return;
  const key = input.value.trim();
  if (!key) { showToast('Enter an API key'); return; }
  try {
    const res = await fetch(`${API_BASE}/settings/provider`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider_id: pid, api_key: key }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    input.value = '';
    showToast('API key saved');
    loadProviderSettings();
  } catch (err) {
    showToast('Save failed: ' + err.message);
  }
}

async function removeProviderKey(pid) {
  if (!confirm('Remove API key for this provider?')) return;
  try {
    const res = await fetch(`${API_BASE}/settings/provider`, {
      method: 'DELETE', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider_id: pid }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    showToast('API key removed');
    loadProviderSettings();
  } catch (err) {
    showToast('Remove failed: ' + err.message);
  }
}

async function testProvider(pid) {
  showToast('Testing connection…');
  try {
    const res = await fetch(`${API_BASE}/settings/test`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider_id: pid }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    showToast('Connection successful!');
  } catch (err) {
    showToast('Test failed: ' + err.message);
  }
}

async function fetchProviderModels(pid) {
  showToast('Fetching models…');
  try {
    const res = await fetch(`${API_BASE}/settings/models/${pid}`, { method: 'POST' });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    showToast('Models loaded!');
    loadProviderSettings();
  } catch (err) {
    showToast('Failed to load models: ' + err.message);
  }
}

async function setDefaultProvider(pid) {
  const model = _providersData?.providers?.[pid]?.cached_models?.[0]?.id ||
                _providersData?.providers?.[pid]?.models_fixed?.[0] || 'gpt-3.5-turbo';
  try {
    const res = await fetch(`${API_BASE}/settings/default`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: pid, model }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    showToast(`Default provider set to ${pid}`);
    loadProviderSettings();
  } catch (err) {
    showToast('Failed: ' + err.message);
  }
}

async function setDefaultModel(pid, model) {
  try {
    const res = await fetch(`${API_BASE}/settings/default`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: pid, model }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    showToast(`Model set to ${model}`);
    loadProviderSettings();
  } catch (err) {
    showToast('Failed: ' + err.message);
  }
}

// ═══════════════════════════════════════════════════════════════════════
//  INTEGRATED TERMINAL
// ═══════════════════════════════════════════════════════════════════════

const terminalPanel   = document.getElementById('terminalPanel');
const terminalOutput  = document.getElementById('terminalOutput');
const terminalInput   = document.getElementById('terminalInput');
const terminalPrompt  = document.getElementById('terminalPrompt');
const terminalTabs    = document.getElementById('terminalTabs');
let   terminalActive  = 0;
const termHistory     = [[]];  // array of arrays — one history per terminal
const termCwds        = ['.']; // one cwd per terminal
let   termHistIdx     = -1;
let   termCmdBuf      = '';

// ── Toggle terminal ────────────────────────────────────────────────────
document.getElementById('termToggle').addEventListener('click', () => {
  terminalPanel.classList.toggle('open');
  if (terminalPanel.classList.contains('open')) {
    terminalInput.focus();
  }
});

// ── New / clear / kill ─────────────────────────────────────────────────
document.getElementById('termNew').addEventListener('click', () => {
  termHistory.push([]);
  termCwds.push('.');
  terminalActive = termHistory.length - 1;
  termHistIdx = -1;
  terminalOutput.innerHTML = '';
  renderTerminalTabs();
  updateTermPrompt();
  terminalInput.focus();
});

document.getElementById('termClear').addEventListener('click', () => {
  terminalOutput.innerHTML = '';
});

document.getElementById('termKill').addEventListener('click', () => {
  if (termHistory.length <= 1) return;
  termHistory.splice(terminalActive, 1);
  termCwds.splice(terminalActive, 1);
  terminalActive = Math.min(terminalActive, termHistory.length - 1);
  termHistIdx = -1;
  renderTerminalTabs();
  updateTermPrompt();
  terminalOutput.innerHTML = '';
});

// ── Tab switching ──────────────────────────────────────────────────────
function renderTerminalTabs() {
  terminalTabs.innerHTML = termHistory.map((_, i) =>
    `<div class="term-tab${i === terminalActive ? ' active' : ''}" data-idx="${i}">
      <span>Terminal ${i + 1}</span>
      ${termHistory.length > 1 ? `<button class="term-tab-close" data-close="${i}">&times;</button>` : ''}
    </div>`
  ).join('');
  terminalTabs.querySelectorAll('.term-tab').forEach(el => {
    el.addEventListener('click', e => {
      if (e.target.closest('.term-tab-close')) return;
      switchTerminal(parseInt(el.dataset.idx));
    });
  });
  terminalTabs.querySelectorAll('.term-tab-close').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const idx = parseInt(btn.dataset.close);
      if (termHistory.length <= 1) return;
      termHistory.splice(idx, 1);
      termCwds.splice(idx, 1);
      terminalActive = Math.min(terminalActive, termHistory.length - 1);
      termHistIdx = -1;
      terminalOutput.innerHTML = termHistory[terminalActive].map(e => `<div class="term-cmd-echo">${e}</div>`).join('');
      renderTerminalTabs();
      updateTermPrompt();
    });
  });
}

function switchTerminal(idx) {
  terminalActive = idx;
  termHistIdx = -1;
  terminalOutput.innerHTML = termHistory[idx].map(e => `<div class="term-cmd-echo">${e}</div>`).join('');
  renderTerminalTabs();
  updateTermPrompt();
  terminalInput.focus();
}

// ── Update prompt ──────────────────────────────────────────────────────
function updateTermPrompt() {
  const cwd = termCwds[terminalActive] || '.';
  terminalPrompt.textContent = 'lumora@dev:' + cwd + '$';
}

// ── Execute command ────────────────────────────────────────────────────
async function executeCommand(cmd) {
  if (!cmd.trim()) { updateTermPrompt(); return; }

  const echo = '<span class="term-cmd-prompt">' + escapeHTML(terminalPrompt.textContent + ' ') + '</span>' + escapeHTML(cmd);
  termHistory[terminalActive].push(echo);
  termHistIdx = -1;
  terminalOutput.innerHTML += '<div class="term-cmd-echo">' + echo + '</div>';
  terminalOutput.scrollTop = terminalOutput.scrollHeight;

  try {
    const res = await fetch(`${API_BASE}/terminal/exec`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd, cwd: termCwds[terminalActive] }),
    });
    if (!res.ok) {
      terminalOutput.innerHTML += '<div>Error: ' + res.status + '</div>';
      return;
    }
    const data = await res.json();

    // Update CWD
    if (data.cwd !== undefined) termCwds[terminalActive] = data.cwd;

    // Render output with ANSI support
    if (data.output) {
      const ansiHtml = ansiToHtml(data.output);
      terminalOutput.innerHTML += '<div>' + ansiHtml + '</div>';
    }
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  } catch (err) {
    terminalOutput.innerHTML += '<div style="color:#F87171">Connection error: ' + escapeHTML(err.message) + '</div>';
  }

  updateTermPrompt();
}

// ── ANSI to HTML (basic support) ───────────────────────────────────────
function ansiToHtml(text) {
  let s = escapeHTML(text);
  // Simple ANSI code replacements
  s = s.replace(/\033\[0m/g, '</span>');
  s = s.replace(/\033\[1m/g, '<span style="font-weight:bold">');
  s = s.replace(/\033\[3m/g, '<span style="font-style:italic">');
  s = s.replace(/\033\[4m/g, '<span style="text-decoration:underline">');
  s = s.replace(/\033\[31m/g, '<span style="color:#F87171">');
  s = s.replace(/\033\[32m/g, '<span style="color:#86EFAC">');
  s = s.replace(/\033\[33m/g, '<span style="color:#FDE68A">');
  s = s.replace(/\033\[34m/g, '<span style="color:#93C5FD">');
  s = s.replace(/\033\[35m/g, '<span style="color:#C084FC">');
  s = s.replace(/\033\[36m/g, '<span style="color:#22D3EE">');
  s = s.replace(/\033\[37m/g, '<span style="color:#F4F4F5">');
  s = s.replace(/\033\[90m/g, '<span style="color:#71717A">');
  s = s.replace(/\033\[2J\033\[H/g, ''); // clear screen
  return s;
}

// ── Input handling ─────────────────────────────────────────────────────
terminalInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    e.preventDefault();
    const cmd = terminalInput.value;
    terminalInput.value = '';
    termCmdBuf = '';
    executeCommand(cmd);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    const hist = termHistory[terminalActive];
    if (termHistIdx < hist.length - 1) {
      if (termHistIdx === -1) termCmdBuf = terminalInput.value;
      termHistIdx++;
      const entry = hist[hist.length - 1 - termHistIdx];
      // Extract command from the html line
      const tmp = document.createElement('div');
      tmp.innerHTML = entry;
      const cmdText = (tmp.textContent || '').replace(/^[^$]*\$\s*/, '');
      terminalInput.value = cmdText;
    }
  } else if (e.key === 'ArrowDown') {
    e.preventDefault();
    const hist = termHistory[terminalActive];
    if (termHistIdx >= 0) {
      termHistIdx--;
      if (termHistIdx === -1) {
        terminalInput.value = termCmdBuf;
      } else {
        const entry = hist[hist.length - 1 - termHistIdx];
        const tmp = document.createElement('div');
        tmp.innerHTML = entry;
        const cmdText = (tmp.textContent || '').replace(/^[^$]*\$\s*/, '');
        terminalInput.value = cmdText;
      }
    }
  } else if (e.key === 'l' && e.ctrlKey) {
    e.preventDefault();
    terminalOutput.innerHTML = '';
  } else if (e.key === 'c' && e.ctrlKey) {
    e.preventDefault();
    terminalInput.value = '';
    terminalOutput.innerHTML += '<div class="term-cmd-echo"><span class="term-cmd-prompt">' + escapeHTML(terminalPrompt.textContent + ' ') + '</span>^C</div>';
  }
});

// ── Click output to focus input ────────────────────────────────────────
terminalOutput.addEventListener('click', () => terminalInput.focus());

// ═══════════════════════════════════════════════════════════════════════
//  SOURCE CONTROL (GIT + GITHUB)
// ═══════════════════════════════════════════════════════════════════════

async function loadSCM() {
  const panel = document.getElementById('scmPanel');
  if (!panel) return;
  panel.dataset.loaded = '1';
  await refreshSCM();
  await loadGitHubStatus();
  wireSCMButtons();
}

function wireSCMButtons() {
  const refresh = document.getElementById('scmRefresh');
  const commit = document.getElementById('scmCommitBtn');
  const pull = document.getElementById('scmPull');
  const push = document.getElementById('scmPush');
  const fetchBtn = document.getElementById('scmFetch');
  const branches = document.getElementById('scmBranches');
  if (refresh) refresh.addEventListener('click', refreshSCM);
  if (commit) commit.addEventListener('click', commitSCM);
  if (pull) pull.addEventListener('click', () => gitAction('pull'));
  if (push) push.addEventListener('click', () => gitAction('push'));
  if (fetchBtn) fetchBtn.addEventListener('click', () => gitAction('fetch'));
  if (branches) branches.addEventListener('click', showBranchesDialog);
}

async function refreshSCM() {
  try {
    const res = await fetch(`${API_BASE}/git/status`);
    const data = await res.json();
    renderSCM(data);
  } catch (err) {
    const panel = document.getElementById('scmPanel');
    if (panel) panel.innerHTML = '<div class="scm-no-repo">Could not read Git status.<br><small>' + escapeHTML(err.message) + '</small></div>';
  }
}

function renderSCM(data) {
  if (!data.has_repo) {
    const panel = document.getElementById('scmPanel');
    if (panel) panel.innerHTML = '<div class="scm-no-repo"><p>No Git repository found.</p><button class="pv-btn primary" onclick="gitInit()" style="margin-top:8px">Initialize Repository</button></div>';
    return;
  }
  const bEl = document.getElementById('scmBranch');
  if (bEl) bEl.textContent = data.branch || 'main';
  renderFileGroup('scmStagedList', 'scmStagedCount', data.staged || [], 'A', 'unstageFile', false, '');
  renderFileGroup('scmChangesList', 'scmChangesCount', data.unstaged || [], 'M', 'stageFile', true, '');
  renderFileGroup('scmUntrackedList', 'scmUntrackedCount', data.untracked || [], 'U', 'stageFile', true, '#22D3EE');
}

function renderFileGroup(listId, countId, files, indicator, actionFn, clickable, color) {
  const list = document.getElementById(listId);
  if (!list) return;
  if (!files.length) {
    list.innerHTML = '<div style="font-size:11px;color:var(--text-4);padding:4px 6px">No changes</div>';
  } else {
    list.innerHTML = files.map(f => {
      const onclickAttr = clickable ? ' onclick="openFile(\'' + escapeHTML(f) + '\')"' : '';
      const colorStyle = color ? ' style="color:' + color + '"' : '';
      const btnLabel = actionFn === 'stageFile' ? '+' : '\u2212';
      return '<div class="scm-file-row"><span class="scm-file-indicator"' + colorStyle + '>' + indicator + '</span><span class="scm-file-label" title="' + escapeHTML(f) + '"' + onclickAttr + '>' + escapeHTML(f) + '</span><button class="scm-file-action" onclick="' + actionFn + '(\'' + escapeHTML(f) + '\')">' + btnLabel + '</button></div>';
    }).join('');
  }
  const cnt = document.getElementById(countId);
  if (cnt) cnt.textContent = files.length;
}

async function stageFile(file) {
  await fetch(`${API_BASE}/git/stage`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ files: [file] }) });
  refreshSCM();
}

async function unstageFile(file) {
  await fetch(`${API_BASE}/git/unstage`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ files: [file] }) });
  refreshSCM();
}

async function commitSCM() {
  const msgEl = document.getElementById('scmCommitMsg');
  const msg = msgEl ? msgEl.value.trim() : '';
  if (!msg) { showToast('Enter a commit message'); return; }
  try {
    const res = await fetch(`${API_BASE}/git/commit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    if (msgEl) msgEl.value = '';
    showToast('Committed!');
    refreshSCM();
  } catch (err) { showToast('Commit failed: ' + err.message); }
}

async function gitAction(action) {
  showToast('Running git ' + action + '…');
  try {
    const res = await fetch(`${API_BASE}/git/${action}`, { method: 'POST' });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    showToast('git ' + action + ' done');
    refreshSCM();
  } catch (err) { showToast(action + ' failed: ' + err.message); }
}

async function gitInit() {
  try {
    await fetch(`${API_BASE}/git/init`, { method: 'POST' });
    showToast('Repository initialized!');
    refreshSCM();
  } catch (err) { showToast('Init failed: ' + err.message); }
}

async function showBranchesDialog() {
  try {
    const res = await fetch(`${API_BASE}/git/branches`);
    const data = await res.json();
    const action = prompt('Branches:\n' + (data.branches || []).join('\n') + '\n\nType: create NAME | switch NAME | delete NAME | cancel');
    if (!action || action === 'cancel') return;
    const parts = action.trim().split(/\s+/);
    const cmd = parts[0];
    const name = parts.slice(1).join(' ');
    if (cmd === 'create') await fetch(`${API_BASE}/git/branch/create`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
    else if (cmd === 'switch') await fetch(`${API_BASE}/git/branch/switch`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
    else if (cmd === 'delete') await fetch(`${API_BASE}/git/branch/${name}`, { method: 'DELETE' });
    showToast('Branch ' + cmd + ': ' + name);
    refreshSCM();
  } catch (err) { showToast('Branch op failed: ' + err.message); }
}

async function loadGitHubStatus() {
  const el = document.getElementById('scmGitHubStatus');
  if (!el) return;
  try {
    const data = await (await fetch(`${API_BASE}/settings`)).json();
    if (data.github_username) {
      el.innerHTML = '<div style="font-size:12px;color:var(--text-2)">Connected as <b>' + escapeHTML(data.github_username) + '</b></div><button class="pv-btn danger" onclick="disconnectGitHub()" style="margin-top:6px;display:block;width:100%">Disconnect</button><button class="pv-btn" onclick="listGitHubRepos()" style="margin-top:4px;display:block;width:100%">List Repositories</button>';
    }
  } catch (err) { /* GitHub not configured — silently ignore */ }
}

async function connectGitHub() {
  const token = prompt('Enter your GitHub Personal Access Token:');
  if (!token) return;
  try {
    const res = await fetch(`${API_BASE}/github/connect`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token }) });
    if (!res.ok) throw new Error((await res.json()).detail || 'Invalid token');
    showToast('Connected as ' + (await res.json()).username);
    loadGitHubStatus();
  } catch (err) { showToast('GitHub connection failed: ' + err.message); }
}

async function disconnectGitHub() {
  if (!confirm('Disconnect GitHub?')) return;
  await fetch(`${API_BASE}/github/disconnect`, { method: 'DELETE' });
  showToast('GitHub disconnected');
  loadGitHubStatus();
}

async function listGitHubRepos() {
  const content = document.getElementById('scmGitHubContent');
  if (!content) return;
  try {
    const res = await fetch(`${API_BASE}/github/repos`);
    const data = await res.json();
    content.innerHTML += '<div class="scm-repo-list" style="margin-top:6px">' + (data.repos || []).map(r => '<div class="scm-repo-item" onclick="cloneRepo(\'' + escapeHTML(r.clone_url) + '\')"><span>' + (r.private ? '\uD83D\uDD12' : '\uD83D\uDCD6') + '</span><span>' + escapeHTML(r.name) + '</span></div>').join('') + '<div class="scm-repo-item" onclick="createGitHubRepo()" style="color:var(--accent-light);justify-content:center">+ Create New Repository</div></div>';
  } catch (err) { showToast('Failed to list repos: ' + err.message); }
}

async function cloneRepo(url) {
  if (!confirm('Clone ' + url + ' into this directory?')) return;
  try {
    await fetch(`${API_BASE}/git/clone`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) });
    showToast('Repository cloned!');
    refreshSCM();
  } catch (err) { showToast('Clone failed: ' + err.message); }
}

async function createGitHubRepo() {
  const name = prompt('Repository name:');
  if (!name) return;
  const isPrivate = confirm('Make it private? (OK=yes, Cancel=public)');
  try {
    const res = await fetch(`${API_BASE}/github/repos/create`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, private: isPrivate }) });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    const data = await res.json();
    showToast('Repo ' + data.name + ' created!');
    await fetch(`${API_BASE}/github/remote`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ remote_url: data.clone_url }) });
    showToast('Remote set. You can now push!');
  } catch (err) { showToast('Create repo failed: ' + err.message); }
}

function toggleScmSection(header) {
  const chevron = header.querySelector('.scm-chevron');
  const list = header.nextElementSibling;
  if (!list) return;
  list.style.display = list.style.display === 'none' ? '' : 'none';
  if (chevron) chevron.classList.toggle('collapsed', list.style.display === 'none');
}

// ═══════════════════════════════════════════════════════════════════════
//  ACTIVITY PANEL
// ═══════════════════════════════════════════════════════════════════════

const activityTabEl = document.querySelector('.sidebar-tab[data-tab="activity"]');
if (activityTabEl) {
  activityTabEl.addEventListener('click', () => { pollActivity(); });
}

function renderActivity(activities) {
  const log = document.getElementById('activityLog');
  if (!log || !activities || !activities.length) return;
  const existingCount = log.querySelectorAll('.activity-entry').length;
  const newItems = activities.slice(existingCount);
  newItems.forEach(a => {
    const tagClass = 'agent-' + (a.agent || 'coordinator');
    const entry = document.createElement('div');
    entry.className = 'activity-entry';
    entry.innerHTML = '<span class="activity-agent-tag ' + tagClass + '">' + (a.agent || 'CO').toUpperCase() + '</span><span class="activity-entry-text">' + escapeHTML(a.message || '') + '</span><span class="activity-entry-time">' + escapeHTML(a.time || '') + '</span>';
    log.appendChild(entry);
  });
  log.scrollTop = log.scrollHeight;
  const last = activities[activities.length - 1];
  if (last && last.progress !== undefined) updateActivityProgress(last.progress);
}

function updateActivityProgress(pct) {
  const fill = document.getElementById('activityProgressFill');
  const text = document.getElementById('activityProgressText');
  if (fill) fill.style.width = Math.min(100, pct) + '%';
  if (text) text.textContent = pct + '%';
}

async function pollActivity() {
  try {
    const log = document.getElementById('activityLog');
    const since = log ? log.querySelectorAll('.activity-entry').length : 0;
    const res = await fetch(`${API_BASE}/activity?since=${since}`);
    const data = await res.json();
    if (data.activity) renderActivity(data.activity);
    if (data.tasks && data.tasks.length > 0) {
      const latest = data.tasks[0];
      document.getElementById('activityTaskTitle').textContent = latest.title || 'No active task';
      updateActivityProgress(latest.progress || 0);
    }
  } catch (err) { /* silently ignore */ }
}

// ═══════════════════════════════════════════════════════════════════════
//  WORKSPACE DASHBOARD
// ═══════════════════════════════════════════════════════════════════════

let workspacesData = [];
let dashboardSort = 'date';

// Show dashboard on load
window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('dashboard').classList.add('active');
  loadWorkspaces();
  wireDashboard();
});

function wireDashboard() {
  document.getElementById('dashboardSearch')?.addEventListener('input', e => renderWorkspaces(workspacesData, e.target.value));
  document.querySelectorAll('.dashboard-sort-btn').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.dashboard-sort-btn').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    dashboardSort = b.dataset.sort;
    renderWorkspaces(workspacesData, document.getElementById('dashboardSearch')?.value || '');
  }));
  document.querySelectorAll('.template-card').forEach(b => b.addEventListener('click', () => createFromTemplate(b.dataset.template)));
  document.getElementById('sidebarWorkspace')?.addEventListener('click', () => {
    document.getElementById('dashboard').classList.add('active');
    welcomeEl.style.display = 'none';
    loadWorkspaces();
  });
}

async function loadWorkspaces() {
  try {
    const res = await fetch(`${API_BASE}/workspaces`);
    const data = await res.json();
    workspacesData = data.workspaces || [];
    renderWorkspaces(workspacesData);
  } catch (err) {
    document.getElementById('dashboardGrid').innerHTML = '<div class="ft-error">Failed to load workspaces</div>';
  }
}

function renderWorkspaces(data, query) {
  const grid = document.getElementById('dashboardGrid');
  if (!grid) return;
  let filtered = data;
  if (query) {
    const q = query.toLowerCase();
    filtered = data.filter(w => w.name.toLowerCase().includes(q) || (w.description || '').toLowerCase().includes(q) || (w.tags || '').toLowerCase().includes(q));
  }
  if (dashboardSort === 'name') filtered.sort((a, b) => a.name.localeCompare(b.name));
  else if (dashboardSort === 'favorite') filtered.sort((a, b) => (b.favorite || 0) - (a.favorite || 0));
  // default: date (already sorted by API)

  grid.innerHTML = filtered.map(w => `
    <div class="project-card${w.favorite ? ' favorite' : ''}" onclick="openWorkspace('${w.id}')">
      <div class="project-card-top">
        <span class="project-card-icon">${escapeHTML(w.icon || '📁')}</span>
        <button class="project-card-fav${w.favorite ? ' active' : ''}" onclick="event.stopPropagation();toggleFavorite('${w.id}',${w.favorite ? 0 : 1})">${w.favorite ? '★' : '☆'}</button>
      </div>
      <div class="project-card-name">${escapeHTML(w.name)}</div>
      <div class="project-card-desc">${escapeHTML(w.description || 'No description')}</div>
      <div class="project-card-meta">
        <span>${escapeHTML(w.language || 'Unknown')}</span>
        <span>${escapeHTML(w.framework || '')}</span>
        <span>${(w.last_opened_at || '').substring(0,10)}</span>
      </div>
      <div class="project-card-actions">
        <button class="project-card-btn" onclick="event.stopPropagation();renameWorkspace('${w.id}','${escapeHTML(w.name)}')">Rename</button>
        <button class="project-card-btn" onclick="event.stopPropagation();duplicateWorkspace('${w.id}')">Duplicate</button>
        <button class="project-card-btn danger" onclick="event.stopPropagation();deleteWorkspace('${w.id}')">Delete</button>
      </div>
    </div>
  `).join('') + `
    <div class="project-card-new" onclick="showCreateProject()">
      <span class="project-card-new-icon">+</span>
      <span>New Project</span>
    </div>
  `;
}

async function openWorkspace(id) {
  try {
    await fetch(`${API_BASE}/workspaces/${id}`, {
      method: 'PUT', headers: apiHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({}),  // just updates last_opened
    });
    const ws = workspacesData.find(w => w.id === id);
    if (ws) {
      persistWorkspace({ id: ws.id, name: ws.name, icon: ws.icon, framework: ws.framework });
      const sn = document.getElementById('sidebarWsName');
      const si = document.getElementById('sidebarWsIcon');
      if (sn) sn.textContent = ws.name;
      if (si) si.textContent = ws.icon || '📁';
      try { loadFileTree(); } catch (_) {}
      try { maybeAutoPreview(); } catch (_) {}
    }
    document.getElementById('dashboard').classList.remove('active');
  } catch (err) { showToast('Failed to open: ' + err.message); }
}

async function toggleFavorite(id, val) {
  try {
    await fetch(`${API_BASE}/workspaces/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ favorite: val }),
    });
    loadWorkspaces();
  } catch (err) { showToast('Failed: ' + err.message); }
}

async function deleteWorkspace(id) {
  if (!confirm('Delete this project? This cannot be undone.')) return;
  try {
    await fetch(`${API_BASE}/workspaces/${id}`, { method: 'DELETE' });
    showToast('Project deleted');
    loadWorkspaces();
  } catch (err) { showToast('Delete failed: ' + err.message); }
}

function showCreateProject() {
  const name = prompt('Project name:');
  if (!name) return;
  const desc = prompt('Description (optional):') || '';
  const lang = prompt('Language (e.g. Python, JavaScript):') || '';
  const framework = prompt('Framework (e.g. FastAPI, React):') || '';
  createWorkspace(name, desc, lang, framework, '');
}

function createFromTemplate(tpl) {
  const map = { react: 'React', nextjs: 'Next.js', python: 'Python', fastapi: 'FastAPI', nodejs: 'Node.js', html: 'HTML/CSS/JS', empty: '' };
  const name = prompt('Project name: ' + (map[tpl] || tpl));
  if (!name) return;
  const langMap = { react: 'JavaScript', nextjs: 'TypeScript', python: 'Python', fastapi: 'Python', nodejs: 'JavaScript', html: 'HTML' };
  createWorkspace(name, map[tpl] + ' project', langMap[tpl] || '', map[tpl] || '', tpl);
}

async function createWorkspace(name, desc, lang, fw, tpl) {
  try {
    const res = await fetch(`${API_BASE}/workspaces`, {
      method: 'POST', headers: apiHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ name, description: desc, language: lang, framework: fw, template: tpl }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
    const created = await res.json();
    persistWorkspace({ id: created.id, name, icon: '📁', framework: fw });
    showToast('Project created: ' + name);
    loadWorkspaces();
    try { loadFileTree(); } catch (_) {}
    try { maybeAutoPreview(); } catch (_) {}
  } catch (err) { showToast('Create failed: ' + err.message); }
}

async function renameWorkspace(id, oldName) {
  const name = prompt('New name:', oldName);
  if (!name || name === oldName) return;
  try {
    await fetch(`${API_BASE}/workspaces/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    loadWorkspaces();
  } catch (err) { showToast('Rename failed: ' + err.message); }
}

async function duplicateWorkspace(id) {
  const ws = workspacesData.find(w => w.id === id);
  if (!ws) return;
  createWorkspace(ws.name + ' (Copy)', ws.description, ws.language, ws.framework, '');
}

// ═══════════════════════════════════════════════════════════════════════
//  CODEBASE INTELLIGENCE PANEL
// ═══════════════════════════════════════════════════════════════════════

const codebaseTabEl = document.querySelector('.sidebar-tab[data-tab="codebase"]');
if (codebaseTabEl) {
  codebaseTabEl.addEventListener('click', () => { loadCodebaseStats(); });
}

document.getElementById('codebaseRefresh')?.addEventListener('click', reindexCodebase);
document.getElementById('codebaseSearch')?.addEventListener('input', e => searchCodebase(e.target.value));

async function loadCodebaseStats() {
  try {
    const res = await fetch(`${API_BASE}/codebase/stats`);
    const data = await res.json();
    document.getElementById('codebaseFiles').textContent = data.total_files || 0;
    document.getElementById('codebaseSymbols').textContent = data.total_symbols || 0;
  } catch (err) { /* ignore */ }
}

async function reindexCodebase() {
  showToast('Indexing codebase…');
  try {
    const res = await fetch(`${API_BASE}/codebase/index`, { method: 'POST' });
    const data = await res.json();
    document.getElementById('codebaseFiles').textContent = (data.stats && data.stats.total_files) || 0;
    document.getElementById('codebaseSymbols').textContent = (data.stats && data.stats.total_symbols) || 0;
    showToast('Indexed ' + (data.stats && data.stats.total_symbols) + ' symbols');
  } catch (err) { showToast('Index failed: ' + err.message); }
}

async function searchCodebase(q) {
  const resultsEl = document.getElementById('codebaseResults');
  if (!q) { resultsEl.innerHTML = '<div style="font-size:11px;color:var(--text-4);padding:12px 8px">Type to search symbols.</div>'; return; }
  try {
    const res = await fetch(`${API_BASE}/codebase/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    const results = data.results || [];
    resultsEl.innerHTML = results.length
      ? results.map(r => `<div class="codebase-result" onclick="openFile('${escapeHTML(r.file)}')"><span class="codebase-result-type ${r.type}">${r.type}</span><span class="codebase-result-name">${escapeHTML(r.name)}</span><span class="codebase-result-file">${escapeHTML(r.file)}:${r.line}</span></div>`).join('')
      : '<div style="font-size:11px;color:var(--text-4);padding:12px 8px">No matches. Click ↺ to re-index.</div>';
  } catch (err) { /* ignore */ }
}

// ═══════════════════════════════════════════════════════════════════════
//  DATABASE STUDIO
// ═══════════════════════════════════════════════════════════════════════

const databaseTabEl = document.querySelector('.sidebar-tab[data-tab="database"]');
if (databaseTabEl) {
  databaseTabEl.addEventListener('click', () => {
    document.getElementById('databaseView').classList.toggle('hidden');
    if (!document.getElementById('databaseView').classList.contains('hidden')) {
      loadDbTables();
    }
  });
}

async function loadDbTables() {
  try {
    const res = await fetch(`${API_BASE}/db/tables`);
    const data = await res.json();
    const list = document.getElementById('dbTableList');
    const tables = data.tables || [];
    list.innerHTML = tables.map(t => `<div class="db-table-item" onclick="loadDbTable('${t}')">📋 ${escapeHTML(t)}</div>`).join('') || '<div style="font-size:11px;color:var(--text-4);padding:8px">No tables</div>';
  } catch (err) { document.getElementById('dbTableList').innerHTML = '<div style="font-size:11px;color:#F87171;padding:8px">Failed to load</div>'; }
}

async function loadDbTable(name) {
  document.getElementById('dbTableTitle').textContent = 'Table: ' + name;
  try {
    const res = await fetch(`${API_BASE}/db/table/${name}`);
    const data = await res.json();
    document.getElementById('dbEditor').value = `SELECT * FROM "${name}" LIMIT 50;`;
    showDbResult({ type: 'schema', table: data });
  } catch (err) { /* ignore */ }
}

async function runDbQuery() {
  const sql = document.getElementById('dbEditor').value.trim();
  if (!sql) return;
  const resultsEl = document.getElementById('dbResults');
  resultsEl.innerHTML = '<div class="db-results-placeholder">Running…</div>';
  try {
    await fetch(`${API_BASE}/db/history`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sql }) });
    const res = await fetch(`${API_BASE}/db/query`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sql }) });
    const data = await res.json();
    let html = '';
    if (data.elapsed_ms) html += `<div class="db-meta">${data.statements} statement(s) — ${data.elapsed_ms}ms</div>`;
    (data.results || []).forEach(r => {
      if (r.type === 'error') {
        html += `<div class="db-error">${escapeHTML(r.message)}</div>`;
      } else if (r.type === 'write') {
        html += `<div class="db-meta">✓ ${r.affected} rows affected</div>`;
        loadDbTables();
      } else {
        html += `<table class="db-results-table"><thead><tr>${(r.columns||[]).map(c => `<th>${escapeHTML(c)}</th>`).join('')}</tr></thead><tbody>${(r.rows||[]).map(row => `<tr>${(r.columns||[]).map(c => `<td>${escapeHTML(String(row[c] ?? ''))}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
        html += `<div class="db-meta">${r.count} rows</div>`;
      }
    });
    resultsEl.innerHTML = html || '<div class="db-results-placeholder">Query executed</div>';
  } catch (err) { resultsEl.innerHTML = `<div class="db-error">${escapeHTML(err.message)}</div>`; }
}

// ── Init ───────────────────────────────────────────────────────────────
updateTermPrompt();
renderTerminalTabs();
messageInput.focus();

// ═══════════════════════════════════════════════════════════════════════
//  BROWSER PANEL (Phase 2A)
// ═══════════════════════════════════════════════════════════════════════
(function initBrowserPanel() {
  const statusEl = document.getElementById('brStatus');
  const urlEl = document.getElementById('brUrl');
  const titleEl = document.getElementById('brTitle');
  const tabsEl = document.getElementById('brTabs');
  if (!statusEl) return;

  async function refreshBrowserStatus() {
    try {
      const r = await fetch(`${API_BASE}/browser/status`);
      const d = await r.json();
      statusEl.textContent = d.running ? 'running' : 'idle';
      const active = (d.tabs || []).find(t => t.active);
      urlEl.textContent = active ? active.url : '—';
      titleEl.textContent = active ? (active.title || '—') : '—';
      if (tabsEl) {
        tabsEl.innerHTML = (d.tabs || []).map(t =>
          `<div style="padding:4px 6px;border-radius:4px;background:${t.active ? 'var(--bg-3)' : 'transparent'};cursor:pointer" data-tab-id="${t.id}">
            ${t.active ? '● ' : ''}${escapeHTML(t.title || t.url || t.id)}
          </div>`
        ).join('') || '<div style="color:var(--text-4)">No tabs</div>';
        tabsEl.querySelectorAll('[data-tab-id]').forEach(el => {
          el.addEventListener('click', async () => {
            await fetch(`${API_BASE}/browser/tab/select`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ tab_id: el.getAttribute('data-tab-id') }),
            });
            refreshBrowserStatus();
          });
        });
      }
    } catch (e) {
      statusEl.textContent = 'error';
    }
  }

  document.getElementById('brLaunch')?.addEventListener('click', async () => {
    statusEl.textContent = 'launching…';
    await fetch(`${API_BASE}/browser/launch`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ headless: true }),
    });
    refreshBrowserStatus();
  });
  document.getElementById('brClose')?.addEventListener('click', async () => {
    await fetch(`${API_BASE}/browser/close`, { method: 'POST' });
    refreshBrowserStatus();
  });
  document.getElementById('brRefreshStatus')?.addEventListener('click', refreshBrowserStatus);
  document.getElementById('brGo')?.addEventListener('click', async () => {
    const url = document.getElementById('brUrlInput')?.value?.trim();
    if (!url) return;
    await fetch(`${API_BASE}/browser/goto`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    refreshBrowserStatus();
  });

  // Refresh when browser tab shown
  document.querySelectorAll('.sidebar-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.getAttribute('data-tab') === 'browser') refreshBrowserStatus();
    });
  });
})();

/* ── Vision panel (Phase 2C) ─────────────────────────────────────── */
(function initVisionPanel() {
  const statusEl = document.getElementById('visionStatus');
  const issuesEl = document.getElementById('visionIssues');
  const ocrEl = document.getElementById('visionOcr');
  const confEl = document.getElementById('visionConfidence');
  const fixesEl = document.getElementById('visionFixes');
  const shotEl = document.getElementById('visionShot');

  async function captureAnd(endpoint, bodyExtra = {}) {
    statusEl.textContent = 'capturing…';
    let screenshot = '';
    try {
      const r = await fetch(`${API_BASE}/browser/screenshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_page: false }),
      });
      const j = await r.json();
      screenshot = j.path || j.data || j.screenshot || '';
      if (j.path && shotEl) {
        // try serve local path via files or just note it
        shotEl.style.display = 'none';
      }
    } catch (e) {
      statusEl.textContent = 'browser screenshot failed – provide path manually';
      return;
    }
    if (!screenshot) {
      statusEl.textContent = 'no screenshot available';
      return;
    }
    statusEl.textContent = 'analyzing…';
    try {
      const r = await fetch(`${API_BASE}/vision/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ screenshot, ...bodyExtra }),
      });
      const j = await r.json();
      statusEl.textContent = j.message || 'done';
      if (confEl) confEl.textContent = `Confidence: ${(j.confidence ?? 0).toFixed(2)}`;
      if (issuesEl) issuesEl.textContent = JSON.stringify(j.issues || [], null, 2);
      if (ocrEl && j.data && j.data.full_text) ocrEl.textContent = j.data.full_text;
      if (ocrEl && j.data && j.data.ocr && j.data.ocr.full_text) ocrEl.textContent = j.data.ocr.full_text;
      if (fixesEl) {
        fixesEl.innerHTML = '';
        (j.issues || []).forEach(iss => {
          const li = document.createElement('li');
          li.textContent = iss.message || iss.type;
          fixesEl.appendChild(li);
        });
      }
    } catch (e) {
      statusEl.textContent = 'vision request failed: ' + e;
    }
  }

  document.getElementById('visionAnalyzeBtn')?.addEventListener('click', () => captureAnd('analyze'));
  document.getElementById('visionOcrBtn')?.addEventListener('click', () => captureAnd('ocr'));
  document.getElementById('visionLayoutBtn')?.addEventListener('click', () => captureAnd('layout'));

  // ensure tab switching shows vision panel
  document.querySelectorAll('.sidebar-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.getAttribute('data-tab') === 'vision') {
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
        document.getElementById('visionTab')?.classList.remove('hidden');
      }
    });
  });
})();

/* ── Knowledge panel (Phase 3A) ──────────────────────────────────── */
(function initKnowledgePanel() {
  const statusEl = document.getElementById('knowledgeStatus');
  const resultsEl = document.getElementById('knowledgeResults');
  const citesEl = document.getElementById('knowledgeCites');

  document.getElementById('knowledgeSearchBtn')?.addEventListener('click', async () => {
    const q = document.getElementById('knowledgeQuery')?.value?.trim();
    if (!q) return;
    statusEl.textContent = 'searching…';
    try {
      const r = await fetch(`${API_BASE}/knowledge/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, top_k: 8 }),
      });
      const j = await r.json();
      statusEl.textContent = `Found ${j.count ?? 0} passages`;
      resultsEl.textContent = (j.results || []).map(h =>
        `[${(h.score ?? 0).toFixed(3)}] ${h.title || h.source}\n${(h.text || '').slice(0, 220)}\n`
      ).join('\n');
      citesEl.innerHTML = '';
      (j.citations || []).forEach(c => {
        const li = document.createElement('li');
        li.textContent = `[${c.index}] ${c.title} (${c.score})`;
        citesEl.appendChild(li);
      });
    } catch (e) {
      statusEl.textContent = 'search failed: ' + e;
    }
  });

  document.getElementById('knowledgeReindexBtn')?.addEventListener('click', async () => {
    statusEl.textContent = 'reindexing…';
    try {
      const r = await fetch(`${API_BASE}/knowledge/reindex`, { method: 'POST' });
      const j = await r.json();
      statusEl.textContent = `Imported ${j.imported ?? 0} docs`;
    } catch (e) {
      statusEl.textContent = 'reindex failed: ' + e;
    }
  });

  document.getElementById('knowledgeListBtn')?.addEventListener('click', async () => {
    try {
      const r = await fetch(`${API_BASE}/knowledge/list`);
      const j = await r.json();
      resultsEl.textContent = (j.documents || []).map(d =>
        `${d.title || d.doc_id} – ${d.source} (${d.char_count || 0} chars)`
      ).join('\n');
      statusEl.textContent = `${(j.documents || []).length} documents`;
    } catch (e) {
      statusEl.textContent = 'list failed: ' + e;
    }
  });

  document.querySelectorAll('.sidebar-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.getAttribute('data-tab') === 'knowledge') {
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
        document.getElementById('knowledgeTab')?.classList.remove('hidden');
      }
    });
  });
})();

/* ── Multi-Agent panel (Phase 3B) ────────────────────────────────── */
(function initMultiAgentPanel() {
  const statusEl = document.getElementById('maStatus');
  const agentsEl = document.getElementById('maAgents');
  const tasksEl = document.getElementById('maTasks');
  const msgsEl = document.getElementById('maMsgs');

  async function refreshAgents() {
    try {
      const r = await fetch(`${API_BASE}/multiagent/agents`);
      const j = await r.json();
      agentsEl.textContent = (j.agents || []).map(a =>
        `${a.active ? '●' : '○'} ${a.role} – ${a.description}`
      ).join('\n');
    } catch (e) { /* ignore */ }
  }

  document.getElementById('maStartBtn')?.addEventListener('click', async () => {
    const goal = document.getElementById('maGoal')?.value?.trim();
    if (!goal) return;
    statusEl.textContent = 'starting team…';
    try {
      const r = await fetch(`${API_BASE}/multiagent/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, auto_run: true, max_steps: 12 }),
      });
      const j = await r.json();
      statusEl.textContent = `Goal started – ${j.plan?.count || 0} tasks`;
      tasksEl.textContent = JSON.stringify(j.run?.queue || j.plan, null, 2);
      refreshAgents();
    } catch (e) {
      statusEl.textContent = 'start failed: ' + e;
    }
  });

  document.getElementById('maStatusBtn')?.addEventListener('click', async () => {
    try {
      const r = await fetch(`${API_BASE}/multiagent/status`);
      const j = await r.json();
      statusEl.textContent = `Goal: ${j.context_goal || 'none'} | msgs=${j.messages}`;
      agentsEl.textContent = (j.agents || []).map(a =>
        `${a.active ? '●' : '○'} ${a.role}`
      ).join('\n');
      tasksEl.textContent = JSON.stringify(j.queue || {}, null, 2);
    } catch (e) {
      statusEl.textContent = 'status failed: ' + e;
    }
  });

  document.getElementById('maTasksBtn')?.addEventListener('click', async () => {
    try {
      const r = await fetch(`${API_BASE}/multiagent/tasks`);
      const j = await r.json();
      tasksEl.textContent = (j.tasks || []).map(t =>
        `[${t.status}] ${t.role}: ${t.title}`
      ).join('\n');
    } catch (e) {
      statusEl.textContent = 'tasks failed: ' + e;
    }
  });

  document.getElementById('maMsgsBtn')?.addEventListener('click', async () => {
    try {
      const r = await fetch(`${API_BASE}/multiagent/messages?limit=30`);
      const j = await r.json();
      msgsEl.textContent = (j.messages || []).map(m =>
        `${m.from_agent}→${m.to_agent}: ${m.body}`
      ).join('\n');
    } catch (e) {
      statusEl.textContent = 'messages failed: ' + e;
    }
  });

  document.querySelectorAll('.sidebar-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.getAttribute('data-tab') === 'multiagent') {
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
        document.getElementById('multiagentTab')?.classList.remove('hidden');
        refreshAgents();
      }
    });
  });
})();

/* ── System panel (Phase 3C) ─────────────────────────────────────── */
(function initSystemPanel() {
  const statusEl = document.getElementById('sysStatus');
  const healthEl = document.getElementById('sysHealth');
  const metricsEl = document.getElementById('sysMetrics');

  async function get(path) {
    const r = await fetch(`${API_BASE}${path}`);
    return r.json();
  }

  document.getElementById('sysHealthBtn')?.addEventListener('click', async () => {
    statusEl.textContent = 'checking…';
    try {
      const j = await get('/system/health');
      statusEl.textContent = `Overall: ${j.overall}`;
      healthEl.textContent = (j.components || []).map(c =>
        `${c.status === 'healthy' ? '✓' : c.status === 'degraded' ? '~' : '✗'} ${c.name} (${c.latency_ms}ms) ${c.message || ''}`
      ).join('\n');
    } catch (e) { statusEl.textContent = 'health failed: ' + e; }
  });

  document.getElementById('sysMetricsBtn')?.addEventListener('click', async () => {
    try {
      const j = await get('/system/metrics');
      statusEl.textContent = `Uptime ${j.uptime_s}s`;
      metricsEl.textContent = JSON.stringify(j, null, 2);
    } catch (e) { statusEl.textContent = 'metrics failed: ' + e; }
  });

  document.getElementById('sysDiagBtn')?.addEventListener('click', async () => {
    statusEl.textContent = 'diagnosing…';
    try {
      const j = await get('/system/diagnostics');
      statusEl.textContent = `${(j.failed_or_degraded||[]).length} issues`;
      metricsEl.textContent = JSON.stringify({
        suggestions: j.suggestions,
        recovery_actions: j.recovery_actions,
        dependencies: j.dependencies,
        config_issues: j.config_issues,
      }, null, 2);
    } catch (e) { statusEl.textContent = 'diagnostics failed: ' + e; }
  });

  document.getElementById('sysEventsBtn')?.addEventListener('click', async () => {
    try {
      const j = await get('/system/events?limit=20');
      metricsEl.textContent = (j.events || []).map(e =>
        `${e.topic} @ ${e.source}`
      ).join('\n');
      statusEl.textContent = `${(j.events||[]).length} events`;
    } catch (e) { statusEl.textContent = 'events failed: ' + e; }
  });

  document.getElementById('sysWarmBtn')?.addEventListener('click', async () => {
    try {
      const r = await fetch(`${API_BASE}/system/warmup`, { method: 'POST' });
      const j = await r.json();
      statusEl.textContent = 'warmup done';
      metricsEl.textContent = JSON.stringify(j.results || j, null, 2);
    } catch (e) { statusEl.textContent = 'warmup failed: ' + e; }
  });

  document.querySelectorAll('.sidebar-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.getAttribute('data-tab') === 'system') {
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
        document.getElementById('systemTab')?.classList.remove('hidden');
      }
    });
  });
})();

/* ── Deployment panel (v4.0) ─────────────────────────────────────── */
(function initDeploymentPanel() {
  const statusEl = document.getElementById('depStatus');
  const outEl = document.getElementById('depOutput');

  document.getElementById('depBuildBtn')?.addEventListener('click', async () => {
    statusEl.textContent = 'building…';
    try {
      const r = await fetch(`${API_BASE}/deployment/build`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_dir: '.' }),
      });
      const j = await r.json();
      statusEl.textContent = `Build ${j.status}`;
      outEl.textContent = JSON.stringify(j, null, 2);
    } catch (e) { statusEl.textContent = 'build failed: ' + e; }
  });

  document.getElementById('depDeployBtn')?.addEventListener('click', async () => {
    const platform = document.getElementById('depPlatform')?.value || 'static';
    statusEl.textContent = 'deploying…';
    try {
      const r = await fetch(`${API_BASE}/deployment/deploy`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform, project_dir: '.', build_first: true }),
      });
      const j = await r.json();
      statusEl.textContent = `Deploy ${j.status} (${platform})`;
      outEl.textContent = JSON.stringify(j, null, 2);
    } catch (e) { statusEl.textContent = 'deploy failed: ' + e; }
  });

  document.getElementById('depHistoryBtn')?.addEventListener('click', async () => {
    try {
      const r = await fetch(`${API_BASE}/deployment/history`);
      const j = await r.json();
      outEl.textContent = (j.history || []).map(h =>
        `${h.deployment_id} [${h.platform}] ${h.status}`
      ).join('\n') || 'No history';
      statusEl.textContent = `${(j.history||[]).length} deployments`;
    } catch (e) { statusEl.textContent = 'history failed: ' + e; }
  });

  document.getElementById('depPlatformsBtn')?.addEventListener('click', async () => {
    try {
      const r = await fetch(`${API_BASE}/deployment/platforms`);
      const j = await r.json();
      outEl.textContent = (j.platforms || []).map(p =>
        `${p.name}: ${JSON.stringify(p.validation)}`
      ).join('\n');
      statusEl.textContent = 'platforms loaded';
    } catch (e) { statusEl.textContent = 'platforms failed: ' + e; }
  });

  document.querySelectorAll('.sidebar-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.getAttribute('data-tab') === 'deployment') {
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
        document.getElementById('deploymentTab')?.classList.remove('hidden');
      }
    });
  });
})();


/** Prefer index.html in the active project for Preview. */
async function maybeAutoPreview() {
  if (!currentWorkspace) return;
  try {
    const res = await fetch(`${API_BASE}/files`, { headers: apiHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    const flat = [];
    (function walk(nodes) {
      (nodes || []).forEach(n => {
        if (n.type === 'file') flat.push(n.path);
        if (n.children) walk(n.children);
      });
    })(data.files || []);
    const entry = flat.find(p => /(^|\/)index\.html$/i.test(p)) || flat.find(p => /\.html$/i.test(p));
    if (entry) {
      window.__lumoraPreviewEntry = entry;
      const hint = document.getElementById('previewEmptyHint');
      if (hint) {
        hint.innerHTML = '<p>Entry point detected: <strong>' + entry + '</strong></p>' +
          '<button type="button" class="pv-btn primary" id="btnOpenPreviewEntry">Open Preview</button>';
        document.getElementById('btnOpenPreviewEntry')?.addEventListener('click', () => {
          document.querySelector('.sidebar-tab[data-tab="preview"]')?.click();
          if (typeof openFile === 'function') openFile(entry);
        });
      }
    }
  } catch (_) {}
}

function applyTheme(mode) {
  const root = document.documentElement;
  let resolved = mode;
  if (mode === 'system') {
    resolved = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }
  root.setAttribute('data-theme', resolved);
  root.classList.toggle('theme-light', resolved === 'light');
  try { localStorage.setItem('lumora_theme', mode); } catch (_) {}
  const sel = document.getElementById('settingTheme');
  if (sel) sel.value = mode;
}
(function initTheme() {
  let mode = 'dark';
  try { mode = localStorage.getItem('lumora_theme') || 'dark'; } catch (_) {}
  applyTheme(mode);
  document.getElementById('settingTheme')?.addEventListener('change', e => applyTheme(e.target.value));
  document.getElementById('themeToggleBtn')?.addEventListener('click', () => {
    const cur = localStorage.getItem('lumora_theme') || 'dark';
    const next = cur === 'dark' ? 'light' : cur === 'light' ? 'system' : 'dark';
    applyTheme(next);
  });
})();

// Mobile "More" menu
document.getElementById('moreTabsBtn')?.addEventListener('click', () => {
  document.getElementById('moreTabsSheet')?.classList.toggle('open');
});
document.querySelectorAll('#moreTabsSheet [data-tab]').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.getAttribute('data-tab');
    document.querySelector(`.sidebar-tab[data-tab="${tab}"]`)?.click();
    document.getElementById('moreTabsSheet')?.classList.remove('open');
  });
});


/** Drive a queued generation job via bounded /tick calls until done or paused. */
async function driveJobTicks(jobId) {
  const stages = {
    queued: 'Queued…',
    planning: 'Planning your website…',
    generating: 'Generating files…',
    reviewing: 'Reviewing…',
    finishing: 'Finishing…',
    running: 'Working…',
    paused: 'Paused — send "continue" or retry.',
    completed: 'Completed.',
    failed: 'Failed.',
  };
  const statusEl = document.createElement('div');
  statusEl.className = 'job-progress-card';
  statusEl.innerHTML = '<div class="job-progress-title">Project generation</div>' +
    '<div class="job-progress-bar"><div class="job-progress-fill" style="width:2%"></div></div>' +
    '<div class="job-progress-meta">Starting…</div>';
  const chat = document.getElementById('chatMessages') || document.querySelector('.messages') || document.getElementById('chatArea');
  if (chat) chat.appendChild(statusEl);

  const maxTicks = 20;
  let lastStage = '';
  for (let i = 0; i < maxTicks; i++) {
    let job;
    try {
      const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/tick`, {
        method: 'POST',
        headers: apiHeaders({ 'Content-Type': 'application/json' }),
      });
      if (!res.ok) {
        const detail = await res.text().catch(() => res.statusText);
        statusEl.querySelector('.job-progress-meta').textContent = `Tick error: ${res.status} ${detail.slice(0, 120)}`;
        if (res.status === 503 || res.status === 429) {
          appendMessage('ai', 'Generation paused (provider limit or agent unavailable). Files created so far are kept. Retry later with Continue.');
          break;
        }
        // try continue once
        await new Promise(r => setTimeout(r, 1500));
        continue;
      }
      job = await res.json();
    } catch (err) {
      statusEl.querySelector('.job-progress-meta').textContent = 'Network error: ' + err.message;
      await new Promise(r => setTimeout(r, 2000));
      continue;
    }

    const progress = job.progress || 0;
    const stage = job.stage || job.status || 'running';
    const fill = statusEl.querySelector('.job-progress-fill');
    if (fill) fill.style.width = Math.max(2, progress) + '%';
    const meta = stages[stage] || stage;
    const files = (job.files_created || []).slice(0, 8).join(', ');
    statusEl.querySelector('.job-progress-meta').textContent =
      `${meta} (${progress}%)` + (files ? ` · ${files}` : '');

    if (stage !== lastStage) {
      lastStage = stage;
      const badge = document.querySelector('.nav-badge');
      if (badge) badge.textContent = stage === 'completed' ? 'Ready' : ('Stage ' + Math.min(5, Math.ceil(progress / 20) || 1));
    }

    if (job.workspace_id) {
      if (!currentWorkspace || currentWorkspace.id !== job.workspace_id) {
        persistWorkspace({ id: job.workspace_id, name: job.workspace_id });
      }
    }
    try { loadFileTree(); } catch (_) {}
    try { maybeAutoPreview(); } catch (_) {}

    if (job.status === 'completed') {
      statusEl.querySelector('.job-progress-meta').textContent = 'Completed (100%)';
      if (fill) fill.style.width = '100%';
      appendMessage('ai', job.response || ('Project generation completed. Files: ' + (job.files_created || []).join(', ')));
      try { localStorage.removeItem('lumora_active_job'); } catch (_) {}
      return job;
    }
    if (job.status === 'paused' || job.status === 'failed') {
      appendMessage('ai', 'Generation ' + job.status + (job.error ? (': ' + job.error) : '') +
        '\\n\\nYou can continue later. Files so far: ' + (job.files_created || []).join(', '));
      return job;
    }
    // brief pause between ticks
    await new Promise(r => setTimeout(r, 400));
  }
  appendMessage('ai', 'Generation still running after max ticks. Open Files to see progress, or send "continue".');
  return null;
}

// Resume active job after refresh
(async function resumeActiveJob() {
  try {
    const id = localStorage.getItem('lumora_active_job');
    if (!id) return;
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(id)}`, { headers: apiHeaders() });
    if (!res.ok) return;
    const job = await res.json();
    if (job.status === 'completed' || job.status === 'failed') {
      localStorage.removeItem('lumora_active_job');
      return;
    }
    if (job.status === 'queued' || job.status === 'running' || job.status === 'paused' || job.partial) {
      await driveJobTicks(id);
    }
  } catch (_) {}
})();
