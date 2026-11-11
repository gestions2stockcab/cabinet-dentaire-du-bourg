/* Mesure des clics vers Doctolib et sur le téléphone (événements GoatCounter, sans cookie). */
(function(){
  function where(a){
    if(a.closest('header'))return 'en-tete';
    if(a.closest('footer'))return 'pied-de-page';
    if(a.closest('.bot'))return 'assistant';
    var s=a.closest('section[id],div[id^="view-"],.hero,.band,aside');
    if(s&&s.classList.contains('hero'))return 'haut-de-page';
    if(s&&s.classList.contains('band'))return 'grande-photo';
    if(s&&s.tagName==='ASIDE')return 'encart-page';
    if(s&&s.id)return s.id.replace(/^view-/,'');
    return 'autre';
  }
  function page(){var p=location.pathname.replace(/\/$/,'')||'/accueil';return p.replace(/^\//,'');}
  document.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('a[href]');if(!a)return;
    var h=a.getAttribute('href'),kind=null;
    if(h.indexOf('doctolib.fr')>-1)kind='rdv-doctolib';else if(h.indexOf('tel:')===0)kind='appel-telephone';
    if(!kind||!window.goatcounter||!window.goatcounter.count)return;
    window.goatcounter.count({path:kind==='rdv-doctolib'?'Clic Doctolib':'Clic téléphone',title:kind==='rdv-doctolib'?'Clic vers Doctolib':'Clic sur le numéro',event:true});
  },true);
})();
