/* Shared left sidebar: new chat, daily-limit status, previous chats, account links, admin links, sign out.
   Used by /, /admin and /password. Pages that are not the chat navigate to "/" when a chat is picked. */
window.Sidebar = (() => {
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  let opts = {}, me = null;
  const store = {
    get: () => { try { return localStorage.getItem('sid') } catch (e) { return null } },
    set: v => { try { v ? localStorage.setItem('sid', v) : localStorage.removeItem('sid') } catch (e) {} }
  };
  const currentSid = () => opts.getSid ? opts.getSid() : store.get();
  const close = () => document.body.classList.remove('nav');

  function ago(ts) {
    const m = Math.round((Date.now() / 1000 - ts) / 60);
    if (m < 1) return 'just now';
    if (m < 60) return m + ' min ago';
    const h = Math.round(m / 60);
    if (h < 24) return h + ' h ago';
    const d = Math.round(h / 24);
    return d === 1 ? 'yesterday' : d + ' days ago';
  }

  function template() {
    const cur = p => opts.active === p ? ' class="cur"' : '';
    return `<button id="new">+ New chat</button>
<div class="lim" id="lim"></div><h3>Previous chats</h3><div id="sl"></div>
<div class="acct"><div id="who" class="who"></div>
<div id="adm" class="admlinks"><h3>Admin</h3>
<a href="/admin#create-user">＋ Create user</a><a href="/admin#create-role">＋ Create role</a>
<a href="/admin"${cur('admin')}>Users, roles &amp; usage</a></div>
<a href="/password"${cur('password')}>Change password</a><button id="out">Sign out</button></div>`;
  }

  function setMe(m) {
    me = m;
    $('who').textContent = m ? m.email + ' · ' + m.role : '';
    $('adm').style.display = m && m.role === 'admin' ? 'flex' : 'none';
    const L = $('lim');
    if (!m) { L.innerHTML = ''; return; }
    const u = m.used_today, l = m.limit, pct = l ? Math.min(100, 100 * u / l) : 0;
    L.className = 'lim' + (l && u >= l ? ' full' : (l && pct >= 80 ? ' warn' : ''));
    L.innerHTML = l
      ? `<b>${u} of ${l}</b> messages used today<div class="bar"><i style="width:${pct}%"></i></div><small>${u >= l ? 'Limit reached. Resets at midnight.' : (l - u) + ' left today · resets at midnight'}</small>`
      : `<b>${u}</b> messages today<div class="bar"><i style="width:0"></i></div><small>No daily limit</small>`;
  }

  async function refreshMe() {
    const r = await fetch('/me');
    if (r.status === 401) { clear(); if (opts.onSignedOut) opts.onSignedOut(); else location.href = '/'; return null; }
    setMe(await r.json());
    return me;
  }

  async function refresh() {
    const box = $('sl'), cur = currentSid();
    try {
      const r = await fetch('/sessions');
      if (!r.ok) throw 0;
      const list = await r.json();
      box.innerHTML = list.length ? '' : '<div class="none">No previous chats yet.</div>';
      list.forEach(x => {
        const d = document.createElement('div');
        d.className = 'si' + (x.sid === cur ? ' on' : '');
        d.title = x.title;
        d.innerHTML = `<div><div class="t">${esc(x.title)}</div><div class="d">${ago(x.updated)} · ${x.messages / 2 | 0} Q</div></div><button title="Delete chat" aria-label="Delete chat">×</button>`;
        d.onclick = () => select(x.sid);
        d.querySelector('button').onclick = async e => {
          e.stopPropagation();
          if (!confirm('Delete this chat?')) return;
          await fetch('/sessions/' + x.sid, {method: 'DELETE'});
          if (x.sid === currentSid()) { if (opts.onDeleteCurrent) opts.onDeleteCurrent(); else store.set(null); }
          refresh();
        };
        box.append(d);
      });
    } catch (e) { box.innerHTML = ''; }
  }

  function select(sid) {
    close();
    if (opts.onSelect) { if (sid !== currentSid()) opts.onSelect(sid); return; }
    store.set(sid); location.href = '/';
  }

  function newChat() {
    close();
    if (opts.onNew) opts.onNew(); else { store.set(null); location.href = '/'; }
  }

  async function signOut() {
    await fetch('/logout', {method: 'POST'});
    if (opts.onSignOut) opts.onSignOut(); else { store.set(null); location.href = '/'; }
  }

  function clear() { if ($('sl')) $('sl').innerHTML = ''; if ($('lim')) $('lim').innerHTML = ''; if ($('who')) $('who').textContent = ''; }

  /* opts: active, getSid, onSelect, onNew, onDeleteCurrent, onSignOut, onSignedOut, skipLoad */
  async function init(o) {
    opts = o || {};
    const side = $('side');
    side.className = 'side';
    side.innerHTML = template();
    $('new').onclick = newChat;
    $('out').onclick = signOut;
    let menu = $('menu');
    if (!menu) { menu = document.createElement('button'); menu.id = 'menu'; menu.className = 'fab'; menu.setAttribute('aria-label', 'Menu'); menu.textContent = '☰'; document.body.append(menu); }
    menu.onclick = () => document.body.classList.toggle('nav');
    if (!opts.skipLoad) { if (await refreshMe()) refresh(); }
  }

  return {init, setMe, refresh, refreshMe, clear};
})();
