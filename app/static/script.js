// ==================================================
// 1. CYBERPUNK ALERTS SYSTEM (SWEETALERT2)
// ==================================================
const swalScript = document.createElement('script');
swalScript.src = "https://cdn.jsdelivr.net/npm/sweetalert2@11";
document.head.appendChild(swalScript);

const swalStyle = document.createElement('style');
swalStyle.innerHTML = `
    .cyber-swal-popup {
        border: 1px solid #00f3ff !important;
        box-shadow: 0 0 20px rgba(0, 243, 255, 0.2) !important;
        backdrop-filter: blur(10px) !important;
    }
    .swal2-confirm {
        color: #000 !important;
        font-family: 'Orbitron', sans-serif !important;
        box-shadow: 0 0 10px rgba(0, 243, 255, 0.5) !important;
    }
    .cyber-swal-cancel {
        background: rgba(255, 77, 77, 0.1) !important;
        border: 1px solid #ff4d4d !important;
        color: #ff4d4d !important;
        font-family: 'Orbitron', sans-serif !important;
    }
`;
document.head.appendChild(swalStyle);

swalScript.onload = () => {
    window.alert = function (message) {
        Swal.fire({
            text: message,
            icon: message.toLowerCase().includes('error') || message.toLowerCase().includes('fail') ? 'error' : 'success',
            background: 'rgba(15, 23, 42, 0.95)',
            color: '#fff',
            confirmButtonColor: '#00f3ff',
            customClass: { popup: 'cyber-swal-popup' }
        });
    };
};

window.cyberConfirm = async function (message) {
    return Swal.fire({
        text: message,
        icon: 'warning',
        showCancelButton: true,
        background: 'rgba(15, 23, 42, 0.95)',
        color: '#fff',
        confirmButtonColor: '#ff4d4d',
        cancelButtonColor: 'rgba(255, 255, 255, 0.1)',
        confirmButtonText: 'Yes',
        cancelButtonText: 'Cancel',
        customClass: {
            popup: 'cyber-swal-popup',
            cancelButton: 'cyber-swal-cancel'
        }
    }).then((result) => result.isConfirmed);
};

// ==================================================
// 2. GLOBAL STATE & HELPER FUNCTIONS
// ==================================================
window.mainMeterId = parseInt(sessionStorage.getItem('mainMeterId')) || null;
window.activeEspId = parseInt(sessionStorage.getItem('activeEspId')) || null;

window.sysTracker = {
    powerOn: false,
    voltageState: 'normal',
    timerActive: false,
    initialized: false
};

window.masterSyncInterval = null;

function initMasterSync() {
    if (window.masterSyncInterval) {
        clearInterval(window.masterSyncInterval);
    }

    window.masterSyncInterval = setInterval(async () => {
        if (!window.activeEspId) return;
        try {
            const res = await fetch(`/latest?espid=${window.activeEspId}`);
            const data = await res.json();

            if (typeof updateDashboardUI === 'function') {
                updateDashboardUI(data);
            }

            if (typeof updateMiniChartUI === 'function' && document.getElementById('powerMiniChart')) {
                updateMiniChartUI(data);
            }

            if (window.currentBudgetKWh > 0 && typeof trackBudgetLocal === 'function') {
                trackBudgetLocal(data);
            }
        } catch (e) {
            console.error("Master Sync Error:", e);
        }
    }, 2500);
}

// Save and read ID from session storage
// Default to null instead of 0 if no device is active yet
window.activeEspId = parseInt(sessionStorage.getItem('activeEspId')) || null;

function safeTxt(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function getDeviceIcon(name) {
    const n = name.toLowerCase();

    if (n.includes("fridge") || n.includes("refrigerator")) return "fa-snowflake";
    if (n.includes("microwave") || n.includes("oven")) return "fa-fire-burner";
    if (n.includes("kettle") || n.includes("coffee") || n.includes("tea")) return "fa-mug-hot";
    if (n.includes("toaster") || n.includes("grill")) return "fa-bread-slice";
    if (n.includes("blender") || n.includes("mixer")) return "fa-lemon";
    if (n.includes("dish")) return "fa-soap";

    if (n.includes("iron")) return "fa-shirt";
    if (n.includes("wash") || n.includes("laundry")) return "fa-jug-detergent";
    if (n.includes("heater") || n.includes("boiler")) return "fa-temperature-arrow-up";
    if (n.includes("fan")) return "fa-fan";
    if (n.includes("ac") || n.includes("conditioner") || n.includes("cool")) return "fa-wind";
    if (n.includes("vacuum")) return "fa-broom";

    if (n.includes("tv") || n.includes("screen")) return "fa-tv";
    if (n.includes("pc") || n.includes("computer") || n.includes("laptop")) return "fa-laptop";
    if (n.includes("router") || n.includes("wifi")) return "fa-wifi";
    if (n.includes("playstation") || n.includes("xbox") || n.includes("game")) return "fa-gamepad";
    if (n.includes("phone") || n.includes("charger")) return "fa-mobile-screen";

    if (n.includes("lamp") || n.includes("light") || n.includes("bulb") || n.includes("led")) return "fa-lightbulb";

    return "fa-plug-circle-bolt";
}

window.sysSettings = null;

window.loadSysSettings = async function () {
    try {
        const res = await fetch(`/api/get_user_settings?espid=${window.activeEspId}`);
        const data = await res.json();
        if (data.status === 'success') {
            window.sysSettings = data.settings;
        }
    } catch (e) {
        console.error(e);
    }
};

// ==================================================
// 3. INITIALIZATION & ROUTING
// ==================================================
document.addEventListener('DOMContentLoaded', function () {
    console.log("🚀 SENTRA System Loaded");

    window.updateNavigationState();
    window.checkSettingsAccess();

    const body = document.body;

    if (body.classList.contains('dashboard-page')) initDashboard();
    if (body.classList.contains('analytics-page')) initAnalytics();
    if (body.classList.contains('auth-page')) initAuth();
    if (body.classList.contains('settings-page')) initSettings();
    if (body.classList.contains('contact-page')) initContact();

    initSidebar();
    initNotifications();
    initDeviceScrollLogic();

    if (document.getElementById('powerMiniChart')) {
        initPowerMiniChart();
    }

    if (document.getElementById('tariff-type')) {
        updateTierPrice();
    }

    if (!body.classList.contains('auth-page')) {
        window.syncNotifications();
        setInterval(window.syncNotifications, 3000);
    }
});

// ==================================================
// 4. NAVIGATION & LAYOUT
// ==================================================
window.forceSyncNow = async function () {
    try {
        const res = await fetch(`/latest?espid=${window.activeEspId}`);
        const data = await res.json();

        if (typeof updateDashboardUI === 'function') {
            updateDashboardUI(data);
        }
        if (typeof updateMiniChartUI === 'function' && document.getElementById('powerMiniChart')) {
            updateMiniChartUI(data);
        }
    } catch (e) {
        console.error("Force Sync Error:", e);
    }
};

window.switchEsp = function (id) {
    window.activeEspId = id;
    sessionStorage.setItem('activeEspId', id);
    
    window.checkSettingsAccess(); 
    window.updateNavigationState();
    
    window.loadEspTabs();
    window.loadSysSettings();

    forceSyncNow();

    if (typeof syncTimerUI === 'function') syncTimerUI();

    if (document.body.classList.contains('settings-page')) {
        initSettings();
        if (typeof window.loadEnergyBudgetFromServer === 'function') {
            window.loadEnergyBudgetFromServer();
        }
    }
};

window.updateNavigationState = function () {

    const settingsLinks = [
        document.getElementById('nav-settings'),
        document.getElementById('sidebar-settings-link')
    ];


    const isMainMeterActive = (window.activeEspId === window.mainMeterId);

    settingsLinks.forEach(link => {
        if (link) {
            if (isMainMeterActive) {
                link.classList.add('disabled-nav-link');
                link.title = "Settings are disabled for the Main Meter";
                link.onclick = (e) => e.preventDefault();
            } else {
                link.classList.remove('disabled-nav-link');
                link.removeAttribute('title');
                link.onclick = null;
            }
        }
    });

    const aiSection = document.getElementById('ai-monitoring-section');
    if (aiSection) {
        if (isMainMeterActive) {
            aiSection.style.display = 'block';
        } else {
            aiSection.style.display = 'none';
        }
    }

    const aiPredictionsSection = document.getElementById('ai-predictions-section');
    if (aiPredictionsSection) {
        aiPredictionsSection.style.display = isMainMeterActive ? 'block' : 'none';
    }

    if (isMainMeterActive && document.body.classList.contains('settings-page')) {
        window.location.href = '/dashboard';
    }
};

function toggleProfileDropdown() {
    const dropdown = document.getElementById('profile-dropdown');
    if (dropdown) {
        dropdown.style.display = (dropdown.style.display === 'none' || dropdown.style.display === '') ? 'block' : 'none';
    }
}

function initSidebar() {
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');

    if (toggle && sidebar) {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('open');
            document.body.classList.toggle('sidebar-open');
        });

        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
                sidebar.classList.remove('open');
                document.body.classList.remove('sidebar-open');
            }
        });
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');

    if (sidebar) {
        sidebar.classList.toggle('open');
        if (overlay) {
            overlay.style.display = sidebar.classList.contains('open') ? 'block' : 'none';
        }
    }
}

window.openWifiModal = function () {
    const modal = document.getElementById('wifiModal');
    if (modal) modal.style.display = 'flex';
};

window.closeWifiModal = function () {
    const modal = document.getElementById('wifiModal');
    if (modal) modal.style.display = 'none';
};

// Global Click Handlers
document.addEventListener('click', function (event) {
    const profileContainer = document.querySelector('.profile-dropdown-container');
    const profileDropdown = document.getElementById('profile-dropdown');
    if (profileContainer && profileDropdown && !profileContainer.contains(event.target)) {
        profileDropdown.style.display = 'none';
    }

    const notifContainer = document.querySelector('.notification-container');
    const notifPopup = document.getElementById('notification-popup');
    if (notifContainer && notifPopup && !notifContainer.contains(event.target)) {
        notifPopup.style.display = 'none';
    }
});

window.onclick = function (event) {
    const deviceModal = document.getElementById('deviceModal');
    if (event.target == deviceModal) closeDeviceModal();
};

// ==================================================
// 5. DASHBOARD & DEVICES LOGIC
// ==================================================
// --- Update initDashboard function ---
function initDashboard() {
    console.log("Initializing Dashboard...");
    window.loadEspTabs();
    window.loadSysSettings();

    checkMainMeterSetup();

    initMasterSync();

    setInterval(fetchAIStatus, 4000);
    fetchAIStatus();
}

// --- New Function: Check and Auto-create Main Meter ---
async function checkMainMeterSetup() {
    try {
        const res = await fetch('/api/main_meter_status');
        const data = await res.json();

        if (data.status === 'not_found') {
            document.getElementById('mainMeterModal').style.display = 'flex';
            const idDisplay = document.getElementById('main-meter-generated-id');

            const idRes = await fetch('/api/generate_esp_id');
            const idData = await idRes.json();

            if (idData.status === 'success') {
                idDisplay.innerText = idData.espid;
                idDisplay.dataset.espid = idData.espid;
            } else {
                idDisplay.innerText = "ERROR";
            }
        }
    } catch (e) {
        console.error("Main Meter Check Error:", e);
    }
}

// --- New Function: Register Main Meter ---
window.registerMainMeter = async function () {
    const idDisplay = document.getElementById('main-meter-generated-id');
    const espid = idDisplay.dataset.espid;

    if (!espid) return;

    try {
        const res = await fetch('/api/add_safe_power_device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: "TOTAL (MAIN)", espid: parseInt(espid), is_main: true })
        });

        const data = await res.json();
        if (data.status === 'success') {
            document.getElementById('mainMeterModal').style.display = 'none';
            window.triggerSmartAlert('SYSTEM INITIALIZED', 'Main meter ID generated successfully. You can view it in Settings.', 'info');
            window.loadEspTabs();
        } else {
            alert("Error: " + data.message);
        }
    } catch (e) {
        alert("Connection Error");
    }
};

