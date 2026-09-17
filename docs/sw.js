const CACHE='mercadona-v1';
const SHELL=['./','./index.html','./icon-192.png','./manifest.json'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(u.hostname.endsWith('supabase.co')) return;      // datos: siempre a red
  e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
});
