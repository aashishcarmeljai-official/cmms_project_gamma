// Service Worker for CMMS Application
// Provides offline support and caching for media files

const CACHE_NAME = 'cmms-v1';
const STATIC_CACHE = 'cmms-static-v1';
const MEDIA_CACHE = 'cmms-media-v1';

// Files to cache for offline functionality
const STATIC_FILES = [
    '/',
    '/static/css/style.css',
    '/static/js/script.js',
    '/static/js/media-upload.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => {
                console.log('Service Worker installed');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('Service Worker installation failed:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== STATIC_CACHE && cacheName !== MEDIA_CACHE) {
                            console.log('Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('Service Worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - handle requests
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Handle API requests
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(handleApiRequest(request));
        return;
    }

    // Handle media file requests
    if (url.pathname.startsWith('/static/uploads/')) {
        event.respondWith(handleMediaRequest(request));
        return;
    }

    // Handle static file requests
    if (url.pathname.startsWith('/static/') || url.pathname === '/') {
        event.respondWith(handleStaticRequest(request));
        return;
    }

    // Handle other requests with network-first strategy
    event.respondWith(handleOtherRequest(request));
});

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Network failed for API request, trying cache:', request.url);
        
        // Fallback to cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline response for API requests
        return new Response(JSON.stringify({
            error: 'Offline',
            message: 'You are offline and this data is not cached.'
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Handle media requests with cache-first strategy
async function handleMediaRequest(request) {
    const cache = await caches.open(MEDIA_CACHE);
    
    // Check cache first
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        // Try network
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Network failed for media request:', request.url);
        
        // Return placeholder for missing media
        return new Response('Media not available offline', {
            status: 404,
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

// Handle static file requests with cache-first strategy
async function handleStaticRequest(request) {
    const cache = await caches.open(STATIC_CACHE);
    
    // Check cache first
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        // Try network
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Network failed for static request:', request.url);
        
        // Return offline page for HTML requests
        if (request.headers.get('accept').includes('text/html')) {
            return cache.match('/');
        }
        
        return new Response('Resource not available offline', {
            status: 404,
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

// Handle other requests with network-first strategy
async function handleOtherRequest(request) {
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Network failed, trying cache:', request.url);
        
        // Fallback to cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline response
        return new Response('Page not available offline', {
            status: 503,
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

// Background sync for offline uploads
self.addEventListener('sync', (event) => {
    if (event.tag === 'background-sync') {
        console.log('Background sync triggered');
        event.waitUntil(syncOfflineData());
    }
});

// Sync offline data when connection is restored
async function syncOfflineData() {
    try {
        // Get all clients
        const clients = await self.clients.matchAll();
        
        // Notify clients to sync their offline data
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_OFFLINE_DATA'
            });
        });
        
        console.log('Background sync completed');
    } catch (error) {
        console.error('Background sync failed:', error);
    }
}

// Handle push notifications (for future use)
self.addEventListener('push', (event) => {
    if (event.data) {
        const data = event.data.json();
        
        const options = {
            body: data.body,
            icon: '/static/img/icon-192x192.png',
            badge: '/static/img/badge-72x72.png',
            vibrate: [100, 50, 100],
            data: {
                dateOfArrival: Date.now(),
                primaryKey: 1
            },
            actions: [
                {
                    action: 'explore',
                    title: 'View Work Order',
                    icon: '/static/img/checkmark.png'
                },
                {
                    action: 'close',
                    title: 'Close',
                    icon: '/static/img/xmark.png'
                }
            ]
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    if (event.action === 'explore') {
        // Open the work order
        event.waitUntil(
            clients.openWindow('/work-orders')
        );
    }
});

// Handle messages from the main thread
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'CACHE_MEDIA') {
        event.waitUntil(cacheMedia(event.data.url));
    }
});

// Cache media file
async function cacheMedia(url) {
    try {
        const cache = await caches.open(MEDIA_CACHE);
        const response = await fetch(url);
        
        if (response.ok) {
            await cache.put(url, response.clone());
            console.log('Media cached:', url);
        }
    } catch (error) {
        console.error('Failed to cache media:', url, error);
    }
} 