window.loadEspTabs = async function () {
    try {
        const res = await fetch('/api/get_saved_esps');
        const data = await res.json();

        if (data.status === 'success') {
            const mainEsp = data.esps.find(e => e.is_main === true);
            if (mainEsp) {
                window.mainMeterId = mainEsp.espid;
                sessionStorage.setItem('mainMeterId', mainEsp.espid);
            }

            const tabsList = document.getElementById('esp-tabs-list');
            if (!tabsList) return;

            let html = '';

            const sortedEsps = data.esps.sort((a, b) => {
                return (b.is_main === true ? 1 : 0) - (a.is_main === true ? 1 : 0);
            });

            sortedEsps.forEach(esp => {
                const isActive = window.activeEspId === esp.espid ? 'active' : '';
                html += `<button class="esp-tab ${isActive}" onclick="switchEsp(${esp.espid})">${esp.device_name.toUpperCase()}</button>`;
            });

            tabsList.innerHTML = html;

            if (sortedEsps.length > 0 && !sortedEsps.find(e => e.espid === window.activeEspId)) {
                switchEsp(sortedEsps[0].espid);
            }

            window.updateNavigationState();
            window.checkSettingsAccess();
        }
    } catch (e) {
        console.error("Error loading tabs", e);
    }
};

function updateDashboardUI(data) {
    try {

        safeTxt('voltage-value', data.voltage + ' V');
        safeTxt('current-value', data.current + ' A');
        safeTxt('power-value', data.power + ' W');
        safeTxt('energy-value', data.energy + ' kWh');
        safeTxt('frequency-value', data.frequency + ' Hz');
        safeTxt('power_factor-value', data.pf);

        const costElement = document.getElementById('cost-value');
        if (costElement && data.total_dashboard_cost !== undefined) {
            costElement.textContent = parseFloat(data.total_dashboard_cost).toFixed(2) + ' EGP';
        }

        const dot = document.getElementById('status-dot');
        const txt = document.getElementById('status-text');
        const pwrCard = document.querySelector('.power-card');
        if (txt && pwrCard) {
            if (data.power > 5) {
                txt.innerHTML = "● Active";
                txt.style.color = "#10b981";
                pwrCard.style.filter = "none";
                pwrCard.style.opacity = "1";
            } else {
                txt.innerHTML = "○ Standby (OFF)";
                txt.style.color = "#f87171";
                pwrCard.style.filter = "grayscale(80%)";
                pwrCard.style.opacity = "0.7";
            }
        }

        const efficiencyPercent = (data.pf * 100).toFixed(1);
        safeTxt('efficiency-value', efficiencyPercent + '%');

        const effRing = document.getElementById('efficiency-ring');
        if (effRing) {
            effRing.style.strokeDasharray = `${Math.min(efficiencyPercent, 100)}, 100`;
        }

        const qualityEl = document.getElementById('quality-value');
        if (qualityEl) {
            let newState = data.pf >= 0.9 ? "EXCELLENT" : (data.pf >= 0.8 ? "GOOD" : "POOR");

            if (qualityEl.dataset.currentState !== newState) {
                qualityEl.dataset.currentState = newState;
                qualityEl.innerText = newState;

                if (newState === "EXCELLENT") {
                    qualityEl.style.color = "#4ade80";
                    qualityEl.style.background = "rgba(74, 222, 128, 0.15)";
                    qualityEl.style.borderColor = "#4ade80";
                    qualityEl.style.boxShadow = "0 0 15px rgba(74, 222, 128, 0.5), inset 0 0 10px rgba(74, 222, 128, 0.2)";
                } else if (newState === "GOOD") {
                    qualityEl.style.color = "#facc15";
                    qualityEl.style.background = "rgba(250, 204, 21, 0.15)";
                    qualityEl.style.borderColor = "#facc15";
                    qualityEl.style.boxShadow = "0 0 15px rgba(250, 204, 21, 0.5), inset 0 0 10px rgba(250, 204, 21, 0.2)";
                } else {
                    qualityEl.style.color = "#f87171";
                    qualityEl.style.background = "rgba(248, 113, 113, 0.15)";
                    qualityEl.style.borderColor = "#f87171";
                    qualityEl.style.boxShadow = "0 0 15px rgba(248, 113, 113, 0.5), inset 0 0 10px rgba(248, 113, 113, 0.2)";
                }
            }
        }

        const currentPower = data.power || 0;
        const limit = 2000;
        const loadPercent = Math.min(((currentPower / limit) * 100), 100).toFixed(1);

        safeTxt('load-value', loadPercent + '%');
        const loadBar = document.getElementById('load-bar');
        const statusText = document.getElementById('load-status-text');

        if (loadBar) {
            loadBar.style.width = loadPercent + '%';
            let newLoadState = loadPercent > 80 ? "HIGH" : "STABLE";

            if (loadBar.dataset.currentLoad !== newLoadState) {
                loadBar.dataset.currentLoad = newLoadState;

                if (newLoadState === "HIGH") {
                    loadBar.style.background = "#ff4d4d";
                    loadBar.style.boxShadow = "0 0 10px #ff4d4d";
                    if (statusText) {
                        statusText.style.color = "#ff4d4d";
                        statusText.innerText = "High Load";
                    }
                    if (!window.highLoadAlertTriggered) {
                        window.triggerSmartAlert('CRITICAL ALERT', `High power consumption detected: ${loadPercent}% load.`, 'error');
                        window.highLoadAlertTriggered = true;
                    }
                } else {
                    loadBar.style.background = "linear-gradient(90deg, #ec4899, #8b5cf6)";
                    loadBar.style.boxShadow = "0 0 10px #ec4899";
                    if (statusText) {
                        statusText.style.color = "#94a3b8";
                        statusText.innerText = "System Stable";
                    }
                    window.highLoadAlertTriggered = false;
                }
            }
        }

        const isNowOn = data.power > 5;
        if (window.sysTracker.initialized && window.sysTracker.powerOn !== isNowOn) {
            if (window.activeEspId !== window.mainMeterId) {
                if (isNowOn) {
                    window.addNotification('CIRCUIT STATUS', 'Power has been turned ON (Circuit Closed)', 'info', 'Just now');
                } else {
                    window.addNotification('CIRCUIT STATUS', 'Power has been turned OFF (Circuit Opened)', 'info', 'Just now');
                }
            } else {
                if (!isNowOn && window.sysTracker.powerOn) {
                    window.triggerSmartAlert('GRID OUTAGE', 'Main power grid outage detected! (Blackout)', 'error');
                } else if (isNowOn && !window.sysTracker.powerOn) {
                    window.addNotification('GRID RESTORED', 'Main power grid has been restored.', 'info', 'Just now');
                }
            }
            window.sysTracker.powerOn = isNowOn;
        } else if (!window.sysTracker.initialized) {
            window.sysTracker.powerOn = isNowOn;
            window.sysTracker.initialized = true;
        }

        let maxV = window.sysSettings?.max_voltage || 250;
        let minV = window.sysSettings?.min_voltage || 190;
        let currentVState = 'normal';

        if (data.voltage > maxV) currentVState = 'high';
        else if (data.voltage > 50 && data.voltage < minV) currentVState = 'low';

        if (currentVState !== window.sysTracker.voltageState) {
            if (currentVState === 'high') {
                window.triggerSmartAlert('CRITICAL: HIGH VOLTAGE', `Voltage spiked to ${data.voltage}V! Exceeds maximum limit of ${maxV}V.`, 'error');
            } else if (currentVState === 'low') {
                window.triggerSmartAlert('WARNING: LOW VOLTAGE', `Voltage dropped to ${data.voltage}V! Below minimum limit of ${minV}V.`, 'maintenance');
            }
            window.sysTracker.voltageState = currentVState;
        }

        if (data.command) {
            if (typeof window.updateRemoteUI === 'function') {
                window.updateRemoteUI(data.command);
            }
        }

        const onBtnEl = document.getElementById('on-btn');
        if (onBtnEl) {
            if (data.budget_locked === true) {
                onBtnEl.disabled = true;
                onBtnEl.style.opacity = '0.4';
                onBtnEl.style.cursor = 'not-allowed';
            } else {
                onBtnEl.disabled = false;
                onBtnEl.style.opacity = '1';
                onBtnEl.style.cursor = 'pointer';
            }
        }

    } catch (e) {
        console.error("Data Sync Error:", e);
    }
}

// Add Safe Power Modal Functions
window.openSafePowerModal = async function () {
    document.getElementById('safePowerModal').style.display = 'flex';
    document.getElementById('safeDeviceName').value = '';

    const idDisplay = document.getElementById('generated-esp-id');
    idDisplay.innerText = "Loading...";

    try {
        const res = await fetch('/api/generate_esp_id');
        const data = await res.json();

        if (data.status === 'success') {
            idDisplay.innerText = data.espid;
            idDisplay.dataset.espid = data.espid;
        } else {
            idDisplay.innerText = "Error generating ID";
        }
    } catch (e) {
        console.error(e);
        idDisplay.innerText = "Network Error";
    }
};

window.closeSafePowerModal = function () {
    document.getElementById('safePowerModal').style.display = 'none';
};

window.confirmAddSafeDevice = async function () {
    const name = document.getElementById('safeDeviceName').value.trim();
    const idDisplay = document.getElementById('generated-esp-id');
    const espid = idDisplay.dataset.espid;

    if (!name || !espid) return alert("Please enter name and wait for ID generation.");

    try {
        const res = await fetch('/api/add_safe_power_device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, espid: parseInt(espid), is_main: false }) // Forced to false
        });
        const data = await res.json();
        if (data.status === 'success') {
            closeSafePowerModal();
            window.loadEspTabs();
            window.switchEsp(parseInt(espid));
        } else alert("Error: " + data.message);
    } catch (e) { alert("Connection Error"); }
};

window.showMyDeviceIDs = async function () {
    try {
        const res = await fetch('/api/my_device_ids');
        const data = await res.json();

        if (data.status === 'success') {
            let htmlContent = '<div style="text-align: left; margin-top: 15px;">';

            data.devices.forEach(dev => {
                const color = dev.is_main ? '#f59e0b' : '#00f3ff';
                const icon = dev.is_main ? 'fa-bolt' : 'fa-plug-circle-bolt';
                htmlContent += `
                <div style="background: rgba(255,255,255,0.05); border-left: 4px solid ${color}; padding: 12px; margin-bottom: 10px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <i class="fa-solid ${icon}" style="color: ${color}; margin-right: 8px;"></i>
                        <strong style="color: #fff; font-size: 1rem;">${dev.device_name}</strong>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="color: ${color}; font-family: monospace;">ID: ${dev.espid}</span>
                        
                        <button onclick="window.editSafeDevice('${dev.espid}', '${dev.device_name}')" style="background: none; border: none; color: #facc15; cursor: pointer;" title="Edit">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button onclick="window.deleteSafeDevice('${dev.espid}')" style="background: none; border: none; color: #ff4d4d; cursor: pointer;" title="Delete">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                        
                        <button onclick="window.copyDirectId('${dev.espid}', this)" style="background: none; border: none; color: ${color}; cursor: pointer;" title="Copy ID">
                            <i class="fa-regular fa-copy"></i>
                        </button>
                    </div>
                </div>
            `;
            });

            htmlContent += '</div><p style="color: #94a3b8; font-size: 0.8rem; margin-top: 15px;">Use these IDs during the ESP WiFi Setup phase.</p>';

            Swal.fire({
                title: 'YOUR HARDWARE IDs',
                html: htmlContent,
                background: 'rgba(15, 23, 42, 0.95)',
                color: '#fff',
                confirmButtonColor: '#00f3ff',
                customClass: { popup: 'cyber-swal-popup' },
                width: '500px'
            });
        }
    } catch (e) {
        console.error("Error fetching IDs", e);
    }
};

