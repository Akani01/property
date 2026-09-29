/* OppoGlobe cross-page alert sound helper.
 * Include this from the shared OppoGlobe base template if you want the same
 * alert sound on every open page, not only the car-wash map.
 */
(function(){
  'use strict';
  if (window.__OPPOGLOBE_LIVE_ALERTS__) return;
  window.__OPPOGLOBE_LIVE_ALERTS__ = true;

  let ready = false;
  let known = new Set();
  let timer = null;

  function rows(data){
    if (Array.isArray(data)) return data;
    for (const key of ['alerts','results','data','notifications']) {
      if (Array.isArray(data && data[key])) return data[key];
    }
    return [];
  }
  function idOf(a){ return a && (a.id ?? a.alert_id ?? a.pk); }
  function getAudio(){
    let audio = document.getElementById('oppoglobe-global-notification-audio');
    if (!audio) {
      audio = document.createElement('audio');
      audio.id = 'oppoglobe-global-notification-audio';
      audio.preload = 'auto';
      audio.src = '/static/hiring/audio/notification.mp3';
      audio.style.display = 'none';
      document.body.appendChild(audio);
    }
    return audio;
  }
  function play(){
    try {
      const a = getAudio();
      a.currentTime = 0;
      const p = a.play();
      if (p) p.catch(()=>{});
    } catch (_) {}
  }
  async function poll(){
    if (!navigator.onLine) return;
    try {
      const r = await fetch('/api/alerts/?_live=' + Date.now(), {
        credentials:'same-origin', cache:'no-store',
        headers:{'Accept':'application/json','Cache-Control':'no-cache'}
      });
      if (!r.ok) return;
      const data = await r.json();
      const list = rows(data);
      const ids = list.map(idOf).filter(v=>v!=null).map(String);
      if (!ready) { known = new Set(ids); ready = true; return; }
      const fresh = list.filter(a=>{ const id=idOf(a); return id!=null && !known.has(String(id)); });
      known = new Set(ids);
      if (fresh.length) play();
    } catch (_) {}
  }
  function start(){
    poll();
    if (timer) clearInterval(timer);
    timer = setInterval(poll,15000);
  }
  ['pointerdown','touchstart','keydown'].forEach(evt=>document.addEventListener(evt,()=>{
    const a=getAudio();
    try { const p=a.play(); if(p)p.then(()=>{a.pause();a.currentTime=0;}).catch(()=>{}); } catch(_) {}
  },{passive:true}));
  document.addEventListener('visibilitychange',()=>{ if(document.visibilityState==='visible') poll(); });
  window.addEventListener('focus',poll);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',start);
  else start();
})();
