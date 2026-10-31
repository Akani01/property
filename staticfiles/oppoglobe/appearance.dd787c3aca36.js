(function(){
  const KEY='oppoglobe.theme';
  const allowed=['light','dark','system'];
  let value;
  try {value=localStorage.getItem(KEY)||localStorage.getItem('tolleya_theme')||'light';}catch(e){value='light';}
  if(!allowed.includes(value))value='light';
  const media=window.matchMedia('(prefers-color-scheme: dark)');
  function apply(){const resolved=value==='system'?(media.matches?'dark':'light'):value;document.documentElement.dataset.ogTheme=resolved;document.documentElement.style.colorScheme=resolved;document.querySelectorAll('[data-og-theme]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.ogTheme===value)));}
  apply();
  if(media.addEventListener)media.addEventListener('change',apply);
  document.addEventListener('click',function(e){const el=e.target.closest('[data-og-theme]');if(!el)return;value=el.dataset.ogTheme;if(!allowed.includes(value))return;try{localStorage.setItem(KEY,value);localStorage.setItem('tolleya_theme',value);}catch(e){}apply();});
  document.addEventListener('DOMContentLoaded',apply);
  window.OppoGlobeAppearance={get:()=>value,set:function(next){if(allowed.includes(next)){value=next;try{localStorage.setItem(KEY,next)}catch(e){}apply();}}};
})();