window.copyDirectId = function (idText, btnElement) {
    navigator.clipboard.writeText(idText).then(() => {
        const originalHtml = btnElement.innerHTML;

        btnElement.innerHTML = '<i class="fa-solid fa-check" style="color: #4ade80; font-size: 1.2rem;"></i>';

        setTimeout(() => {
            btnElement.innerHTML = originalHtml;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
};


function initDeviceScrollLogic() {
    const scrollContainer = document.querySelector('.devices-scroll-container');
    const btnLeft = document.getElementById('scrollLeft');
    const btnRight = document.getElementById('scrollRight');

    if (scrollContainer && btnLeft && btnRight) {
        btnRight.addEventListener('click', () => {
            scrollContainer.scrollBy({ left: 250, behavior: 'smooth' });
        });

        btnLeft.addEventListener('click', () => {
            scrollContainer.scrollBy({ left: -250, behavior: 'smooth' });
        });
    }
}

function addNewDeviceUI() {
    const modal = document.getElementById('deviceModal');
    if (modal) {
        modal.style.display = 'flex';
        document.getElementById('newDeviceName').focus();
    }
}

function closeDeviceModal() {
    const modal = document.getElementById('deviceModal');
    if (modal) {
        modal.style.display = 'none';
        document.getElementById('newDeviceName').value = '';
    }
}

async function confirmAddDevice() {
    const nameInput = document.getElementById('newDeviceName');
    const deviceName = nameInput.value.trim();

    if (deviceName) {
        try {
            const response = await fetch('/api/add_device', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: deviceName })
            });

            const data = await response.json();

            if (data.status === 'success') {
                const iconClass = getDeviceIcon(deviceName);

                const newCardHTML = `
                <div class="cyber-card">
                    <div class="cyber-card-inner">
                        <div class="card-header">
                            <span class="device-name">${deviceName}</span>
                            <label class="toggle-switch">
                                <input type="checkbox" checked>
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="card-body">
                            <i class="fa-solid ${iconClass} device-icon"></i>
                        </div>
                        <div class="card-footer">
                            <span class="power-value">0W</span>
                        </div>
                    </div>
                </div>`;

                const addBtn = document.querySelector('.add-new-card');
                if (addBtn) addBtn.insertAdjacentHTML('beforebegin', newCardHTML);

                closeDeviceModal();

                const scrollContainer = document.querySelector('.devices-scroll-container');
                if (scrollContainer) {
                    setTimeout(() => {
                        scrollContainer.scrollTo({ left: scrollContainer.scrollWidth, behavior: 'smooth' });
                    }, 100);
                }
            } else {
                alert("Error: " + data.message);
            }
        } catch (error) {
            console.error("Connection Error:", error);
            alert("Failed to save the device.");
        }
    }
}
// window.editSafeDevice = async function (espid, currentName) {
//     const { value: newName } = await Swal.fire({
//         title: 'تعديل اسم الجهاز',
//         input: 'text',
//         inputValue: currentName,
//         showCancelButton: true,
//         background: 'rgba(15, 23, 42, 0.95)',
//         color: '#fff',
//         confirmButtonColor: '#00f3ff',
//         cancelButtonColor: '#ff4d4d',
//         inputValidator: (value) => {
//             if (!value) return 'يجب كتابة اسم للجهاز!'
//         }
//     });

//     if (newName) {
//         try {
//             const res = await fetch('/api/edit_safe_power_device', {
//                 method: 'POST',
//                 headers: { 'Content-Type': 'application/json' },
//                 body: JSON.stringify({ espid: parseInt(espid), name: newName })
//             });
//             const data = await res.json();
//             if (data.status === 'success') {
//                 window.showMyDeviceIDs();
//                 window.loadEspTabs();
//             } else alert("Error: " + data.message);
//         } catch (e) { alert("خطأ في الاتصال"); }
//     }
// };

window.deleteSafeDevice = async function (espid) {
    const confirmation = await window.cyberConfirm("Are you sure you want to delete this device? You will no longer be able to monitor it.");
    if (confirmation) {
        try {
            const res = await fetch('/api/delete_safe_power_device', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ espid: parseInt(espid) })
            });
            const data = await res.json();
            if (data.status === 'success') {
                window.showMyDeviceIDs();
                window.loadEspTabs();
            } else alert("Error: " + data.message);
        } catch (e) { alert("خطأ في الاتصال"); }
    }
};

function calculateCostBySegment(energyKwh, segmentNumber) {
    const segmentPrices = {
        1: 0.58,
        2: 0.68,
        3: 0.83,
        4: 1.25,
        5: 1.40,
        6: 1.50,
        7: 1.65
    };
    
    const price = segmentPrices[segmentNumber] || 0.58; 
    return energyKwh * price;
}

function runDynamicReactorEngine() {
    const aiMode = document.getElementById('ai-mode-content');
    const reactorMode = document.getElementById('reactor-mode-content');
    if (!aiMode || !reactorMode) return;

    const activeTab = document.querySelector('.esp-tabs-wrapper .active');
    if (!activeTab) return;

    const tabText = activeTab.textContent.toUpperCase();
    
    if (tabText.includes('TOTAL') || tabText.includes('MAIN')) {
        aiMode.style.display = 'flex';
        reactorMode.style.display = 'none';
        return;
    }

    aiMode.style.display = 'none';
    reactorMode.style.display = 'flex';

    const cleanDeviceName = activeTab.textContent.replace(/⚡|[\d.]+\s*W|[\d.]+\s*A/gi, '').trim();
    
    let currentAmp = 0;
    let powerW = 0;

    const ampElement = document.getElementById('current-value');
    const powerElement = document.getElementById('livePowerValue') || document.getElementById('power-value');

    if (ampElement) currentAmp = parseFloat(ampElement.textContent) || 0;
    if (powerElement) powerW = parseFloat(powerElement.textContent) || 0;

    const nameEl = document.getElementById('reactorDeviceName');
    const ampValEl = document.getElementById('reactorAmpValue');
    const limitEl = document.getElementById('reactorAmpLimit');
    const badgeEl = document.getElementById('reactorStatusBadge');
    const ringEl = document.getElementById('reactorRingProgress');
    const iconContainer = document.getElementById('reactorIcon');
    const reactorCard = document.getElementById('dynamic-ai-card');
    const glowEl = document.getElementById('reactorGlow');

    if (nameEl) nameEl.textContent = cleanDeviceName;
    if (ampValEl) ampValEl.textContent = currentAmp.toFixed(2);

    let maxLimit = 15;
    const upperName = cleanDeviceName.toUpperCase();

    if (window.sysSettings && window.sysSettings.current_limit) {
        maxLimit = parseFloat(window.sysSettings.current_limit);
    } else {
        if (upperName.includes('AC') || upperName.includes('CONDITIONER')) maxLimit = 20;
        else if (upperName.includes('FRIDGE') || upperName.includes('REFRIGERATOR')) maxLimit = 10;
        else if (upperName.includes('KETTLE')) maxLimit = 12;
        else if (upperName.includes('HEATER')) maxLimit = 16;
    }
    
    if (limitEl) limitEl.textContent = maxLimit;

    let iconClass = "fa-solid fa-microchip";
    
    if (upperName.includes('KETTLE') || upperName.includes('COFFEE') || upperName.includes('TEA')) {
        iconClass = "fa-solid fa-mug-hot";
    }
    else if (upperName.includes('AC') || upperName.includes('CONDITIONER')) {
        iconClass = "fa-solid fa-wind";
    }
    else if (upperName.includes('FRIDGE') || upperName.includes('REFRIGERATOR')) {
        iconClass = "fa-solid fa-snowflake";
    }
    else if (upperName.includes('WASH') || upperName.includes('LAUNDRY')) {
        iconClass = "fa-solid fa-jug-detergent";
    }
    else if (upperName.includes('MICROWAVE') || upperName.includes('OVEN')) {
        iconClass = "fa-solid fa-fire-burner";
    }
    else if (upperName.includes('HEAT') || upperName.includes('BOILER')) {
        iconClass = "fa-solid fa-temperature-arrow-up";
    }
    else if (upperName.includes('IRON')) {
        iconClass = "fa-solid fa-shirt";
    }
    else if (upperName.includes('TV') || upperName.includes('SCREEN')) {
        iconClass = "fa-solid fa-tv";
    }
    else if (upperName.includes('ROUTER') || upperName.includes('WIFI')) {
        iconClass = "fa-solid fa-wifi";
    }
    else if (upperName.includes('LAMP') || upperName.includes('LIGHT') || upperName.includes('BULB')) {
        iconClass = "fa-solid fa-lightbulb";
    }
    else {
        iconClass = "fa-solid fa-plug-circle-bolt";
    }

    if (iconContainer) {
        iconContainer.innerHTML = `<i class="${iconClass}"></i>`;
    }
    
    const percentage = Math.min((currentAmp / maxLimit) * 100, 100);
    const radius = 45;
    const circumference = 2 * Math.PI * radius;
    let dashoffset = circumference - (percentage / 100) * circumference;

    if (ringEl) {
        ringEl.style.strokeDasharray = circumference;
    }

    if (reactorCard) {
        reactorCard.classList.remove('reactor-safe', 'reactor-warning', 'reactor-critical', 'reactor-standby');

        if (powerW < 3) {
            reactorCard.classList.add('reactor-standby');
            if (badgeEl) {
                badgeEl.textContent = "STANDBY";
                badgeEl.style.color = "#94a3b8";
                badgeEl.style.background = "rgba(148, 163, 184, 0.1)";
            }
            if (ringEl) ringEl.style.strokeDashoffset = circumference;
        } else {
            if (ringEl) ringEl.style.strokeDashoffset = dashoffset;

            if (percentage <= 50) {
                reactorCard.classList.add('reactor-safe');
                if (badgeEl) {
                    badgeEl.textContent = "SAFE";
                    badgeEl.style.color = "#00f3ff";
                    badgeEl.style.background = "rgba(0, 243, 255, 0.15)";
                }
            } else if (percentage <= 80) {
                reactorCard.classList.add('reactor-warning');
                if (badgeEl) {
                    badgeEl.textContent = "WARNING";
                    badgeEl.style.color = "#facc15";
                    badgeEl.style.background = "rgba(250, 204, 21, 0.15)";
                }
            } else {
                reactorCard.classList.add('reactor-critical');
                if (badgeEl) {
                    badgeEl.textContent = "CRITICAL";
                    badgeEl.style.color = "#ff4d4d";
                    badgeEl.style.background = "rgba(255, 77, 77, 0.15)";
                }
            }
        }
    }

    if (glowEl && powerW >= 3) {
        const animSpeed = Math.max(0.2, 2.0 - (powerW / 2000));
        glowEl.style.animation = `pulseGlow ${animSpeed}s infinite alternate`;
    } else if (glowEl) {
        glowEl.style.animation = 'none';
    }
}

setInterval(runDynamicReactorEngine, 500);
// ==================================================
// SUPABASE AI PREDICTIONS CHART
// ==================================================


const SUPABASE_URL = "https://wtsfngscmtmywcklplhj.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0c2ZuZ3NjbXRteXdja2xwbGhqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjEzNDQ0MSwiZXhwIjoyMDg3NzEwNDQxfQ.wYesuGasSOKtuvDwXJdQBZPY4MkTqVsKwKOGmjBtCBA";

let _supabase = null;
if (window.supabase) {
    _supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
} else {
    console.warn("Supabase library not loaded. AI predictions chart will be disabled.");
}
async function fetchAndRenderPredictionsChart() {
    console.log("Fetching the last 24 predictions...");
    
    // Fetch the latest 24 rows ordered by descending ID
    let { data: rows, error } = await _supabase
        .from('predictions')
        .select('prediction_time, predicted_value, id')
        .order('id', { ascending: false })
        .limit(24); 

    if (error) {
        console.error("Failed to fetch prediction data:", error);
        return;
    }

    if (!rows || rows.length === 0) {
        console.warn("No predictions available in the database.");
        return;
    }

    // Reverse array to display chronological order (left to right)
    rows.reverse();

    // Map X-axis: Format time
    const labelsX = rows.map(row => {
        const dateObj = new Date(row.prediction_time);
        return dateObj.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC' });
    });

    // Map Y-axis: Predicted values
    const dataValuesY = rows.map(row => row.predicted_value);

    const canvas = document.getElementById('futurePredictionsChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Destroy previous chart instance to prevent rendering glitches
    if (window.predictionsChartInstance) {
        window.predictionsChartInstance.destroy();
    }

    // Create Cyberpunk Purple Gradient
    const gradientPurple = ctx.createLinearGradient(0, 0, 0, 400);
    gradientPurple.addColorStop(0, 'rgba(187, 19, 254, 0.5)'); 
    gradientPurple.addColorStop(1, 'rgba(187, 19, 254, 0.0)');

    // Render the new chart
    window.predictionsChartInstance = new Chart(ctx, {
        type: 'line', 
        data: {
            labels: labelsX,
            datasets: [{
                label: 'Predicted Power (W)',
                data: dataValuesY,
                borderColor: '#bb13fe', 
                backgroundColor: gradientPurple,
                borderWidth: 3,
                fill: true,
                tension: 0.4, 
                pointRadius: 3,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#bb13fe',
                pointHoverRadius: 6,
                pointHoverBackgroundColor: '#00f3ff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: true,
                    labels: { color: '#fff', font: { family: 'Orbitron', size: 12 } }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#00f3ff',
                    bodyColor: '#fff',
                    borderColor: '#bb13fe',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function (context) { return `Predicted: ${context.parsed.y} W`; }
                    }
                }
            },
            scales: {
                x: { 
                    title: { display: true, text: 'Prediction Time (UTC)', color: '#94a3b8', font: { family: 'Rajdhani', size: 14 } },
                    grid: { color: 'rgba(255, 255, 255, 0.05)', display: false },
                    ticks: { color: 'rgba(255, 255, 255, 0.5)', font: { size: 10 } }
                },
                y: { 
                    title: { display: true, text: 'Predicted Value (Watts)', color: '#94a3b8', font: { family: 'Rajdhani', size: 14 } }, 
                    beginAtZero: false,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#00f3ff', font: { size: 12 }, padding: 10 }
                }
            }
        }
    });
    console.log("Predictions chart rendered successfully.");
}

