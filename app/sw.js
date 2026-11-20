/* ExamBoost AI Service Worker
 * 策略：导航与 HTML 走网络优先（改了立刻生效，断网才回落缓存）；
 *       静态资源走缓存优先 + 后台更新；/api/ 一律不缓存，保证数据实时。
 */
const CACHE = 'examboost-v3';
const CORE = [
  '/',
  '/index.html',
  '/manifest.json',
  '/static/style.css',
  '/static/app.js',
  '/static/icon.svg',
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);

  if (req.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;
  // API 永不缓存
  if (url.pathname.startsWith('/api/')) return;

  // 页面导航：网络优先，失败回落缓存（离线可打开）
  if (req.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('.html')) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put('/index.html', copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match('/index.html').then((r) => r || caches.match('/')))
    );
    return;
  }

  // 静态资源：缓存优先 + 后台刷新
  e.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
