// ============================================================
// TOLOLEYA PWA - Complete Client-Side Setup
// ============================================================

class TolleyaPWA {
    constructor() {
        this.deferredPrompt = null;
        this.isInstalled = false;
        this.installPromptShown = false;
        this.swRegistration = null;
        
        // Check if already in standalone mode
        this.isStandalone = window.matchMedia('(display-mode: standalone)').matches;
        
        if (this.isStandalone) {
            this.isInstalled = true;
            console.log('📱 Tolleya is running as installed app');
        }
        
        this.init();
    }
    
    async init() {
        // 1. Register service worker
        await this.registerServiceWorker();
        
        // 2. Setup install prompt
        this.setupInstallPrompt();
        
        // 3. Setup notifications
        this.setupNotifications();
        
        // 4. Check for updates
        this.checkForUpdates();
        
        // 5. Setup online/offline handlers
        this.setupConnectivityHandlers();
    }
    
    // ============================================================
    // SERVICE WORKER REGISTRATION
    // ============================================================
    
    async registerServiceWorker() {
        if (!('serviceWorker' in navigator)) {
            console.warn('⚠️ Service Workers not supported');
            return;
        }
        
        try {
            // Register the service worker
            this.swRegistration = await navigator.serviceWorker.register('/sw.js', {
                scope: '/'
            });
            
            console.log('✅ Service Worker registered:', this.swRegistration);
            
            // Listen for controller change (new SW takes over)
            navigator.serviceWorker.addEventListener('controllerchange', () => {
                console.log('🔄 Service Worker controller changed');
                // Reload to get new version
                this.showUpdateNotification();
            });
            
            // Check for updates periodically
            setInterval(() => this.checkForUpdates(), 60000); // Check every minute
            
            return this.swRegistration;
        } catch (error) {
            console.error('❌ Service Worker registration failed:', error);
        }
    }
    
    async checkForUpdates() {
        if (!this.swRegistration) return;
        
        try {
            await this.swRegistration.update();
            console.log('🔄 Checked for SW updates');
        } catch (error) {
            console.error('Failed to check for updates:', error);
        }
    }
    
    // ============================================================
    // INSTALL PROMPT
    // ============================================================
    