// Ensure the chart initializes when the dashboard loads
document.addEventListener('DOMContentLoaded', () => {
    if (document.body.classList.contains('dashboard-page')) {
        setTimeout(() => {
            if (document.getElementById('futurePredictionsChart')) {
                fetchAndRenderPredictionsChart();
                
                // Refresh predictions every 60 seconds automatically
                setInterval(fetchAndRenderPredictionsChart, 60000); 
            }
        }, 1000); // Slight delay to ensure DOM and libraries are fully loaded
    }
});

// ==================================================
// 6. AI ENGINE & NILM
// ==================================================
async function fetchAIStatus() {
    if (!window.activeEspId) return;
    try {
        const response = await fetch(`/ai-status?espid=${window.activeEspId}`);

        const data = await response.json();

        if (data.status === "success") {
            const deviceNameEl = document.getElementById('ai-device-name');
            const deviceStatusEl = document.getElementById('ai-device-status');
            const cardInner = document.querySelector('.ai-card-border');

            if (deviceNameEl) deviceNameEl.textContent = data.device_name;

            if (deviceStatusEl) {
                deviceStatusEl.textContent = data.badge_status;

                if (data.badge_status === "Active") {
                    deviceStatusEl.style.backgroundColor = "#10b981";
                    deviceStatusEl.style.color = "#ffffff";
                    if (cardInner) cardInner.style.boxShadow = "0 0 20px rgba(0, 234, 255, 0.6)";
                } else {
                    deviceStatusEl.style.backgroundColor = "#4b5563";
                    deviceStatusEl.style.color = "#d1d5db";
                    if (cardInner) cardInner.style.boxShadow = "none";
                }
            }
        }
    } catch (error) {
        console.error("AI Model Connection Error:", error);
    }
}

window.SIMULATION_MODE = 'ALL';

const DEVICE_CONFIGS = {
    KETTLE: { url: '/static/kettle_test.json', cutoff: 3100.0, data: null, startIndex: 0 },
    FRIDGE: { url: '/static/fridge_test.json', cutoff: 300.0, data: null, startIndex: 0 },
    WASHING_MACHINE: { url: '/static/washing_test.json', cutoff: 2500.0, data: null, startIndex: 0 }
};

let timeIndex = 0;

Object.keys(DEVICE_CONFIGS).forEach(device => {
    fetch(DEVICE_CONFIGS[device].url)
        .then(response => response.json())
        .then(json => {
            DEVICE_CONFIGS[device].data = json.gt;

            if (device === 'KETTLE') {
                for (let i = 0; i < json.gt.length; i++) {
                    if (json.gt[i][0] > 0.3) {
                        DEVICE_CONFIGS[device].startIndex = Math.max(0, i - 470);
                        break;
                    }
                }
            } else if (device === 'WASHING_MACHINE') {
                for (let i = 0; i < json.gt.length; i++) {
                    if (json.gt[i][0] > 0.1) {
                        DEVICE_CONFIGS[device].startIndex = Math.max(0, i - 470);
                        break;
                    }
                }
            } else if (device === 'FRIDGE') {
                for (let i = 0; i < json.gt.length; i++) {
                    if (json.gt[i][0] > 0.2) {
                        DEVICE_CONFIGS[device].startIndex = Math.max(0, i - 470);
                        break;
                    }
                }
            }
        })
        .catch(err => console.error(err));
});

function getCurrentPowerSequence() {
    const windowSize = 480;
    let sequence = new Array(windowSize).fill(0);

    for (let i = 0; i < windowSize; i++) {
        sequence[i] = 10 + (Math.random() * 20);
    }

    const mode = window.SIMULATION_MODE;

    if (mode === 'OFF') {
        return sequence;
    }

    const devicesToSimulate = mode === 'ALL' ? Object.keys(DEVICE_CONFIGS) : [mode];

    devicesToSimulate.forEach(device => {
        const config = DEVICE_CONFIGS[device];

        if (config.data) {
            const maxIndex = config.data.length;
            const startOff = config.startIndex;

            for (let i = 0; i < windowSize; i++) {
                const dataIndex = (startOff + timeIndex + i) % maxIndex;
                const normalizedPower = config.data[dataIndex][0];
                const realPower = normalizedPower * config.cutoff;
                sequence[i] += realPower;
            }
        }
    });

    timeIndex += 1;
    return sequence;
}

async function updateNILMStatus() {
    try {
        const powerData = getCurrentPowerSequence();

        const response = await fetch('/api/process_nilm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sequence: powerData })
        });

        const result = await response.json();

        if (result.status === "success") {
            const predictions = result.data;

            Object.keys(predictions).forEach(device => {
                const deviceData = predictions[device];
                const toggleElement = document.getElementById(`${device}-toggle`);
                const powerElement = document.getElementById(`${device}-power`);
                const cardElement = document.getElementById(`${device}-card`);

                if (toggleElement && powerElement) {
                    const aiIsOn = (deviceData.status === "ON");

                    toggleElement.checked = aiIsOn;
                    powerElement.innerText = `${deviceData.power}W`;

                    if (aiIsOn) {
                        cardElement.style.opacity = "1";
                    } else {
                        cardElement.style.opacity = "0.6";
                    }
                }
            });
        }
    } catch (error) {
    }
}

setInterval(updateNILMStatus, 6000);

// ==================================================
// 7. CHARTS & ANALYTICS
// ==================================================
let powerMiniChart;

function initPowerMiniChart() {
    const canvas = document.getElementById('powerMiniChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { willReadFrequently: true });

    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(236, 72, 153, 0.4)');
    gradient.addColorStop(1, 'rgba(236, 72, 153, 0)');

    powerMiniChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Power (W)',
                data: [],
                borderColor: '#ec4899',
                borderWidth: 3,
                pointRadius: 4,
                pointBackgroundColor: '#fff',
                fill: true,
                backgroundColor: gradient,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        label: function (context) { return `Power: ${context.parsed.y} W`; }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: { display: false },
                    ticks: { color: 'rgba(255,255,255,0.5)', font: { size: 10 } }
                },
                y: {
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: 'rgba(255,255,255,0.7)', font: { size: 12 }, padding: 10 }
                }
            }
        }
    });


}

function updateMiniChartUI(data) {
    try {
        const now = new Date().toLocaleTimeString();
        const livePowerEl = document.getElementById('livePowerValue');

        if (livePowerEl) {
            livePowerEl.innerText = data.power + ' W';
        }

        if (powerMiniChart) {
            powerMiniChart.data.labels.push(now);
            powerMiniChart.data.datasets[0].data.push(data.power);

            if (powerMiniChart.data.labels.length > 20) {
                powerMiniChart.data.labels.shift();
                powerMiniChart.data.datasets[0].data.shift();
            }
            powerMiniChart.update();
        }
    } catch (e) {
        console.error("Chart UI Error:", e);
    }
}


// ==================================================
// 8. SETTINGS, TIMER & NOTIFICATIONS SYNC
// ==================================================
window.currentBudgetKWh = 0;
window.consumedSinceBudget = 0;
window.activeBudgetDuration = 0;
window.budgetAlertsTriggered = { 50: false, 75: false, 100: false };
window.budgetInterval = null;

async function initSettings() {
    console.log("Loading Settings from Database...");
    
    if (window.activeEspId === window.mainMeterId) {
        window.location.href = '/dashboard'; 
        return;
    }

    try {
        const res = await fetch(`/api/get_user_settings?espid=${window.activeEspId}`);
        const data = await res.json();

        if (data.status === 'success') {
            const s = data.settings;

            if (document.getElementById('ww')) {
                document.getElementById('ww').innerText = parseFloat(s.current_limit || 50).toFixed(1);
            }

            if (document.getElementById('budget-kwh-display')) {
                document.getElementById('budget-kwh-display').innerText = parseFloat(s.budget_kwh || 0).toFixed(2);
            }

            window.currentBudgetKWh = parseFloat(s.budget_kwh || 0);

            if (document.getElementById('active-min-v')) {
                document.getElementById('active-min-v').innerText = s.min_voltage || 190;
            }
            if (document.getElementById('active-max-v')) {
                document.getElementById('active-max-v').innerText = s.max_voltage || 250;
            }
        }
    } catch (e) {
        console.error("Error loading settings:", e);
    }

    if (!window.timerSyncInterval) {
        window.timerSyncInterval = setInterval(syncTimerUI, 1000);
    }
}

window.checkSettingsAccess = function() {
    const activeId = parseInt(sessionStorage.getItem('activeEspId'));
    const mainId = parseInt(sessionStorage.getItem('mainMeterId'));
    
    const settingsLinks = document.querySelectorAll('a[href="/settings"]'); 
    
    if (isNaN(activeId) || activeId === 0 || activeId === mainId) {
        /* Apply lock class to the entire HTML document */
        document.documentElement.classList.add('settings-locked');
        
        settingsLinks.forEach(link => {
            if (link) {
                link.title = "Settings are locked for the Main Meter";
                link.onclick = (e) => e.preventDefault();
            }
        });
    } else {
        /* Remove lock class */
        document.documentElement.classList.remove('settings-locked');
        
        settingsLinks.forEach(link => {
            if (link) {
                link.removeAttribute('title');
                link.onclick = null;
            }
        });
    }
};

window.submitCurrentLimit = async function () {
    const val = document.getElementById('current-limit').value;
    if (!val) return alert("Please enter a value!");
    
    const activeId = sessionStorage.getItem('activeEspId');
    if (!activeId || activeId === "null") return alert("Error: No active device selected from Dashboard!");

    try {
        const res = await fetch('/api/update_user_settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_limit: parseFloat(val),
                espid: parseInt(activeId)
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            alert("Current Limit Saved Successfully!");
            document.getElementById('ww').innerText = val;
            document.getElementById('current-limit').value = '';
            
            if (!window.sysSettings) window.sysSettings = {};
            window.sysSettings.current_limit = parseFloat(val);
        } else {
            alert("Error: " + (data.message || "Failed to save."));
        }
    } catch (e) {
        alert("Connection Error.");
    }
};

window.calculateKWh = function () {
    const egpInput = document.getElementById('budget-egp').value;
    const displayElement = document.getElementById('budget-kwh-display');

    if (!egpInput || isNaN(egpInput) || parseFloat(egpInput) <= 0) {
        displayElement.innerText = "0.0";
        window.currentBudgetKWh = 0;
        return;
    }

    const egp = parseFloat(egpInput);
    let kwh = 0.0;

    const tierInput = document.getElementById('user-tariff-tier');
    const userTier = tierInput ? tierInput.value : "1";

    switch (userTier) {
        case "1": kwh = egp / 0.68; break;
        case "2": kwh = egp / 0.78; break;
        case "3": kwh = egp / 0.95; break;
        case "4": kwh = egp / 1.55; break;
        case "5": kwh = egp / 1.95; break;
        case "6": kwh = egp / 2.10; break;
        case "7": kwh = egp / 2.23; break;
        default: kwh = egp / 0.68; break;
    }

    window.currentBudgetKWh = kwh;
    displayElement.innerText = kwh.toFixed(2);
};

