(function () {
  'use strict';
  const KEY = 'oppoglobe.theme';
  const allowed = ['light', 'dark', 'system'];
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  function choice() { try { let v = localStorage.getItem(KEY); if (!allowed.includes(v)) { const legacy=localStorage.getItem('tolleya_theme'); v=allowed.includes(legacy)?legacy:'system'; localStorage.setItem(KEY,v); } return v; } catch (_) { return 'system'; } }
  function apply() {
    const c = choice();
    const effective = c === 'system' ? (media.matches ? 'dark' : 'light') : c;
    document.documentElement.dataset.ogTheme = effective; document.documentElement.dataset.theme = effective;
    document.documentElement.style.colorScheme = effective;
    document.querySelectorAll('[data-og-theme-choice]').forEach(el => { el.checked = el.value === c; });
    document.querySelectorAll('[data-og-theme-current]').forEach(el => { el.textContent = c.charAt(0).toUpperCase() + c.slice(1); });
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = effective === 'dark' ? '#101b18' : '#1f6f5c';
  }
  function csrf() { const found = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/); return found ? decodeURIComponent(found[1]) : ''; }
  let dirty = false;
  function syncSave(value) { fetch('/api/preferences/appearance/', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':csrf()}, body:JSON.stringify({theme:value})}).catch(()=>{}); }
  window.OppoGlobeTheme = { set(value) { if (!allowed.includes(value)) return; dirty = true; try { localStorage.setItem(KEY, value); } catch (_) {} apply(); syncSave(value); }, get: choice, apply };
  // Restore account preference after the local theme is applied immediately.
  fetch('/api/preferences/appearance/', {credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(data=>{if (!dirty && data && allowed.includes(data.theme)) {try {localStorage.setItem(KEY,data.theme);} catch (_) {} apply();}}).catch(()=>{});
  document.addEventListener('change', e => { if (e.target.matches('[data-og-theme-choice]')) window.OppoGlobeTheme.set(e.target.value); });
  if (media.addEventListener) media.addEventListener('change', apply); else if (media.addListener) media.addListener(apply);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply); else apply();
  apply();
})();
