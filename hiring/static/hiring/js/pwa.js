// ============================================
// PWA HELPER - PRODUCTION READY
// ============================================

(function() {
    'use strict';
    
    // Check if we're in standalone mode (app installed)
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || 
                         window.navigator.standalone === true;
    
    console.log('PWA Mode:', isStandalone ? 'Standalone (Installed)' : 'Browser');
    
    // ============================================
    // 1. SERVICE WORKER REGISTRATION
    // ============================================
    
    if ('serviceWorker' in navigator) {
        // Use a timeout to avoid blocking the main thread
        setTimeout(() => {
            navigator.serviceWorker.register('/static/hiring/js/sw.js', {
                scope: '/'
            })
            .then(registration => {
                console.log('[PWA] Service Worker registered successfully:', registration);
                
                // Check for updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            // New version available
                            showUpdateNotification();
                        }
                    });
                });
                
                // Handle push notification permission
                if ('PushManager' in window) {
                    requestPushPermission(registration);
                }
            })
            .catch(error => {
                console.error('[PWA] Service Worker registration failed:', error);
            });
        }, 1000);
    } else {
        console.warn('[PWA] Service Worker not supported');
    }
    
    // ============================================
    // 2. INSTALL PROMPT HANDLING
    // ============================================
    
    let deferredPrompt = null;
    
    window.addEventListener('beforeinstallprompt', (e) => {
        // Prevent Chrome 67+ from auto-showing the prompt
        e.preventDefault();
        deferredPrompt = e;
        
        // Show install button
        showInstallBanner();
        console.log('[PWA] Install prompt available');
    });
    
    window.addEventListener('appinstalled', () => {
        console.log('[PWA] App installed successfully!');
        // Hide install banner
        hideInstallBanner();
        // Show success message
        showToast('App installed successfully!', 'success');
        deferredPrompt = null;
    });
    
    function showInstallBanner() {
        // Check if banner already exists
        if (document.getElementById('pwaInstallBanner')) {
            return;
        }
        
        // Only show if not in standalone mode
        if (isStandalone) {
            return;
        }
        
        const banner = document.createElement('div');
        banner.id = 'pwaInstallBanner';
        banner.className = 'pwa-install-banner';
        banner.innerHTML = `
            <div class="pwa-install-content">
                <div class="pwa-install-info">
                    <img src="/static/hiring/icons/icon-72x72.png" alt="Tolleya" width="48" height="48">
                    <div>
                        <strong>Install Tolleya</strong>
                        <div style="font-size:12px;color:#666;">Get the app experience</div>
                    </div>
                </div>
                <div class="pwa-install-actions">
                    <button class="btn btn-primary btn-sm" id="pwaInstallBtn">
                        <i class="fas fa-download me-1"></i>Install
                    </button>
                    <button class="btn btn-sm btn-close" id="pwaInstallDismiss"></button>
                </div>
            </div>
        `;
        
        document.body.appendChild(banner);
        
        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .pwa-install-banner {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: white;
                padding: 12px 16px;
                box-shadow: 0 -4px 12px rgba(0,0,0,0.1);
                z-index: 99999;
                border-top: 1px solid #eee;
                animation: slideUp 0.3s ease;
            }
            
            @keyframes slideUp {
                from { transform: translateY(100%); }
                to { transform: translateY(0); }
            }
            
            .pwa-install-content {
                max-width: 600px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
            }
            
            .pwa-install-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .pwa-install-actions {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .pwa-install-banner .btn-primary {
                background: #c62828;
                border-color: #c62828;
                padding: 6px 16px;
                border-radius: 20px;
                font-weight: 500;
            }
            
            .pwa-install-banner .btn-primary:hover {
                background: #b71c1c;
                border-color: #b71c1c;
            }
            
            .pwa-install-banner .btn-close {
                font-size: 14px;
                padding: 4px;
            }
            
            @media (min-width: 768px) {
                .pwa-install-banner {
                    padding: 16px 32px;
                }
            }
        `;
        document.head.appendChild(style);
        
        // Event listeners
        document.getElementById('pwaInstallBtn').addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const result = await deferredPrompt.userChoice;
                if (result.outcome === 'accepted') {
                    console.log('[PWA] User accepted install');
                } else {
                    console.log('[PWA] User dismissed install');
                }
                deferredPrompt = null;
            }
        });
        
        document.getElementById('pwaInstallDismiss').addEventListener('click', () => {
            hideInstallBanner();
            // Don't show again for a while
            localStorage.setItem('pwa_install_dismissed', Date.now().toString());
        });
    }
    
    function hideInstallBanner() {
        const banner = document.getElementById('pwaInstallBanner');
        if (banner) {
            banner.style.animation = 'slideDown 0.3s ease forwards';
            setTimeout(() => banner.remove(), 300);
        }
    }
    
    // ============================================
    // 3. UPDATE NOTIFICATION
    // ============================================
    
    function showUpdateNotification() {
        const toast = document.createElement('div');
        toast.className = 'pwa-update-toast';
        toast.innerHTML = `
            <div class="pwa-update-content">
                <i class="fas fa-sync-alt fa-spin"></i>
                <span style="flex:1;">New version available!</span>
                <button class="btn btn-primary btn-sm" onclick="updateApp()">Update</button>
                <button class="btn btn-sm btn-close" onclick="this.closest('.pwa-update-toast').remove()"></button>
            </div>
        `;
        
        const style = document.createElement('style');
        style.textContent = `
            .pwa-update-toast {
                position: fixed;
                bottom: 80px;
                left: 50%;
                transform: translateX(-50%);
                background: #1a1a1a;
                color: white;
                padding: 12px 20px;
                border-radius: 12px;
                z-index: 99999;
                max-width: 90%;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                animation: slideUp 0.3s ease;
            }
            
            .pwa-update-content {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .pwa-update-content .btn-primary {
                background: #c62828;
                border-color: #c62828;
                padding: 4px 16px;
                border-radius: 20px;
                font-weight: 500;
                font-size: 13px;
            }
            
            .pwa-update-content .btn-primary:hover {
                background: #b71c1c;
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(toast);
        
        // Auto hide after 30 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 30000);
    }
    
    // ============================================
    // 4. PUSH NOTIFICATIONS
    // ============================================
    
    function requestPushPermission(registration) {
        if (!('Notification' in window)) {
            console.log('[PWA] Notifications not supported');
            return;
        }
        
        if (Notification.permission === 'denied') {
            console.log('[PWA] Notifications denied');
            return;
        }
        
        if (Notification.permission === 'granted') {
            subscribeToPush(registration);
            return;
        }
        
        // Ask for permission
        document.addEventListener('click', () => {
            if (Notification.permission === 'default') {
                Notification.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        console.log('[PWA] Notification permission granted');
                        subscribeToPush(registration);
                    }
                });
            }
        }, { once: true });
    }
    
    function subscribeToPush(registration) {
        // Check if already subscribed
        registration.pushManager.getSubscription()
            .then(subscription => {
                if (subscription) {
                    console.log('[PWA] Already subscribed to push');
                    return;
                }
                
                // Subscribe
                return registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(
                        'YOUR_VAPID_PUBLIC_KEY' // Replace with your actual VAPID key
                    )
                });
            })
            .then(subscription => {
                if (subscription) {
                    console.log('[PWA] Subscribed to push:', subscription);
                    // Send subscription to server
                    sendSubscriptionToServer(subscription);
                }
            })
            .catch(error => {
                console.error('[PWA] Push subscription error:', error);
            });
    }
    
    function sendSubscriptionToServer(subscription) {
        // Get CSRF token
        function getCSRFToken() {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if (name === 'csrftoken') return decodeURIComponent(value);
            }
            return '';
        }
        
        fetch('/api/notifications/subscribe/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ subscription })
        })
        .then(response => response.json())
        .then(data => {
            console.log('[PWA] Subscription sent to server:', data);
        })
        .catch(error => {
            console.error('[PWA] Failed to send subscription:', error);
        });
    }
    
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
    
    // ============================================
    // 5. GLOBAL FUNCTIONS
    // ============================================
    
    window.updateApp = function() {
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
                type: 'SKIP_WAITING'
            });
        }
        // Force reload
        window.location.reload(true);
    };
    
    window.showToast = function(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `pwa-toast pwa-toast-${type}`;
        toast.innerHTML = `
            <div class="pwa-toast-content">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        
        const style = document.createElement('style');
        style.textContent = `
            .pwa-toast {
                position: fixed;
                bottom: 100px;
                left: 50%;
                transform: translateX(-50%);
                background: #1a1a1a;
                color: white;
                padding: 12px 20px;
                border-radius: 12px;
                z-index: 99999;
                max-width: 90%;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                animation: slideUp 0.3s ease;
            }
            
            .pwa-toast-content {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .pwa-toast-success .pwa-toast-content i {
                color: #4caf50;
            }
            
            .pwa-toast-info .pwa-toast-content i {
                color: #2196f3;
            }
            
            @keyframes slideUp {
                from { transform: translateX(-50%) translateY(100%); opacity: 0; }
                to { transform: translateX(-50%) translateY(0); opacity: 1; }
            }
            
            @keyframes slideDown {
                from { transform: translateX(-50%) translateY(0); opacity: 1; }
                to { transform: translateX(-50%) translateY(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(toast);
        
        // Auto hide after 4 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'slideDown 0.3s ease forwards';
                setTimeout(() => toast.remove(), 300);
            }
        }, 4000);
    };
    
    console.log('[PWA] PWA Helper initialized successfully');
})();