window.submitEnergyBudget = async function () {
    const egpInput = document.getElementById('budget-egp').value;
    const durationInput = document.getElementById('budget-duration').value;

    if (!egpInput || isNaN(egpInput) || window.currentBudgetKWh <= 0) {
        return alert("Please enter a valid budget amount in EGP!");
    }
    if (!durationInput || isNaN(durationInput) || parseFloat(durationInput) <= 0) {
        return alert("Please enter a valid duration in days!");
    }

    const payload = {
        egp: parseFloat(egpInput),
        kwh: window.currentBudgetKWh,
        days: parseFloat(durationInput),
        espid: window.activeEspId
    };

    try {
        const response = await fetch('/api/set_budget', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (data.status === 'success') {
            window.activeBudgetDuration = payload.days * 86400;
            window.consumedSinceBudget = 0;
            window.budgetAlertsTriggered = { 50: false, 75: false, 100: false };

            alert(`Budget saved successfully!\nEnergy: ${window.currentBudgetKWh.toFixed(2)} kWh\nDuration: ${durationInput} days.`);

            document.getElementById('budget-egp').value = '';
            document.getElementById('budget-duration').value = '';


        }
    } catch (error) {
        console.error("Save Error:", error);
    }
};

window.loadEnergyBudgetFromServer = async function () {
    try {
        const response = await fetch(`/api/get_budget?espid=${window.activeEspId}`);
        const data = await response.json();

        if (data && data.kwh > 0) {
            window.currentBudgetKWh = data.kwh;
            window.activeBudgetDuration = data.days * 86400;



        }
    } catch (error) {
        console.error("Load Error:", error);
    }
};

window.trackBudgetLocal = function (data) {
    if (window.currentBudgetKWh <= 0) return;

    try {
        const powerW = data.power || 0;
        const energyKWhPerInterval = (powerW / 1000) * (2.5 / 3600);

        window.consumedSinceBudget += energyKWhPerInterval;
        const percentageUsed = (window.consumedSinceBudget / window.currentBudgetKWh) * 100;

        if (percentageUsed >= 50 && !window.budgetAlertsTriggered[50]) {
            window.triggerSmartAlert('BUDGET ALERT', 'You have consumed 50% of your energy budget.', 'info');
            window.budgetAlertsTriggered[50] = true;
        }
        if (percentageUsed >= 75 && !window.budgetAlertsTriggered[75]) {
            window.triggerSmartAlert('BUDGET WARNING', 'You have consumed 75% of your energy budget. Consider reducing usage.', 'maintenance');
            window.budgetAlertsTriggered[75] = true;
        }
        if (percentageUsed >= 100 && !window.budgetAlertsTriggered[100]) {
            window.triggerSmartAlert('CRITICAL BUDGET LIMIT', 'You have reached 100% of your energy budget! Additional consumption is now unbudgeted.', 'error');
            window.budgetAlertsTriggered[100] = true;


        }

    } catch (e) {
        console.error("Budget Tracking Error:", e);
    }
};

window.onSetTimeClick = async function () {
    const min = document.getElementById('timer-duration').value;
    if (!min || isNaN(min)) return alert("Enter a valid duration in minutes!");

    await fetch('/set_timer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            duration_minutes: parseInt(min, 10),
            espid: window.activeEspId
        })
    });

    document.getElementById('timer-duration').value = '';
    syncTimerUI();
};

window.onPauseClick = async () => {
    const btn = document.getElementById('pause-btn');
    const isResume = btn.innerText.includes("Resume");
    const endpoint = isResume ? '/resume_timer' : '/pause_timer';

    try {
        await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ espid: window.activeEspId })
        });
        syncTimerUI();
    } catch (e) {
        console.error("Timer toggle error:", e);
    }
};

window.onCancelClick = async () => {
    window.sysTracker.timerActive = false;

    try {
        await fetch('/reset_timer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ espid: window.activeEspId })
        });
        syncTimerUI();
    } catch (e) {
        console.error("Timer reset error:", e);
    }
};

window.updateRemoteUI = function (state) {
    const onBtn = document.getElementById('on-btn');
    const offBtn = document.getElementById('off-btn');
    if (!onBtn || !offBtn) return;

    if (state === 'on') {
        onBtn.classList.add('active-on');
        offBtn.classList.remove('active-off');
    } else {
        offBtn.classList.add('active-off');
        onBtn.classList.remove('active-on');
    }
};

window.fetchDeviceState = async function () {
    try {
        const res = await fetch(`/control?espid=${window.activeEspId}`);
        const data = await res.json();

        if (data.command) {
            window.updateRemoteUI(data.command);
        }

        const onBtn = document.getElementById('on-btn');
        if (onBtn) {
            if (data.locked) {
                onBtn.disabled = true;
                onBtn.style.opacity = '0.4';
                onBtn.style.cursor = 'not-allowed';
            } else {
                onBtn.disabled = false;
                onBtn.style.opacity = '1';
                onBtn.style.cursor = 'pointer';
            }
        }
    } catch (e) {
        console.error("Failed to fetch device state", e);
    }
};

window.sendCommand = async (cmd) => {
    try {
        const response = await fetch('/set_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                command: cmd,
                espid: window.activeEspId
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            window.updateRemoteUI(cmd);
            alert(`Command Sent: ${cmd.toUpperCase()}`);
        } else {
            alert(`Error: ${data.message || 'Action failed'}`);
        }
    } catch (e) {
        console.error("Command Error:", e);
    }
};
async function syncTimerUI() {
    if (!window.activeEspId) return;
    const hEl = document.getElementById('hours');
    if (!hEl) return;

    try {
        const res = await fetch(`/get_timer?espid=${window.activeEspId}`);
        const data = await res.json();

        const remaining = data.remaining_seconds || 0;
        const isPaused = data.paused || false;

        const h = Math.floor(remaining / 3600);
        const m = Math.floor((remaining % 3600) / 60);
        const s = remaining % 60;

        if (hEl) {
            hEl.value = h.toString().padStart(2, '0');
            document.getElementById('minutes').value = m.toString().padStart(2, '0');
            document.getElementById('seconds').value = s.toString().padStart(2, '0');

            const setBtn = document.getElementById('set-time-btn');
            const pauseBtn = document.getElementById('pause-btn');
            const cancelBtn = document.getElementById('cancel-btn');

            if (remaining > 0 || isPaused) {
                if (setBtn) setBtn.style.display = 'none';
                if (pauseBtn) {
                    pauseBtn.style.display = 'inline-block';
                    pauseBtn.innerText = isPaused ? "Resume" : "Pause";
                }
                if (cancelBtn) cancelBtn.style.display = 'inline-block';

                if (remaining > 0 && !isPaused) window.sysTracker.timerActive = true;
            } else {
                if (setBtn) setBtn.style.display = 'inline-block';
                if (pauseBtn) pauseBtn.style.display = 'none';
                if (cancelBtn) cancelBtn.style.display = 'none';

                if (window.sysTracker.timerActive) {
                    window.sysTracker.timerActive = false;
                    if (window.activeEspId !== window.mainMeterId) {
                        window.triggerSmartAlert('TIMER COMPLETED', 'The scheduled timer has finished. Device power has been turned OFF.', 'maintenance');
                    }
                }
            }
        }
    } catch (e) {
        console.error("Timer Sync Error:", e);
    }
}

window.triggerSmartAlert = function (title, message, type) {
    window.addNotification(title, message, type, 'Just now');

    const container = document.getElementById('toast-container');
    if (!container) {
        const newContainer = document.createElement('div');
        newContainer.id = 'toast-container';
        document.body.appendChild(newContainer);
    }

    const toast = document.createElement('div');
    toast.className = `cyber-toast ${type}`;

    let iconClass = 'fa-solid fa-circle-info';
    if (type === 'error') iconClass = 'fa-solid fa-triangle-exclamation';
    else if (type === 'maintenance') iconClass = 'fa-solid fa-gear';

    toast.innerHTML = `
        <div class="toast-header">
            <span class="toast-title"><i class="${iconClass}"></i> ${title.toUpperCase()}</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">&times;</button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;

    document.getElementById('toast-container').appendChild(toast);
};

window.addNotification = function (title, message, type = 'info', timeAgo = 'Just now', id = null) {
    const list = document.getElementById('notification-list');
    const bell = document.querySelector('.fa-bell');

    if (list) {
        const li = document.createElement('li');

        let cardType = 'info';
        if (type === 'error') cardType = 'error';
        else if (type === 'maintenance') cardType = 'maintenance';

        li.className = `notif-card ${cardType}`;

        let iconClass = 'fa-solid fa-circle-info';
        if (type === 'error') iconClass = 'fa-solid fa-triangle-exclamation';
        else if (type === 'maintenance') iconClass = 'fa-solid fa-gear';

        li.innerHTML = `
            <div class="notif-icon-wrapper">
                <i class="${iconClass}"></i>
            </div>
            <div class="notif-content">
                <div class="notif-title">${title}</div>
                <div class="notif-desc">${message}</div>
                <div class="notif-time">${timeAgo}</div>
            </div>
            <button class="notif-close" onclick="event.stopPropagation(); window.dismissNotification('${id}', this);">
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;

        list.prepend(li);

        if (list.children.length > 50) {
            list.removeChild(list.lastChild);
        }

        if (bell) {
            bell.style.color = type === 'error' ? '#ec4899' : '#00f3ff';
            bell.style.filter = `drop-shadow(0 0 10px ${type === 'error' ? '#ec4899' : '#00f3ff'})`;
            setTimeout(() => {
                bell.style.color = '';
                bell.style.filter = '';
            }, 3000);
        }
    }
};

window.clearNotifications = function (event) {
    if (event) {
        event.stopPropagation();
    }

    const list = document.getElementById('notification-list');
    if (!list || list.children.length === 0) return;

    localStorage.setItem('notifsClearedAt', Date.now().toString());

    list.innerHTML = '';

    const bell = document.querySelector('.fa-bell');
    if (bell) {
        bell.style.color = '';
        bell.style.filter = '';
    }
};

window.dismissNotification = function (id, btnElement) {
    if (id && id !== 'null' && id !== 'undefined') {
        let dismissed = JSON.parse(localStorage.getItem('dismissedNotifs') || '[]');
        if (!dismissed.includes(String(id))) {
            dismissed.push(String(id));
            localStorage.setItem('dismissedNotifs', JSON.stringify(dismissed));
        }
    }

    if (btnElement && btnElement.parentElement) {
        btnElement.parentElement.remove();
    }
};

window.syncNotifications = async function () {
    try {
        const res = await fetch('/api/notifications');
        if (!res.ok) return;
        const notifs = await res.json();

        if (notifs && notifs.length > 0) {
            const lastSeenId = localStorage.getItem('last_notif_id');
            const clearedAt = parseInt(localStorage.getItem('notifsClearedAt') || '0');
            const dismissedIds = JSON.parse(localStorage.getItem('dismissedNotifs') || '[]');

            const validNotifs = notifs.filter(n => {
                const notifTime = n.created_at ? new Date(n.created_at).getTime() : 0;
                return notifTime > clearedAt && !dismissedIds.includes(String(n.id));
            });

            let newNotifs = [];
            for (let n of validNotifs) {
                if (String(n.id) === String(lastSeenId)) break;
                newNotifs.push(n);
            }

            if (!lastSeenId && newNotifs.length > 0) {
                newNotifs = [validNotifs[0]];
            }

            // Trigger Toasts only for new notifications
            newNotifs.reverse().forEach(n => {
                if (typeof window.triggerSmartAlert === 'function') {
                    window.triggerSmartAlert(n.title, n.message, n.type);
                }
            });

            if (validNotifs.length > 0) {
                localStorage.setItem('last_notif_id', validNotifs[0].id);
            }

            // Handle UI List rendering independently from newNotifs
            const list = document.getElementById('notification-list');
            if (list) {
                if (list.children.length === 0) {
                    // Initial load: render all valid notifications
                    list.innerHTML = '';
                    validNotifs.slice().reverse().forEach(n => {
                        if (typeof window.addNotification === 'function') {
                            let timeStr = n.created_at ? new Date(n.created_at).toLocaleTimeString() : 'Just now';
                            window.addNotification(n.title, n.message, n.type, timeStr, n.id);
                        }
                    });
                } else if (newNotifs.length > 0) {
                    // Subsequent polls: append only new notifications to avoid UI flickering
                    newNotifs.forEach(n => {
                        if (typeof window.addNotification === 'function') {
                            let timeStr = n.created_at ? new Date(n.created_at).toLocaleTimeString() : 'Just now';
                            window.addNotification(n.title, n.message, n.type, timeStr, n.id);
                        }
                    });
                }
            }
        }
    } catch (e) {
        console.error("Notif Sync Error:", e);
    }
};

function initNotifications() {
    const bell = document.querySelector('.fa-bell');
    const popup = document.getElementById('notification-popup');
    const profileDropdown = document.getElementById('profile-dropdown');

    if (bell && popup) {
        bell.addEventListener('click', (e) => {
            e.stopPropagation();
            popup.style.display = (popup.style.display === 'none' || popup.style.display === '') ? 'block' : 'none';

            if (profileDropdown && popup.style.display === 'block') {
                profileDropdown.style.display = 'none';
            }
        });
    }
}

