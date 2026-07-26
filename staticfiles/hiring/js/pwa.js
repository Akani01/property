// ============================================================
// PWA - Progressive Web App JavaScript
// ============================================================

(function() {
    'use strict';

    // ===== PWA INSTALL PROMPT =====
    let deferredPrompt;
    let isPwaInstalled = false;

    // Check if app is installed (standalone mode)
    if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone) {
        isPwaInstalled = true;
        document.documentElement.classList.add('pwa-installed');
    }

    // Listen for install prompt
    window.addEventListener('beforeinstallprompt', function(e) {
        e.preventDefault();
        deferredPrompt = e;
        showInstallBanner();
    });

    // App installed event
    window.addEventListener('appinstalled', function() {
        isPwaInstalled = true;
        document.documentElement.classList.add('pwa-installed');
        hideInstallBanner();
        console.log('✅ PWA installed successfully!');
    });

    // ===== INSTALL BANNER =====
    function showInstallBanner() {
        // Check if banner already exists or if installed
        if (document.getElementById('pwaInstallBanner') || isPwaInstalled) return;
        
        const banner = document.createElement('div');
        banner.id = 'pwaInstallBanner';
        banner.style.cssText = `
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            padding: 16px 20px;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.15);
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            border-top: 3px solid #c62828;
        `;
        
        banner.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 200px;">
                <img src="/static/hiring/icons/icon-72x72.png" alt="Tolleya" style="width: 44px; height: 44px; border-radius: 8px;">
                <div>
                    <div style="font-weight: 600; font-size: 16px; color: #333;">Install Tolleya App</div>
                    <div style="font-size: 13px; color: #666;">Get faster access and offline support</div>
                </div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button id="pwaInstallBtn" style="
                    background: #c62828;
                    color: white;
                    border: none;
                    padding: 10px 24px;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background 0.3s;
                ">Install</button>
                <button id="pwaCloseBtn" style="
                    background: #f0f0f0;
                    color: #666;
                    border: none;
                    padding: 10px 16px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                ">✕</button>
            </div>
        `;
        
        document.body.appendChild(banner);
        
        // Install button
        document.getElementById('pwaInstallBtn').addEventListener('click', async function() {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const result = await deferredPrompt.userChoice;
                if (result.outcome === 'accepted') {
                    console.log('✅ User accepted install');
                    hideInstallBanner();
                } else {
                    console.log('❌ User dismissed install');
                }
                deferredPrompt = null;
            }
        });
        
        // Close button
        document.getElementById('pwaCloseBtn').addEventListener('click', function() {
            hideInstallBanner();
        });
    }

    function hideInstallBanner() {
        const banner = document.getElementById('pwaInstallBanner');
        if (banner) {
            banner.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
            banner.style.transform = 'translateY(100%)';
            banner.style.opacity = '0';
            setTimeout(() => banner.remove(), 400);
        }
    }

    // ===== NETWORK STATUS =====
    function updateNetworkStatus() {
        const isOnline = navigator.onLine;
        document.documentElement.classList.toggle('offline', !isOnline);
        document.documentElement.classList.toggle('online', isOnline);
        
        // Show/hide offline banner
        let offlineBanner = document.getElementById('pwaOfflineBanner');
        if (!isOnline) {
            if (!offlineBanner) {
                offlineBanner = document.createElement('div');
                offlineBanner.id = 'pwaOfflineBanner';
                offlineBanner.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    background: #dc3545;
                    color: white;
                    padding: 8px 16px;
                    text-align: center;
                    font-size: 14px;
                    font-weight: 500;
                    z-index: 99999;
                `;
                offlineBanner.innerHTML = '📡 You are offline. Some features may not be available.';
                document.body.prepend(offlineBanner);
            }
        } else {
            if (offlineBanner) {
                offlineBanner.style.transition = 'opacity 0.3s ease';
                offlineBanner.style.opacity = '0';
                setTimeout(() => offlineBanner.remove(), 400);
            }
        }
    }

    // Network event listeners
    window.addEventListener('online', updateNetworkStatus);
    window.addEventListener('offline', updateNetworkStatus);
    updateNetworkStatus();

    // ===== SERVICE WORKER REGISTRATION =====
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register('/serviceworker.js')
                .then(function(registration) {
                    console.log('✅ Service Worker registered successfully:', registration);
                })
                .catch(function(error) {
                    console.log('❌ Service Worker registration failed:', error);
                });
        });
    }

    // ===== NOTIFICATION PERMISSION =====
    function requestNotificationPermission() {
        if (!('Notification' in window)) {
            console.log('Notifications not supported');
            return;
        }

        if (Notification.permission === 'granted') {
            console.log('Notification permission already granted');
            return;
        }

        if (Notification.permission === 'denied') {
            console.log('Notification permission denied');
            return;
        }

        // Show permission request on user interaction
        const permissionBtn = document.getElementById('requestNotificationPermission');
        if (permissionBtn) {
            permissionBtn.addEventListener('click', function() {
                Notification.requestPermission().then(function(permission) {
                    if (permission === 'granted') {
                        console.log('✅ Notification permission granted');
                        // Show a test notification
                        showNotification('Notifications Enabled', 'You will now receive notifications from Tolleya');
                    }
                });
            });
        }
    }

    function showNotification(title, body) {
        if (!('Notification' in window) || Notification.permission !== 'granted') return;
        
        try {
            const notification = new Notification(title, {
                body: body,
                icon: '/static/hiring/icons/icon-192x192.png',
                badge: '/static/hiring/icons/icon-72x72.png',
                vibrate: [200, 100, 200],
                silent: false
            });
            
            notification.onclick = function() {
                window.focus();
                notification.close();
            };
        } catch (e) {
            console.log('Notification error:', e);
        }
    }

    // ===== SPLASH SCREEN =====
    function hideSplashScreen() {
        const splash = document.getElementById('pwaSplash');
        if (splash) {
            splash.classList.add('hidden');
            setTimeout(function() {
                splash.style.display = 'none';
            }, 600);
        }
    }

    // ===== EXPOSE FUNCTIONS GLOBALLY =====
    window.TolleyaPWA = {
        showInstallBanner: showInstallBanner,
        hideInstallBanner: hideInstallBanner,
        requestNotificationPermission: requestNotificationPermission,
        showNotification: showNotification,
        hideSplashScreen: hideSplashScreen,
        isInstalled: isPwaInstalled
    };

    // ===== AUTO-HIDE SPLASH =====
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(hideSplashScreen, 800);
    });

    window.addEventListener('load', function() {
        setTimeout(hideSplashScreen, 1000);
    });

    console.log('✅ PWA JavaScript loaded');

})();