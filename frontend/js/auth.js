const API_BASE = '/api';

async function apiRequest(path, options = {}) {
  const token = localStorage.getItem('metafoco_token');
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    if (window.location.pathname !== '/login') {
      localStorage.removeItem('metafoco_token');
      window.location.href = '/login';
    }
    throw new Error('Não autorizado');
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const d = await res.json();
      detail = d.detail || detail;
    } catch (e) {}
    throw new Error(detail);
  }
  return res.json();
}

function getToken() { return localStorage.getItem('metafoco_token'); }
function getUser() {
  try { return JSON.parse(localStorage.getItem('metafoco_user')) || null; }
  catch (e) { return null; }
}
function setAuth(token, user) {
  localStorage.setItem('metafoco_token', token);
  localStorage.setItem('metafoco_user', JSON.stringify(user));
}
function logout() {
  localStorage.removeItem('metafoco_token');
  localStorage.removeItem('metafoco_user');
  window.location.href = '/login';
}

function isLeitura() { const u = getUser(); return u && u.perfil === 'LEITURA'; }
function isGestor() { const u = getUser(); return u && ['SUPERADMIN','GESTOR'].includes(u.perfil); }
function isAdmin() { const u = getUser(); return u && u.perfil === 'SUPERADMIN'; }

function fmtMoney(v) {
  if (v == null || isNaN(v)) return '—';
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function fmtNum(v, decimals = 2) {
  if (v == null || isNaN(v)) return '—';
  return v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: decimals });
}

function fmtPct(v) {
  if (v == null || isNaN(v)) return '—';
  return (v * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + '%';
}

// Toast helper
function toast(message, type = 'info', duration = 3500) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => { el.classList.add('hide'); setTimeout(() => el.remove(), 300); }, duration);
}

// Renderiza topbar + perfis dinâmicos
function renderTopbar(activeLink) {
  const user = getUser();
  if (!user) return;
  const topbar = document.getElementById('topbar-dynamic') || document.body;

  // Determinar links permitidos
  let links = '<a class="navlink" data-link="dashboard" href="/dashboard">Dashboard</a>';
  if (isGestor()) {
    links += '<a class="navlink" data-link="contratos" href="/contratos">Contratos</a>';
    links += '<a class="navlink" data-link="upload" href="/upload">Upload</a>';
  }
  if (isAdmin()) {
    links += '<a class="navlink" data-link="usuarios" href="/usuarios">Usuários</a>';
  }

  if (document.getElementById('navlinks-js')) {
    document.getElementById('navlinks-js').innerHTML = links;
  }

  // Perfil badge
  const perfilLabel = user.perfil === 'SUPERADMIN' ? 'SuperAdmin' : (user.perfil === 'GESTOR' ? 'Gestor' : 'Leitura');
  const perfilClass = user.perfil === 'SUPERADMIN' ? 'superadmin' : (user.perfil === 'GESTOR' ? 'gestor' : 'leitura');

  const userChip = document.getElementById('user-chip-js');
  if (userChip) {
    const initials = (user.nome[0] || '') + (user.sobrenome[0] || '');
    userChip.innerHTML = `
      <span class="avatar">${initials.toUpperCase()}</span>
      <span>${user.nome} ${user.sobrenome}</span>
      <span class="perfil-badge ${perfilClass}">${perfilLabel}</span>
    `;
    userChip.querySelector('.avatar');
    // menu
    const menu = document.getElementById('user-menu-js');
    if (menu) {
      menu.innerHTML = `
        <div class="menu-header">${user.email}</div>
        <button class="menu-item" data-action="trocar-senha">Alterar senha</button>
        <button class="menu-item danger" data-action="logout">Sair</button>
      `;
      menu.querySelector('[data-action="logout"]').addEventListener('click', () => logout());
      if (menu.querySelector('[data-action="trocar-senha"]')) {
        menu.querySelector('[data-action="trocar-senha"]').addEventListener('click', () => openChangePasswordModal());
      }
      userChip.addEventListener('click', (e) => {
        e.stopPropagation();
        menu.classList.toggle('open');
      });
      document.addEventListener('click', (e) => {
        if (!userChip.contains(e.target)) menu.classList.remove('open');
      });
    }
  }

  // last refresh
  const lastRefresh = document.getElementById('last-refresh');
  if (lastRefresh) lastRefresh.textContent = '';

  // password change requirement
  if (user.precisa_trocar_senha && window.location.pathname !== '/login') {
    setTimeout(() => openChangePasswordModal(true), 400);
  }
}

function openChangePasswordModal(forced = false) {
  // Modal simples
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay show';
  overlay.innerHTML = `
    <div class="modal" style="max-width:420px">
      <div class="modal-header">
        <div class="modal-title">Alterar senha</div>
        <button class="modal-close">&times;</button>
      </div>
      <div class="modal-body">
        ${forced ? '<div class="modal-msg" style="color:var(--orange);font-size:13px;margin-bottom:12px">Você precisa trocar a senha padrão para continuar usando o sistema.</div>' : ''}
        <div class="form-field" style="margin-bottom:12px">
          <label>Senha atual</label>
          <input type="password" id="pw-atual" />
        </div>
        <div class="form-field" style="margin-bottom:12px">
          <label>Nova senha</label>
          <input type="password" id="pw-nova" />
        </div>
        <div class="form-field">
          <label>Confirmar nova senha</label>
          <input type="password" id="pw-confirma" />
        </div>
      </div>
      <div class="modal-footer">
        ${forced ? '' : '<button class="btn btn-ghost" data-cancel>Cancelar</button>'}
        <button class="btn btn-primary" data-save>Salvar</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  const close = () => overlay.remove();
  overlay.querySelector('.modal-close').addEventListener('click', () => { if (!forced) close(); });
  overlay.querySelector('[data-cancel]')?.addEventListener('click', () => close());

  overlay.querySelector('[data-save]').addEventListener('click', async () => {
    const atual = overlay.querySelector('#pw-atual').value;
    const nova = overlay.querySelector('#pw-nova').value;
    const confirma = overlay.querySelector('#pw-confirma').value;
    if (!nova || nova.length < 6) { toast('A nova senha deve ter pelo menos 6 caracteres', 'error'); return; }
    if (nova !== confirma) { toast('As senhas não conferem', 'error'); return; }
    try {
      await apiRequest('/auth/trocar-senha', {
        method: 'POST',
        body: JSON.stringify({ senha_atual: atual, nova_senha: nova }),
      });
      toast('Senha alterada com sucesso!', 'success');
      const user = getUser();
      if (user) { user.precisa_trocar_senha = false; localStorage.setItem('metafoco_user', JSON.stringify(user)); }
      close();
    } catch (e) {
      toast(e.message, 'error');
    }
  });
}