window.toggleNotificationPopup = function () {
    const popup = document.getElementById('notification-popup');
    if (popup) {
        popup.style.display = (popup.style.display === 'none' || popup.style.display === '') ? 'block' : 'none';
    }
};

window.submitVoltageLimits = async function () {
    const minV = document.getElementById('min-voltage').value;
    const maxV = document.getElementById('max-voltage').value;

    if (!minV || !maxV) return alert("Please enter both min and max values!");

    const res = await fetch('/api/update_user_settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            min_voltage: parseFloat(minV),
            max_voltage: parseFloat(maxV),
            espid: window.activeEspId
        })
    });

    if ((await res.json()).status === 'success') {
        alert("Voltage Limits Saved!");

        if (!window.sysSettings) window.sysSettings = {};
        window.sysSettings.min_voltage = parseFloat(minV);
        window.sysSettings.max_voltage = parseFloat(maxV);

        document.getElementById('active-min-v').innerText = minV;
        document.getElementById('active-max-v').innerText = maxV;

        document.getElementById('min-voltage').value = '';
        document.getElementById('max-voltage').value = '';
    }
};

// ==================================================
// 9. AUTHENTICATION
// ==================================================
function initAuth() {
    console.log("Initializing Auth Page...");

    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('loginBtn');
            const errorDiv = document.getElementById('loginError');
            const successDiv = document.getElementById('loginSuccess');

            btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> AUTHENTICATING...';
            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: document.getElementById('loginEmail').value,
                        password: document.getElementById('loginPassword').value
                    })
                });

                const data = await res.json();

                if (data.status === 'success') {
                    successDiv.innerText = "Access Granted. Redirecting...";
                    successDiv.style.display = 'block';
                    setTimeout(() => { window.location.href = data.redirect; }, 1000);
                } else {
                    errorDiv.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${data.message}`;
                    errorDiv.style.display = 'block';
                    btn.innerHTML = 'login';
                }
            } catch (err) {
                errorDiv.innerText = 'Connection Error. Please check your network.';
                errorDiv.style.display = 'block';
                btn.innerHTML = 'login';
            }
        });
    }

    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('signupBtn');
            const errorDiv = document.getElementById('signupError');

            btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> PROCESSING...';
            errorDiv.style.display = 'none';

            try {
                const res = await fetch('/api/signup_send_otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: document.getElementById('signupName').value,
                        email: document.getElementById('signupEmail').value,
                        password: document.getElementById('signupPassword').value
                    })
                });

                const data = await res.json();

                if (data.status === 'success') {
                    document.getElementById('signupForm').style.display = 'none';
                    document.getElementById('signupSocialDivider').style.display = 'none';
                    document.getElementById('signupSocialGroup').style.display = 'none';
                    document.getElementById('signupToggleText').style.display = 'none';
                    document.getElementById('signupOtpSection').style.display = 'block';
                } else {
                    errorDiv.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${data.message}`;
                    errorDiv.style.display = 'block';
                }
            } catch (err) {
                errorDiv.innerText = 'Connection Error. Please check your network.';
                errorDiv.style.display = 'block';
            }
            btn.innerHTML = 'Register';
        });
    }
}

window.verifySignupOTP = async function () {
    const code = document.getElementById('signupOtpCode').value;
    const btn = document.getElementById('verifySignupBtn');
    const errorDiv = document.getElementById('signupError');
    const successDiv = document.querySelector('.front #loginSuccess');

    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> VERIFYING...';
    errorDiv.style.display = 'none';

    try {
        const res = await fetch('/api/signup_verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        const data = await res.json();

        if (data.status === 'success') {
            cancelSignupOTP();
            toggleAuth();
            if (successDiv) {
                successDiv.innerText = "Registration successful. Please login.";
                successDiv.style.display = 'block';
            }
        } else {
            errorDiv.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${data.message}`;
            errorDiv.style.display = 'block';
        }
    } catch (err) {
        errorDiv.innerText = 'Connection Error.';
        errorDiv.style.display = 'block';
    }
    btn.innerHTML = 'VERIFY CODE';
};

window.cancelSignupOTP = function () {
    document.getElementById('signupOtpSection').style.display = 'none';
    document.getElementById('signupForm').style.display = 'block';
    document.getElementById('signupSocialDivider').style.display = 'flex';
    document.getElementById('signupSocialGroup').style.display = 'flex';
    document.getElementById('signupToggleText').style.display = 'block';
    document.getElementById('signupOtpCode').value = '';
    const errorDiv = document.getElementById('signupError');
    if (errorDiv) errorDiv.style.display = 'none';
};

window.toggleAuth = function () {
    const authCard = document.getElementById('authCard');
    if (authCard) {
        authCard.classList.toggle('flip');

        document.querySelectorAll('.error-msg, .success-msg').forEach(el => el.style.display = 'none');

        const loginForm = document.getElementById('loginForm');
        const signupForm = document.getElementById('signupForm');
        if (loginForm) loginForm.reset();
        if (signupForm) signupForm.reset();

        if (typeof cancelSignupOTP === 'function') {
            cancelSignupOTP();
        }
    }
};

window.togglePasswordVisibility = function (inputId, iconElement) {
    const inputField = document.getElementById(inputId);
    if (inputField.type === "password") {
        inputField.type = "text";
        inputField.classList.add("password-visible");
        iconElement.classList.remove("fa-eye-slash");
        iconElement.classList.add("fa-eye");
    } else {
        inputField.type = "password";
        inputField.classList.remove("password-visible");
        iconElement.classList.remove("fa-eye");
        iconElement.classList.add("fa-eye-slash");
    }
};

window.openResetOverlay = () => document.getElementById('resetOverlay').classList.add('active');
window.closeResetOverlay = () => document.getElementById('resetOverlay').classList.remove('active');

async function sendOTP() {
    const email = document.getElementById('resetEmail').value;
    const res = await fetch('/api/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
    });
    const data = await res.json();
    if (data.status === 'success') {
        document.getElementById('step1').style.display = 'none';
        document.getElementById('step2').style.display = 'block';
        document.getElementById('resetSub').innerText = "ENTER VERIFICATION CODE";
    } else {
        alert(data.message);
    }
}

async function verifyOTP() {
    const code = document.getElementById('otpCode').value;
    const res = await fetch('/api/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
    });
    const data = await res.json();
    if (data.status === 'success') {
        document.getElementById('step2').style.display = 'none';
        document.getElementById('step3').style.display = 'block';
        document.getElementById('resetSub').innerText = "SET NEW PASSWORD";
    } else {
        alert("Invalid Code");
    }
}

async function updatePassword() {
    const password = document.getElementById('newPass').value;
    const email = document.getElementById('resetEmail').value;
    const res = await fetch('/api/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (data.status === 'success') {
        alert("Password Updated Successfully!");
        location.reload();
    } else {
        alert("Error: " + (data.message || "Failed to reset password."));
    }
}

// ==================================================
// 10. PROFILE & CONFIGURATION
// ==================================================
async function uploadAvatar(event) {
    const file = event.target.files[0];
    if (!file) return;

    document.body.style.cursor = 'wait';

    const reader = new FileReader();
    reader.onload = function (e) {
        const img = new Image();
        img.onload = async function () {
            const canvas = document.createElement('canvas');
            const MAX_WIDTH = 250;
            const MAX_HEIGHT = 250;
            let width = img.width;
            let height = img.height;

            if (width > height) {
                if (width > MAX_WIDTH) {
                    height *= MAX_WIDTH / width;
                    width = MAX_WIDTH;
                }
            } else {
                if (height > MAX_HEIGHT) {
                    width *= MAX_HEIGHT / height;
                    height = MAX_HEIGHT;
                }
            }

            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d', { willReadFrequently: true });
            ctx.drawImage(img, 0, 0, width, height);

            const compressedBase64 = canvas.toDataURL('image/jpeg', 0.8);

            try {
                const response = await fetch('/api/update_avatar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ avatar_url: compressedBase64 })
                });

                const data = await response.json();
                if (data.status === 'success') {
                    const profileImg = document.getElementById('profile-img-display');
                    const profileImgBackup = document.getElementById('profile-img');

                    if (profileImg) profileImg.src = compressedBase64;
                    if (profileImgBackup) profileImgBackup.src = compressedBase64;

                    const navAvatar = document.querySelector('.nav-avatar');
                    if (navAvatar) {
                        navAvatar.src = compressedBase64;
                    } else {
                        const iconCircle = document.querySelector('.icon-circle a[href="/profile"]');
                        if (iconCircle) iconCircle.innerHTML = `<img src="${compressedBase64}" alt="User" class="nav-avatar">`;
                    }
                } else {
                    alert("Error: " + data.message);
                }
            } catch (err) {
                console.error("Network Error:", err);
                alert("Connection issue with the server");
            } finally {
                document.body.style.cursor = 'default';
            }
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

async function updateProfileSettings() {
    const newName = document.getElementById('edit-username').value.trim();
    const newPass = document.getElementById('edit-password').value;
    const confirmPass = document.getElementById('confirm-password').value;
    const msgDiv = document.getElementById('profile-msg');

    if (!newName) {
        msgDiv.style.display = 'block';
        msgDiv.style.color = '#ff4d4d';
        msgDiv.innerText = "Username cannot be empty!";
        return;
    }

    if (newPass && newPass !== confirmPass) {
        msgDiv.style.display = 'block';
        msgDiv.style.color = '#ff4d4d';
        msgDiv.innerText = "Passwords do not match!";
        return;
    }

    const payload = { name: newName };
    if (newPass) payload.password = newPass;

    try {
        const response = await fetch('/api/update_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        msgDiv.style.display = 'block';

        if (data.status === 'success') {
            msgDiv.style.color = '#4ade80';
            msgDiv.innerText = "Profile updated successfully!";

            const headerName = document.querySelector('.neon-header');
            if (headerName) headerName.innerText = newName;

            document.getElementById('edit-password').value = '';
            document.getElementById('confirm-password').value = '';
        } else {
            msgDiv.style.color = '#ff4d4d';
            msgDiv.innerText = "Error: " + data.message;
        }
    } catch (err) {
        msgDiv.style.display = 'block';
        msgDiv.style.color = '#ff4d4d';
        msgDiv.innerText = "Connection Error. Please check your network.";
    }
}

async function saveSystemConfig() {
    const config = {
        tariff: document.getElementById('tariff-type').value,
        appliances: document.getElementById('total-appliances').value,
        schedule: document.getElementById('usage-schedule').value,
        budget: document.getElementById('monthly-budget-input').value
    };

    const response = await fetch('/api/save_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });

    if (response.ok) alert("System Updated!");
}

async function confirmDeleteAccount() {
    const confirmation = await cyberConfirm("WARNING: Are you sure you want to PERMANENTLY delete your account? This action cannot be undone.");

    if (confirmation) {
        try {
            const response = await fetch('/api/delete_account', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (data.status === 'success') {
                alert("Your account has been successfully removed. Redirecting...");
                window.location.href = '/auth';
            } else {
                alert("Error: " + data.message);
            }
        } catch (err) {
            console.error("Deletion Error:", err);
            alert("Connection error. Could not delete account.");
        }
    }
}

window.updateTierPrice = function () {
    const tier = document.getElementById('tariff-type');
    if (!tier) return;

    const val = tier.value;
    const priceDisplay = document.getElementById('tier-price-display');
    const detailsDisplay = document.getElementById('tier-details-display');

    let price = "";
    let details = "";

    switch (val) {
        case "1":
            price = "0.68 EGP / kWh";
            details = "Calculation: Normal calculation for consumption from 0 to 50 kWh.";
            break;
        case "2":
            price = "0.78 EGP / kWh";
            details = "Calculation: Calculated for consumption from 51 to 100 kWh.";
            break;
        case "3":
            price = "0.95 EGP / kWh";
            details = "Calculation: Calculated from zero for the entire amount (0 - 200 kWh).";
            break;
        case "4":
            price = "1.55 EGP / kWh";
            details = "Calculation: Calculated for consumption from 201 to 350 kWh.";
            break;
        case "5":
            price = "1.95 EGP / kWh";
            details = "Calculation: Calculated for consumption from 351 to 650 kWh.";
            break;
        case "6":
            price = "2.10 EGP / kWh";
            details = "Calculation: Calculated from zero for the entire amount (0 - 1000 kWh).";
            break;
        case "7":
            price = "2.23 EGP / kWh";
            details = "Calculation: Calculated from zero for the entire amount (exceeding 1000 kWh).";
            break;
    }

    if (priceDisplay) priceDisplay.innerText = "Price: " + price;
    if (detailsDisplay) detailsDisplay.innerText = details;
};

// ==================================================
// 11. COMMUNITY HUB LOGIC
// ==================================================
async function submitPost() {
    const contentInput = document.getElementById('new-post-content');
    if (!contentInput) return;
    const content = contentInput.value.trim();
    if (!content) return;

    document.body.style.cursor = 'wait';
    try {
        const response = await fetch('/api/create_post', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content })
        });
        const data = await response.json();
        if (data.status === 'success') window.location.reload();
        else alert("Error: " + data.message);
    } catch (err) {
        alert("Connection Error");
    } finally {
        document.body.style.cursor = 'default';
    }
}

async function submitComment(postId) {
    const commentInput = document.getElementById(`comment-input-${postId}`);
    if (!commentInput) return;
    const content = commentInput.value.trim();
    if (!content) return;

    document.body.style.cursor = 'wait';
    try {
        const response = await fetch('/api/add_comment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ post_id: postId, content: content })
        });
        const data = await response.json();
        if (data.status === 'success') window.location.reload();
        else alert("Error: " + data.message);
    } catch (err) {
        console.error("Comment Error:", err);
    } finally {
        document.body.style.cursor = 'default';
    }
}

function enableEditMode(postId) {
    document.getElementById(`post-content-${postId}`).style.display = 'none';
    document.getElementById(`edit-box-${postId}`).style.display = 'block';
}

function cancelEdit(postId) {
    document.getElementById(`post-content-${postId}`).style.display = 'block';
    document.getElementById(`edit-box-${postId}`).style.display = 'none';
}

async function saveEdit(postId) {
    const newContent = document.getElementById(`edit-input-${postId}`).value.trim();
    if (!newContent) return;

    document.body.style.cursor = 'wait';
    try {
        const response = await fetch('/api/edit_post', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ post_id: postId, content: newContent })
        });
        const data = await response.json();
        if (data.status === 'success') window.location.reload();
        else alert("Error: " + data.message);
    } catch (err) {
        alert("Connection Error");
    } finally {
        document.body.style.cursor = 'default';
    }
}

async function deletePost(postId) {
    if (!(await cyberConfirm("Are you sure you want to delete this post?"))) return;

    document.body.style.cursor = 'wait';
    try {
        const response = await fetch('/api/delete_post', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ post_id: postId })
        });
        const data = await response.json();
        if (data.status === 'success') window.location.reload();
        else alert("Error: " + data.message);
    } catch (err) {
        alert("Connection Error");
    } finally {
        document.body.style.cursor = 'default';
    }
}

function toggleSendButton(postId) {
    const input = document.getElementById(`comment-input-${postId}`);
    const btn = document.getElementById(`send-btn-${postId}`);

    if (input && btn) {
        btn.style.display = input.value.trim().length > 0 ? 'block' : 'none';
    }
}

async function deleteComment(commentId) {
    if (!(await cyberConfirm("Delete this log entry?"))) return;

    document.body.style.cursor = 'wait';
    try {
        const response = await fetch('/api/delete_comment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ comment_id: commentId })
        });
        const data = await response.json();
        if (data.status === 'success') window.location.reload();
        else alert("Error: " + data.message);
    } catch (err) {
        alert("Connection Error");
    } finally {
        document.body.style.cursor = 'default';
    }
}

async function viewMyPosts() {
    const container = document.getElementById('my-posts-container');
    const list = document.getElementById('my-posts-list');

    if (container.style.display === 'block') {
        container.style.display = 'none';
        return;
    }

    list.innerHTML = '<p style="color: #00f3ff; text-align: center;">Retrieving data from network...</p>';
    container.style.display = 'block';

    try {
        const response = await fetch('/api/my_posts');
        const data = await response.json();

        if (data.status === 'success') {
            if (data.posts.length === 0) {
                list.innerHTML = '<p style="color: #94a3b8; text-align: center; padding: 20px;">No transmissions found in your logs.</p>';
                return;
            }

            list.innerHTML = '';
            data.posts.forEach(post => {
                const postElement = document.createElement('div');
                postElement.className = 'card glass-card post-card';
                postElement.style.marginBottom = '15px';
                postElement.style.padding = '20px';

                postElement.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <img src="${post.users.avatar_url || '/static/images/logo.png'}" class="nav-avatar" style="width: 35px; height: 35px; margin-right: 12px;">
                            <div>
                                <h4 style="margin: 0; color: #00f3ff; font-size: 0.9rem;">${post.users.name}</h4>
                                <span style="font-size: 0.7rem; color: #94a3b8;">${post.created_at.substring(0, 16).replace('T', ' ')}</span>
                            </div>
                        </div>
                        <button onclick="deletePost('${post.id}')" style="background:none; border:none; color:#ff4d4d; cursor:pointer;">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                    <p style="color: #fff; line-height: 1.5; font-size: 0.95rem; margin-top: 10px;">${post.content}</p>
                `;
                list.appendChild(postElement);
            });

            container.scrollIntoView({ behavior: 'smooth' });
        } else {
            list.innerHTML = `<p style="color: #ff4d4d;">Error: ${data.message}</p>`;
        }
    } catch (err) {
        list.innerHTML = '<p style="color: #ff4d4d;">Failed to connect to the server.</p>';
    }
}