    setupInstallPrompt() {
        // Listen for the beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('📱 Install prompt available');
            e.preventDefault();
            this.deferredPrompt = e;
            this.installPromptShown = true;
            
            // Show the install button
            this.showInstallButton();
            
            // Track with analytics if available
            if (typeof gtag !== 'undefined') {
                gtag('event', 'pwa_prompt_shown', {
                    'event_category': 'PWA',
                    'event_label': 'Install Prompt'
                });
            }
        });
        
        // Listen for successful installation
        window.addEventListener('appinstalled', () => {
            console.log('🎉 Tolleya installed successfully!');
            this.isInstalled = true;
            this.hideInstallButton();
            
            // Track installation
            if (typeof gtag !== 'undefined') {
                gtag('event', 'pwa_installed', {
                    'event_category': 'PWA',
                    'event_label': 'App Installed'
                });
            }
            
            // Send to server
            this.sendInstallEvent('installed');
            
            // Show success message
            this.showToast('🎉 Tolleya installed successfully!', 'success');
        });
        
        // Listen for display mode changes
        window.addEventListener('displaymodechange', (e) => {
            console.log('Display mode changed:', e);
            this.isStandalone = window.matchMedia('(display-mode: standalone)').matches;
            if (this.isStandalone) {
                this.isInstalled = true;
                this.hideInstallButton();
            }
        });
    }
    
    showInstallButton() {
        // Check if button already exists
        if (document.getElementById('tolleyaInstallBtn')) return;
        
        const btn = document.createElement('button');
        btn.id = 'tolleyaInstallBtn';
        btn.innerHTML = `
            <i class="fas fa-download" style="margin-right: 10px;"></i>
            Install Tolleya App
        `;
        btn.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 10000;
            background: linear-gradient(135deg, #c62828, #ff589e);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 50px;
            font-weight: 600;
            font-size: 16px;
            box-shadow: 0 8px 30px rgba(198, 40, 40, 0.4);
            cursor: pointer;
            animation: slideUp 0.5s ease;
            display: flex;
            align-items: center;
            gap: 10px;
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease;
            white-space: nowrap;
        `;
        
        // Hover effects
        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'translateX(-50%) scale(1.05)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'translateX(-50%) scale(1)';
        });
        
        // Click handler
        btn.addEventListener('click', this.handleInstallClick.bind(this));
        
        document.body.appendChild(btn);
        
        // Auto-hide after 15 seconds if not clicked
        setTimeout(() => {
            if (btn && btn.style.display !== 'none') {
                btn.style.animation = 'slideDown 0.5s ease forwards';
                setTimeout(() => {
                    if (btn.parentNode) btn.remove();
                }, 500);
            }
        }, 15000);
    }
    
    hideInstallButton() {
        const btn = document.getElementById('tolleyaInstallBtn');
        if (btn) {
            btn.style.animation = 'slideDown 0.3s ease forwards';
            setTimeout(() => {
                if (btn.parentNode) btn.remove();
            }, 300);
        }
    }
    
    async handleInstallClick() {
        if (!this.deferredPrompt) {
            this.showToast('Install prompt not available. Try opening in Chrome.', 'warning');
            return;
        }
        
        try {
            // Show the install prompt
            this.deferredPrompt.prompt();
            
            // Wait for user choice
            const result = await this.deferredPrompt.userChoice;
            
            if (result.outcome === 'accepted') {
                console.log('✅ User installed the app');
                this.isInstalled = true;
                this.hideInstallButton();
                
                // Track
                if (typeof gtag !== 'undefined') {
                    gtag('event', 'pwa_install_accepted', {
                        'event_category': 'PWA'
                    });
                }
                
                this.sendInstallEvent('accepted');
                this.showToast('🎉 Thank you for installing Tolleya!', 'success');
            } else {
                console.log('❌ User dismissed install');
                this.showToast('Installation canceled', 'info');
                
                if (typeof gtag !== 'undefined') {
                    gtag('event', 'pwa_install_dismissed', {
                        'event_category': 'PWA'
                    });
                }
            }
            
            this.deferredPrompt = null;
        } catch (error) {
            console.error('Install error:', error);
            this.showToast('Error installing app', 'error');
        }
    }
    
    // ============================================================
    // NOTIFICATIONS
    // ============================================================
    
    setupNotifications() {
        if (!('Notification' in window)) {
            console.log('Notifications not supported');
            return;
        }
        
        // Check if user is logged in (your Django template variable)
        const isLoggedIn = document.querySelector('[data-user-logged-in]')?.dataset.userLoggedIn === 'true';
        
        if (!isLoggedIn) return;
        
        // Check permission
        if (Notification.permission === 'granted') {
            console.log('✅ Notification permission granted');
            this.subscribeToPush();
        } else if (Notification.permission === 'default') {
            // Add click handler to notification bell
            const bell = document.querySelector('.notification-wrapper a');
            if (bell) {
                bell.addEventListener('click', (e) => {
                    if (Notification.permission === 'default') {
                        e.preventDefault();
                        this.askNotificationPermission();
                    }
                });
            }
        }
    }
    
    async askNotificationPermission() {
        if (!('Notification' in window)) {
            this.showToast('Notifications not supported', 'warning');
            return;
        }
        
        if (Notification.permission === 'granted') {
            this.showToast('Notifications already enabled', 'success');
            return;
        }
        
        if (Notification.permission === 'denied') {
            this.showToast('Notifications blocked. Please enable in browser settings.', 'warning');
            return;
        }
        
        try {
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                console.log('✅ Notification permission granted');
                this.showToast('Notifications enabled! 🔔', 'success');
                await this.subscribeToPush();
            } else {
                console.log('❌ Notification permission denied');
                this.showToast('Notifications disabled', 'warning');
            }
        } catch (error) {
            console.error('Notification permission error:', error);
        }
    }
    
    // ============================================================
    // FIXED: PUSH SUBSCRIPTION WITH RAW VAPID KEY
    // ============================================================
    
    async subscribeToPush() {
        try {
            // Get the service worker registration
            const registration = await navigator.serviceWorker.ready;
            
            // ✅ RAW VAPID PUBLIC KEY (generated from vapid_raw_keys.txt)
            // This is the correct format for the Push API
            const VAPID_PUBLIC_KEY = 'BAt7mPbnnynQNSCQalbpByolKwY_0LS3JyiQ0VSWpDDC2wFkyVJBsEMmra-beaYx-cUMTXgeQAtrzIYDYnnp7tk';
            
            // Subscribe to push with the raw VAPID key
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
            });
            
            console.log('✅ Push subscription successful:', subscription);
            
            // Send subscription to server
            await this.sendSubscriptionToServer(subscription);
            
            this.showToast('🔔 Push notifications enabled!', 'success');
            
            return subscription;
        } catch (error) {
            console.error('❌ Push subscription error:', error);
            
            // Show user-friendly error message
            let errorMsg = 'Push notifications unavailable. ';
            if (error.message.includes('ApplicationServerKey')) {
                errorMsg += 'Invalid VAPID key configuration.';
            } else if (error.message.includes('permission')) {
                errorMsg += 'Please allow notification permissions.';
            } else {
                errorMsg += error.message;
            }
            
            this.showToast(errorMsg, 'warning');
            return null;
        }
    }
    
    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/push/subscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(subscription)
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Subscription saved to server:', data);
            } else {
                console.error('❌ Server error:', data.error);
            }
        } catch (error) {
            console.error('❌ Failed to save subscription:', error);
        }
    }
    
    // ============================================================
    // CONNECTIVITY HANDLERS
    // ============================================================
    
    setupConnectivityHandlers() {
        // Online/Offline events
        window.addEventListener('online', () => {
            console.log('🌐 Back online');
            this.hideOfflineBanner();
            this.showToast('Back online!', 'success');
            
            // Sync pending data
            this.syncPendingData();
        });
        
        window.addEventListener('offline', () => {
            console.log('📴 Offline');
            this.showOfflineBanner();
            this.showToast('You are offline. Some features may be limited.', 'warning');
        });
        
        // Check initial status
        if (!navigator.onLine) {
            this.showOfflineBanner();
        }
    }
    
    showOfflineBanner() {
        let banner = document.getElementById('offlineBanner');
        if (banner) return;
        
        banner = document.createElement('div');
        banner.id = 'offlineBanner';
        banner.innerHTML = `
            <i class="fas fa-wifi-slash me-2"></i>
            You are offline. Some features may not work.
        `;
        banner.style.cssText = `
            position: fixed;
            top: 70px;
            left: 0;
            right: 0;
            background: #dc3545;
            color: white;
            text-align: center;
            padding: 10px;
            z-index: 9999;
            font-weight: 500;
            animation: slideDown 0.3s ease;
        `;
        
        document.body.prepend(banner);
    }
    
    hideOfflineBanner() {
        const banner = document.getElementById('offlineBanner');
        if (banner) {
            banner.style.animation = 'slideUp 0.3s ease forwards';
            setTimeout(() => banner.remove(), 300);
        }
    }
    
    async syncPendingData() {
        // Sync any pending maintenance requests, comments, etc.
        try {
            const response = await fetch('/api/sync-pending/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            const data = await response.json();
            console.log('✅ Synced pending data:', data);
        } catch (error) {
            console.error('Sync failed:', error);
        }
    }
    
    // ============================================================
    // UTILITY FUNCTIONS
    // ============================================================
    
    sendInstallEvent(status) {
        fetch('/api/pwa/install-event/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                status: status,
                display_mode: this.isStandalone ? 'standalone' : 'browser',
                platform: navigator.platform,
                user_agent: navigator.userAgent,
                timestamp: new Date().toISOString()
            })
        }).catch(err => console.error('Failed to send install event:', err));
    }
    
    showUpdateNotification() {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            border-radius: 12px;
            padding: 16px 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 16px;
            max-width: 90%;
            animation: slideUp 0.3s ease;
        `;
        toast.innerHTML = `
            <div>
                <strong>🔄 Update Available</strong>
                <div style="font-size: 14px; color: #666;">A new version is ready. Refresh to update.</div>
            </div>
            <button onclick="window.location.reload()" style="
                background: #c62828;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
            ">
                Update Now
            </button>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 10000);
    }
    
    showToast(message, type = 'info') {
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            info: '#17a2b8',
            warning: '#ffc107'
        };
        
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            info: 'fa-info-circle',
            warning: 'fa-exclamation-triangle'
        };
        
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 160px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 10000;
            background: ${colors[type] || '#6c757d'};
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            font-weight: 500;
            font-size: 14px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            animation: slideUp 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
        `;
        
        toast.innerHTML = `
            <i class="fas ${icons[type] || 'fa-info-circle'}"></i>
            ${message}
        `;
        
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideDown 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') return decodeURIComponent(value);
        }
        return null;
    }
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }
}

// ============================================================
// INITIALIZE PWA
// ============================================================

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we should initialize
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    
    if (!isStandalone) {
        // Initialize PWA
        window.tolleyaPWA = new TolleyaPWA();
        console.log('✅ Tolleya PWA initialized');
    } else {
        console.log('📱 Tolleya running as installed app');
    }
});

// Add CSS animations
const pwaStyles = document.createElement('style');
pwaStyles.textContent = `
    @keyframes slideUp {
        from { transform: translateX(-50%) translateY(20px); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
    @keyframes slideDown {
        from { transform: translateX(-50%) translateY(0); opacity: 1; }
        to { transform: translateX(-50%) translateY(20px); opacity: 0; }
    }
`;
document.head.appendChild(pwaStyles);

console.log('📱 Tolleya PWA loaded successfully');