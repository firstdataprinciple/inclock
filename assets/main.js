(function(){
  var b=document.querySelector('.menu-btn'),n=document.querySelector('.nav');
  if(b&&n)b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o)});
  var y=document.getElementById('yr');if(y)y.textContent=new Date().getFullYear();
})();