// ==================================================
// 12. CONTACT PAGE LOGIC
// ==================================================
function initContact() {
    const form = document.getElementById('contactForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const json = Object.fromEntries(formData.entries());

            try {
                const res = await fetch('/contact_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(json)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    alert("Message Sent Successfully!");
                    form.reset();
                } else {
                    alert("Error sending message.");
                }
            } catch (err) { alert("Network Error"); }
        });
    }
}

// ==================================================
// SENTRA SYSTEM - ANALYTICS MODULE
// ==================================================

let myHistoricalChart = null;
let myDonutChart = null;
let myCarbonComparison = null;
let myAICostChart = null;
let reportChartInstance = null;

// Helper to secure and retrieve User ID from global scope
window.getUserId = function() {
    if (typeof window.currentUserId === 'undefined' || window.currentUserId === 'None' || window.currentUserId === '') {
        console.error("User ID is missing. Cannot fetch analytics data.");
        return null;
    }
    return window.currentUserId;
};

// Safe text content updater to prevent template crashes
function safeTxt(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

// Render empty structural charts on load to preserve UI borders
window.renderEmptyCharts = function() {
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { display: false } },
            y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { display: false }, beginAtZero: true }
        }
    };

    const ctxLine = document.getElementById('historicalChart');
    if (ctxLine && !myHistoricalChart) {
        myHistoricalChart = new Chart(ctxLine.getContext('2d'), { 
            type: 'line', 
            data: { labels: [], datasets: [] }, 
            options: defaultOptions 
        });
    }

    const ctxDonut = document.getElementById('devicesDonutChart');
    if (ctxDonut && !myDonutChart) {
        myDonutChart = new Chart(ctxDonut.getContext('2d'), { 
            type: 'doughnut', 
            data: { labels: [], datasets: [] }, 
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: { legend: { display: false } } 
            } 
        });
    }

    const ctxCarbon = document.getElementById('carbonComparisonChart');
    if (ctxCarbon && !myCarbonComparison) {
        myCarbonComparison = new Chart(ctxCarbon.getContext('2d'), { 
            type: 'bar', 
            data: { labels: [], datasets: [] }, 
            options: defaultOptions 
        });
    }

    const ctxAICost = document.getElementById('aiCostComparisonChart');
    if (ctxAICost && !myAICostChart) {
        myAICostChart = new Chart(ctxAICost.getContext('2d'), { 
            type: 'bar', 
            data: { labels: [], datasets: [] }, 
            options: defaultOptions 
        });
    }
};

// Initialize Analytics View
window.initAnalytics = function() {
    console.log("Initializing Analytics Dashboard...");
    const dailyTab = document.querySelector('.tabs .tab');
    if (!dailyTab) return;

    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    dailyTab.classList.add('active');

    // Trigger the empty frames immediately to preserve the Cyberpunk look
    window.renderEmptyCharts();

    setTimeout(() => {
        if (typeof window.generateReport === 'function') {
            window.generateReport('daily', dailyTab);
        }
    }, 300);
};

// Tab switcher and periodic report generator (Daily, Weekly, Monthly, Yearly)
window.generateReport = async function(type, btnElement) {
    if (btnElement) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        btnElement.classList.add('active');

        const underline = document.getElementById('tabUnderline');
        if (underline) {
            underline.style.width = btnElement.offsetWidth + "px";
            underline.style.left = btnElement.offsetLeft + "px";
        }
    }

    const titleEl = document.getElementById('reportTitle');
    if (titleEl) titleEl.innerText = "Loading Summary...";

    const uid = window.getUserId();
    if (!uid) return;

    try {
        const response = await fetch(`/report/${type}?user_id=${uid}`);
        if (!response.ok) throw new Error(`Server Error: ${response.status}`);
        const data = await response.json();

        // Update UI metrics inside the summary panels
        safeTxt('totalConsumption', (data.total_consumption || 0).toFixed(2) + ' kWh');
        safeTxt('totalCost', (data.total_cost || 0).toFixed(2) + ' EGP');
        safeTxt('peakConsumption', (data.peak_consumption || 0).toFixed(2) + ' W');

        let titleText = type.charAt(0).toUpperCase() + type.slice(1);
        safeTxt('reportTitle', titleText + ' Summary');

        // Render Periodic Report Chart
        const canvas = document.getElementById('reportChart');
        if (canvas) {
            const ctx = canvas.getContext('2d', { willReadFrequently: true });

            if (window.reportChartInstance) {
                window.reportChartInstance.destroy();
            }

            let gradientBlue = ctx.createLinearGradient(0, 0, 0, 400);
            gradientBlue.addColorStop(0, 'rgba(0, 255, 255, 0.5)');
            gradientBlue.addColorStop(1, 'rgba(0, 255, 255, 0.0)');

            let gradientPink = ctx.createLinearGradient(0, 0, 0, 400);
            gradientPink.addColorStop(0, 'rgba(255, 0, 255, 0.5)');
            gradientPink.addColorStop(1, 'rgba(255, 0, 255, 0.0)');

            window.reportChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: 'Total Consumption (kWh)',
                            data: data.values_total,
                            borderColor: '#00ffff',
                            backgroundColor: gradientBlue,
                            fill: true,
                            tension: 0.2,
                            pointBackgroundColor: '#fff',
                            pointBorderColor: '#00ffff',
                            pointRadius: 4,
                            borderWidth: 2
                        },
                        {
                            label: 'Peak Power (W)',
                            data: data.values_peak,
                            borderColor: '#ff00ff',
                            backgroundColor: gradientPink,
                            fill: true,
                            tension: 0.2,
                            pointBackgroundColor: '#fff',
                            pointBorderColor: '#ff00ff',
                            pointRadius: 4,
                            borderWidth: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, labels: { color: '#fff' } }
                    },
                    scales: {
                        y: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#ccc' } },
                        x: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#ccc' } }
                    }
                }
            });
        }
    } catch (e) {
        console.error("Report Fetching Error:", e);
        safeTxt('reportTitle', "Error Loading Data");
    }
};

