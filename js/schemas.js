/* Schémas des fiches de soins : carrousel manuel (glisser, flèches, points). L'animation d'une étape se joue quand on y arrive. */
(function(){
  function init(w){
    var t=w.querySelector('.sch-track'),s=[].slice.call(t.children),d=[].slice.call(w.querySelectorAll('.sch-dot')),
        p=w.querySelector('.sch-prev'),n=w.querySelector('.sch-next'),cur=-1,tm;
    function set(i,force){
      if(i===cur&&!force)return;cur=i;
      s.forEach(function(e,k){e.classList.remove('on');if(k===i){void e.offsetWidth;e.classList.add('on');}});
      d.forEach(function(e,k){e.classList.toggle('on',k===i);e.setAttribute('aria-current',k===i?'step':'false');});
      p.disabled=i===0;n.disabled=i===s.length-1;
    }
    function go(i){i=Math.max(0,Math.min(s.length-1,i));t.scrollTo({left:i*t.clientWidth,behavior:'smooth'});set(i);}
    t.addEventListener('scroll',function(){clearTimeout(tm);tm=setTimeout(function(){set(Math.round(t.scrollLeft/t.clientWidth));},90);},{passive:true});
    p.addEventListener('click',function(){go(cur-1);});
    n.addEventListener('click',function(){go(cur+1);});
    d.forEach(function(e,k){e.addEventListener('click',function(){go(k);});});
    t.addEventListener('keydown',function(e){if(e.key==='ArrowRight'){e.preventDefault();go(cur+1);}if(e.key==='ArrowLeft'){e.preventDefault();go(cur-1);}});
    w._replay=function(){set(Math.max(cur,0),true);};
    [].slice.call(w.querySelectorAll('[data-view]')).forEach(function(b,k,all){b.addEventListener('click',function(){
      w.setAttribute('data-v',b.getAttribute('data-view'));all.forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});set(Math.max(cur,0),true);});});
    set(0);
  }
  document.querySelectorAll('[data-sch]').forEach(init);
  document.addEventListener('toggle',function(e){if(e.target.open)e.target.querySelectorAll('[data-sch]').forEach(function(w){w._replay&&w._replay();});},true);
})();