// Fetch historical data range from Supabase backend using filters
window.fetchSentraData = async function() {
    const start = document.getElementById('start-date').value;
    const end = document.getElementById('end-date').value;
    const btn = document.getElementById('hist-btn');

    if (!start || !end) {
        alert("Please select both start and end dates first!");
        return;
    }

    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading Data...';
    btn.disabled = true;

    try {
        const userId = window.getUserId();
        // Replace the space with 'T' to match the ISO format in the database
        const url = `/api/readings/history?start=${encodeURIComponent(start + 'T00:00:00')}&end=${encodeURIComponent(end + 'T23:59:59')}&user_id=${encodeURIComponent(userId)}`;
        
        const response = await fetch(url);
        if (!response.ok) throw new Error("Server rejected historical query");

        const data = await response.json();

        if (!data || data.length === 0) {
            alert("No data available for the selected period.");
            safeTxt('hist-peak-load', '-- W');
            safeTxt('hist-peak-time', '--:--');
            safeTxt('hist-present-load', '-- W');
            safeTxt('hist-present-time', '--:--');
            safeTxt('hist-carbon-val', '-- Tons');
            safeTxt('hist-occupancy-val', '--%');
            document.getElementById('occupancy-circle').style.background = `conic-gradient(#6366f1 0%, rgba(255,255,255,0.1) 0%)`;
            
            if (myHistoricalChart) myHistoricalChart.destroy();
            if (myDonutChart) myDonutChart.destroy();
            if (myCarbonComparison) myCarbonComparison.destroy();
            if (myAICostChart) myAICostChart.destroy();
            
            document.getElementById('ai-tips-container').innerHTML = '<p style="color: #94a3b8;">Not enough historical data for system recommendations.</p>';
            return;
        }

        let maxPower = 0;
        let minPower = Infinity;
        let peakTimestamp = "";
        let totalPowerSum = 0;

        let lastRecord = data[data.length - 1];
        let presentPower = parseFloat(lastRecord.power) || 0;
        let presentTimestamp = lastRecord.timestamp;

        data.forEach(item => {
            let p = parseFloat(item.power) || 0;
            totalPowerSum += p;

            if (p > maxPower) {
                maxPower = p;
                peakTimestamp = item.timestamp;
            }
            if (p < minPower) {
                minPower = p;
            }
        });

        if (minPower === Infinity) minPower = 0;

        const formatTimeOnly = (ts) => {
            if (!ts) return "--:--";
            let clean = ts.replace(' ', 'T');
            let d = new Date(clean);
            if (isNaN(d)) d = new Date(clean.split('.')[0] + 'Z');
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        };

        safeTxt('hist-peak-load', maxPower.toFixed(1) + ' W');
        safeTxt('hist-peak-time', formatTimeOnly(peakTimestamp));
        safeTxt('hist-present-load', presentPower.toFixed(1) + ' W');
        safeTxt('hist-present-time', formatTimeOnly(presentTimestamp));

        // Calculate Carbon Footprint parameters
        let total_kWh = (totalPowerSum / 1000) * (2 / 3600);
        let carbon_kg = total_kWh * 0.45;
        let carbon_tons = carbon_kg / 1000;

        if (carbon_tons >= 1) {
            safeTxt('hist-carbon-val', carbon_tons.toFixed(2) + ' Tons');
        } else if (carbon_kg >= 1) {
            safeTxt('hist-carbon-val', carbon_kg.toFixed(2) + ' Kg');
        } else {
            safeTxt('hist-carbon-val', (carbon_kg * 1000).toFixed(1) + ' g');
        }

        // Calculate active occupancy percentage based on noise threshold
        let activeThreshold = minPower + 100;
        let activeReadings = 0;

        data.forEach(item => {
            let p = parseFloat(item.power) || 0;
            if (p > activeThreshold) activeReadings++;
        });

        let occupancyPercentage = data.length > 0 ? Math.round((activeReadings / data.length) * 100) : 0;
        safeTxt('hist-occupancy-val', occupancyPercentage + '%');
        document.getElementById('occupancy-circle').style.background = `conic-gradient(#6366f1 ${occupancyPercentage}%, rgba(255,255,255,0.1) ${occupancyPercentage}%)`;

        // Trigger multi-chart updates
        window.updateCharts(data);

    } catch (error) {
        console.error("Historical Grid Error:", error);
        alert("Failed to retrieve historical matrix: " + error.message);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};

// Render trend, donut distributions, carbon metrics, and optimization bar charts
window.updateCharts = function(data) {
    // 1. Core Consumption Trend Chart (Line)
    // Dynamic step to prevent over-filtering small datasets
    const step = Math.max(1, Math.floor(data.length / 50));
    const filteredData = data.filter((_, index) => index % step === 0);
    
    const labels = filteredData.map(item => {
        let cleanTimestamp = item.timestamp.replace(' ', 'T');
        let dateObj = new Date(cleanTimestamp);
        if (isNaN(dateObj)) dateObj = new Date(cleanTimestamp.split('.')[0] + 'Z');
        return dateObj.toLocaleString([], { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    });
    
    // Parse power safely to ensure numerical values
    const powerValues = filteredData.map(item => parseFloat(item.power) || 0);

    const ctxLine = document.getElementById('historicalChart').getContext('2d');
    if (myHistoricalChart) myHistoricalChart.destroy();

    let gradientBlue = ctxLine.createLinearGradient(0, 0, 0, 400);
    gradientBlue.addColorStop(0, 'rgba(0, 243, 255, 0.6)');
    gradientBlue.addColorStop(1, 'rgba(0, 243, 255, 0.0)');

    myHistoricalChart = new Chart(ctxLine, {
        type: 'line',
        data: { 
            labels: labels, 
            datasets: [{ 
                label: 'Power Consumption (Watts)', 
                data: powerValues, 
                borderColor: '#00f3ff', 
                backgroundColor: gradientBlue, 
                borderWidth: 2, 
                fill: true, 
                tension: 0.4, 
                // Show points if the dataset is very small, otherwise hide them for clean lines
                pointRadius: filteredData.length <= 1 ? 4 : 0 
            }] 
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false, 
            interaction: { mode: 'index', intersect: false }, 
            plugins: { 
                tooltip: { backgroundColor: 'rgba(10, 15, 30, 0.9)', titleColor: '#ffffff', bodyColor: '#00f3ff', borderColor: '#bb13fe', borderWidth: 1, padding: 10 }, 
                legend: { labels: { color: '#ffffff' } } 
            }, 
            scales: { 
                x: { ticks: { color: '#a0a0c0', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } }, 
                y: { beginAtZero: true, ticks: { color: '#00f3ff' }, grid: { color: 'rgba(255,255,255,0.05)' } } 
            } 
        }
    });

    // 2. Disaggregated Device Distribution Chart (Doughnut)
    const deviceConsumption = {};
    data.forEach(item => {
        const device = item.device_name || 'Unknown';
        
        // Skip the main meter from individual device charts
        if (device.toUpperCase() !== 'TOTAL (MAIN)') {
            const power = parseFloat(item.power) || 0;
            deviceConsumption[device] = (deviceConsumption[device] || 0) + power;
        }
    });

    const ctxDonut = document.getElementById('devicesDonutChart').getContext('2d');
    if (myDonutChart) myDonutChart.destroy();
    myDonutChart = new Chart(ctxDonut, {
        type: 'doughnut',
        data: { labels: Object.keys(deviceConsumption), datasets: [{ data: Object.values(deviceConsumption), backgroundColor: ['#00f3ff', '#bb13fe', '#ff0055', '#4F46E5'], borderColor: 'rgba(10, 15, 30, 1)', borderWidth: 3 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { position: 'right', labels: { color: '#ffffff', font: { size: 12 } } } } }
    });

    // 3. Carbon Footprint Impact Mitigation Chart (Horizontal Bar)
    const deviceNamesArr = Object.keys(deviceConsumption);
    const beforeCarbon = deviceNamesArr.map(d => -((deviceConsumption[d] / 1000) * (2 / 3600) * 0.45));
    const afterCarbon = deviceNamesArr.map(d => ((deviceConsumption[d] / 1000) * (2 / 3600) * 0.45) * 0.85);

    const ctxCarbon = document.getElementById('carbonComparisonChart').getContext('2d');
    if (myCarbonComparison) myCarbonComparison.destroy();
    myCarbonComparison = new Chart(ctxCarbon, {
        type: 'bar',
        data: {
            labels: deviceNamesArr,
            datasets: [
                { label: 'Current Carbon', data: beforeCarbon, backgroundColor: '#8b5cf6', borderWidth: 0, borderRadius: 4, barThickness: 45 },
                { label: 'Optimized Carbon', data: afterCarbon, backgroundColor: '#10b981', borderWidth: 0, borderRadius: 4, barThickness: 45 }
            ]
        },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top', labels: { color: '#ffffff', font: { size: 14 } } } }, scales: { x: { stacked: true }, y: { stacked: true } } }
    });

    // 4. AI Cost Optimization Projection Matrix (Double Vertical Bar)
    const aiDevices = Object.keys(deviceConsumption);
    const currentCosts = aiDevices.map(d => ((deviceConsumption[d] / 1000) * (2 / 3600)) * 1.50);
    const optimizedCosts = currentCosts.map(c => c * 0.75);
    const originalSavingsEffect = {};
    aiDevices.forEach((d, i) => originalSavingsEffect[d] = currentCosts[i] * 0.25);

    const ctxAICost = document.getElementById('aiCostComparisonChart').getContext('2d');
    if (myAICostChart) myAICostChart.destroy();
    myAICostChart = new Chart(ctxAICost, {
        type: 'bar',
        data: {
            labels: aiDevices,
            datasets: [
                { label: 'Current Cost (EGP)', data: currentCosts, backgroundColor: '#8b5cf6', borderRadius: 4 },
                { label: 'Optimized Cost (EGP)', data: optimizedCosts, backgroundColor: '#0ea5e9', borderRadius: 4 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { color: '#ffffff' } }, y: { beginAtZero: true, ticks: { color: '#0ea5e9' } } } }
    });

    // Pass disaggregated matrices directly into Gemini Pro pipeline
    if (Object.keys(deviceConsumption).length > 0) {
        window.fetchLiveGeminiTipsFromFlask(deviceConsumption, aiDevices, currentCosts, originalSavingsEffect);
    }
};

// Feed disaggregated matrix into Gemini Engine via safe Flask endpoint
window.fetchLiveGeminiTipsFromFlask = async function(deviceData, aiDevices, currentCosts, originalSavingsEffect) {
    if (!deviceData || typeof deviceData !== 'object' || Object.keys(deviceData).length === 0) {
        const tipsContainer = document.getElementById('ai-tips-container');
        if (tipsContainer) tipsContainer.innerHTML = '<p style="color: #9ca3af;">Not enough device telemetry to generate tips.</p>';
        return;
    }

    const tipsContainer = document.getElementById('ai-tips-container');
    if (!tipsContainer) return;

    tipsContainer.innerHTML = '<p style="color: #38bdf8;"><i class="fa-solid fa-spinner fa-spin"></i> Processing System Optimization...</p>';

    try {
        const flaskResponse = await fetch('/api/ai/recommendations', {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ devices: deviceData })
        });

        const flaskData = await flaskResponse.json();
        if (!flaskResponse.ok) throw new Error(flaskData.error || "Connection failure to Gemini gateway");

        tipsContainer.innerHTML = '';
        const rawTips = flaskData.recommendations.split('*');

        aiDevices.forEach((device, index) => {
            let matchedTip = rawTips.find(t => t.toUpperCase().includes(device.toUpperCase()));
            let cleanTipText = matchedTip && matchedTip.includes(':') ? matchedTip.split(':')[1].trim() : `Monitor operations for ${device}.`;

            let tipRow = document.createElement('div');
            tipRow.style.cssText = 'display: flex; align-items: flex-start; gap: 12px; padding: 12px; margin-bottom: 8px; border-radius: 8px; background: rgba(14, 165, 233, 0.12); border-left: 4px solid #0ea5e9;';
            tipRow.innerHTML = `
                <input type="checkbox" id="check-${device}" data-device-index="${index}" data-device-name="${device}" checked style="width: 18px; height: 18px; cursor: pointer;">
                <label for="check-${device}" style="cursor: pointer; flex: 1;"><strong style="color: #38bdf8;">${device}:</strong> ${cleanTipText}</label>`;

            tipsContainer.appendChild(tipRow);

            document.getElementById(`check-${device}`).addEventListener('change', function() {
                let idx = this.getAttribute('data-device-index');
                let dName = this.getAttribute('data-device-name');
                if (this.checked) {
                    myAICostChart.data.datasets[1].data[idx] = currentCosts[idx] - (originalSavingsEffect[dName] || 0);
                } else {
                    myAICostChart.data.datasets[1].data[idx] = currentCosts[idx];
                }
                myAICostChart.update();
            });
        });
    } catch (geminiError) {
        console.error("AI Recommendations Engine Error:", geminiError);
        tipsContainer.innerHTML = `<p style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> ${geminiError.message}</p>`;
    }
};
// Automated full state tracking clearance on logout
document.querySelectorAll('a[href="/logout"]').forEach(btn => {
    btn.addEventListener('click', function() {
        sessionStorage.clear();
        localStorage.clear();
        window.activeEspId = null;
        window.mainMeterId = null;
    });
});

// Self-invoking DOM trigger for analytics initial lifecycle
document.addEventListener('DOMContentLoaded', function() {
    if (document.body.classList.contains('analytics-page')) {
        window.initAnalytics();
    }
});