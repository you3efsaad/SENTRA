document.addEventListener('DOMContentLoaded', function () {
    console.log("🚀 Safe Power System Loaded");
    
    // أي كود آخر يحتاج للتشغيل عند بداية التحميل ضعيه هنا
    // لكن الدوال التي يتم استدعاؤها من الـ HTML (مثل onclick) يجب أن تكون خارج هذا البلوك
});

// ==================================================
// دالة الـ Sidebar (يجب أن تكون خارج الـ EventListener)
// ==================================================
function toggleSidebar() {
    // 1. الإمساك بالعناصر
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    
    // تأكدنا أن العناصر موجودة قبل العمل عليها لتجنب الأخطاء
    if (sidebar && overlay) {
        // 2. التبديل: إضافة أو إزالة كلاس "open"
        sidebar.classList.toggle('open');
        
        // 3. التحكم في ظهور الخلفية المظلمة (Overlay)
        if (sidebar.classList.contains('open')) {
            overlay.style.display = 'block';
        } else {
            overlay.style.display = 'none';
        }
    } else {
        console.error("Sidebar or Overlay element not found!");
    }
}

document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // 1. حل مشكلة الأسهم (Scroll Logic)
    // ==========================================
    const scrollContainer = document.querySelector('.devices-scroll-container');
    const btnLeft = document.getElementById('scrollLeft');
    const btnRight = document.getElementById('scrollRight');

    if (scrollContainer && btnLeft && btnRight) {
        // عند الضغط يمين
        btnRight.addEventListener('click', () => {
            scrollContainer.scrollBy({ left: 250, behavior: 'smooth' });
        });

        // عند الضغط يسار
        btnLeft.addEventListener('click', () => {
            scrollContainer.scrollBy({ left: -250, behavior: 'smooth' });
        });
    } else {
        console.error("Scroll elements not found!");
    }

});

// ==========================================
// 2. حل مشكلة الأيقونات (Smart Icons)
// ==========================================
function getDeviceIcon(name) {
    const n = name.toLowerCase();

    // --- أجهزة المطبخ (Kitchen) ---
    if (n.includes("fridge") || n.includes("refrigerator")) return "fa-snowflake"; // ثلاجة
    if (n.includes("microwave") || n.includes("oven")) return "fa-fire-burner";    // ميكروويف/فرن
    if (n.includes("kettle") || n.includes("coffee") || n.includes("tea")) return "fa-mug-hot"; // كاتل
    if (n.includes("toaster") || n.includes("grill")) return "fa-bread-slice";     // توستر
    if (n.includes("blender") || n.includes("mixer")) return "fa-lemon";           // خلاط
    if (n.includes("dish")) return "fa-soap"; // غسالة أطباق

    // --- أجهزة المنزل (Home Appliances) ---
    if (n.includes("iron")) return "fa-shirt";  // مكواة (رمز قميص لأنه أوضح شيء للمكواة)
    if (n.includes("wash") || n.includes("laundry")) return "fa-jug-detergent"; // غسالة ملابس
    if (n.includes("heater") || n.includes("boiler")) return "fa-temperature-arrow-up"; // سخان
    if (n.includes("fan")) return "fa-fan"; // مروحة
    if (n.includes("ac") || n.includes("conditioner") || n.includes("cool")) return "fa-wind"; // تكييف
    if (n.includes("vacuum")) return "fa-broom"; // مكنسة (رمز مقشة لعدم توفر مكنسة)

    // --- إلكترونيات (Electronics) ---
    if (n.includes("tv") || n.includes("screen")) return "fa-tv"; // تلفزيون
    if (n.includes("pc") || n.includes("computer") || n.includes("laptop")) return "fa-laptop"; // كمبيوتر
    if (n.includes("router") || n.includes("wifi")) return "fa-wifi"; // راوتر
    if (n.includes("playstation") || n.includes("xbox") || n.includes("game")) return "fa-gamepad"; // ألعاب
    if (n.includes("phone") || n.includes("charger")) return "fa-mobile-screen"; // شاحن موبايل

    // --- إضاءة (Lights) ---
    if (n.includes("lamp") || n.includes("light") || n.includes("bulb") || n.includes("led")) return "fa-lightbulb";

    // --- افتراضي (Default) ---
    return "fa-plug-circle-bolt"; // شكل فيشة شيك للأجهزة غير المعروفة
}

// ==========================================
// 3. دالة إضافة الكارت الجديد
// ==========================================
// فتح النافذة
// دالة لفتح النافذة عند الضغط على كارت Add Device
function addNewDeviceUI() {
    const modal = document.getElementById('deviceModal');
    modal.style.display = 'flex';
    document.getElementById('newDeviceName').focus();
}

// دالة لإغلاق النافذة
function closeDeviceModal() {
    document.getElementById('deviceModal').style.display = 'none';
    document.getElementById('newDeviceName').value = '';
}

// دالة تأكيد الإضافة
function confirmAddDevice() {
    const nameInput = document.getElementById('newDeviceName');
    const deviceName = nameInput.value.trim();

    if (deviceName) {
        // تنفيذ عملية الإضافة (نفس الكود الخاص بكِ سابقاً)
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
        addBtn.insertAdjacentHTML('beforebegin', newCardHTML);
        
        // إغلاق النافذة وتنظيفها
        closeDeviceModal();

        // تحريك السكرول للجهاز الجديد
        const scrollContainer = document.querySelector('.devices-scroll-container');
        setTimeout(() => {
            scrollContainer.scrollTo({ left: scrollContainer.scrollWidth, behavior: 'smooth' });
        }, 100);
    }
}

// إغلاق النافذة عند الضغط خارجها
window.onclick = function(event) {
    const modal = document.getElementById('deviceModal');
    if (event.target == modal) {
        closeDeviceModal();
    }
}


// // ==================================================
// // 2. DASHBOARD LOGIC (الصفحة الرئيسية)
// // ==================================================
// // function initDashboard() {
// //     console.log("🔹 Initializing Dashboard...");

// //     // دالة تحديث البيانات
// //     const updateDashboardData = async () => {
// //         try {
// //             const res = await fetch('/latest');
// //             const data = await res.json();

// //             // تحديث الكروت (مع فحص الأمان)
// //             safeTxt('voltage-value', data.voltage + ' V');
// //             safeTxt('current-value', data.current + ' A');
// //             safeTxt('power-value', data.power + ' W');
// //             safeTxt('energy-value', data.energy + ' kWh');
// //             safeTxt('frequency-value', data.frequency + ' Hz');
// //             safeTxt('power-factor-value', data.pf);

// //             // تحديث الجرافات الصغيرة (Sparklines) لو موجودة
// //             // (ممكن نضيف كود Chart.js هنا لو حابب تفعل الجرافات الصغيرة اللي في HTML)

// //         } catch (e) { console.error("Dashboard Sync Error:", e); }
// //     };

// //     // تحديث كل 2 ثانية
// //     setInterval(updateDashboardData, 2000);
// //     updateDashboardData(); // تحديث فوري عند التحميل
// // }
// // ==================================================
// // 2. DASHBOARD LOGIC (الصفحة الرئيسية)
// // ==================================================
// function initDashboard() {
//     console.log("🔹 Initializing Dashboard...");

//     // دالة تحديث الأرقام (فولت، تيار، باور...)
//     const updateDashboardData = async () => {
//         try {
//             const res = await fetch('/latest');
//             const data = await res.json();

//             safeTxt('voltage-value', data.voltage + ' V');
//             safeTxt('current-value', data.current + ' A');
//             safeTxt('power-value', data.power + ' W');
//             safeTxt('energy-value', data.energy + ' kWh');
//             safeTxt('frequency-value', data.frequency + ' Hz');

//             // تحديث حالة الجهاز (Standby / Active)
//             const dot = document.getElementById('status-dot');
//             const txt = document.getElementById('status-text');
//             if (dot && txt) {
//                 if (data.power > 5) {
//                     dot.className = "status-dot status-on";
//                     txt.innerText = "Active";
//                     txt.style.color = "#4ade80";
//                 } else {
//                     dot.className = "status-dot status-off";
//                     txt.innerText = "Standby";
//                     txt.style.color = "#f87171";
//                 }
//             }

//         } catch (e) { console.error("Dashboard Sync Error:", e); }
//     };

//     // تشغيل تحديث الأرقام كل 2 ثانية
//     setInterval(updateDashboardData, 2000);
//     updateDashboardData();

//     // ✅✅✅ هام جداً: تشغيل تحديث كارت الذكاء الاصطناعي (AI) ✅✅✅
//     // تأكد إن السطر ده موجود عشان الاسم يتغير!
//     if (typeof updateAICard === "function") {
//         setInterval(updateAICard, 2000);
//         updateAICard(); // تشغيل فوري
//     } else {
//         console.error("⚠️ updateAICard function is missing!");
//     }
// }
// async function updateAICard() {
//     const nameEl = document.getElementById('ai-device-name');
//     const statusEl = document.getElementById('ai-device-status');
//     const renameBtn = document.getElementById('rename-btn');
//     const clusterInput = document.getElementById('current-cluster-id');

//     if (!nameEl) return; // لو مش في صفحة الداشبورد اخرج

//     try {
//         const res = await fetch('/latest');
//         const data = await res.json();

//         // تحديث الاسم
//         if (data.ai_device_name) {
//             nameEl.textContent = data.ai_device_name;
//             if (clusterInput) clusterInput.value = data.ai_cluster_id;

//             // تغيير لون الحالة وشكل الزرار
//             if (data.ai_device_name.includes("Unknown")) {
//                 // جهاز جديد
//                 statusEl.textContent = "New Pattern";
//                 statusEl.style.background = "#fef08a"; // أصفر
//                 statusEl.style.color = "#854d0e";

//                 if (renameBtn) {
//                     renameBtn.style.display = "inline-block";
//                     renameBtn.innerHTML = '<i class="fa-solid fa-plus"></i> Name It';
//                 }
//             } else if (data.ai_device_name === "Idle") {
//                 // وضع خمول
//                 statusEl.textContent = "Standby";
//                 statusEl.style.background = "#e2e8f0"; // رصاصي
//                 statusEl.style.color = "#475569";
//                 if (renameBtn) renameBtn.style.display = "none";
//             } else {
//                 // جهاز معروف
//                 statusEl.textContent = "Identified";
//                 statusEl.style.background = "#bbf7d0"; // أخضر
//                 statusEl.style.color = "#166534";

//                 // زرار تعديل (اختياري)
//                 if (renameBtn) {
//                     renameBtn.style.display = "inline-block";
//                     renameBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Edit';
//                 }
//             }
//         }
//     } catch (e) { console.error("AI Update Error", e); }
// }

// // 3. دالة إرسال التسمية للسيرفر (مربوطة بالزرار في HTML)
// window.userRenamesDevice = async function (clusterId, newName) {
//     try {
//         const response = await fetch('/rename_device', {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({
//                 cluster_id: parseInt(clusterId),
//                 new_name: newName
//             })
//         });

//         const result = await response.json();
//         if (result.status === 'success') {
//             alert(`✅ Saved! This device is now: "${newName}"`);
//             // تحديث فوري للاسم في الصفحة
//             const nameEl = document.getElementById('ai-device-name');
//             if (nameEl) nameEl.textContent = newName;

//             // إخفاء الـ Modal
//             if (typeof closeRenameModal === 'function') closeRenameModal();
//         } else {
//             alert("❌ Error: " + result.message);
//         }
//     } catch (error) {
//         console.error("Renaming Error:", error);
//     }
// };

document.addEventListener('DOMContentLoaded', function () {
    console.log("🚀 Safe Power System Loaded");

    // 1. تحديد الصفحة وتشغيل الكود المناسب
    const body = document.body;
    if (body.classList.contains('dashboard-page')) {
        initDashboard();
    }

    // (يمكنك إضافة باقي الصفحات هنا)
});

// ==================================================
// 🛠️ HELPER FUNCTIONS (دوال مساعدة)
// ==================================================
function safeTxt(id, val) {
    const el = document.getElementById(id);
    if (el) el.innerText = val;
}

// ==================================================
// 📊 DASHBOARD LOGIC (الداشبورد)
// ==================================================
function initDashboard() {
    console.log("🔹 Initializing Dashboard...");

    // 1. تشغيل التحديث التلقائي
    setInterval(updateDashboardData, 2000); // كل 2 ثانية للأرقام
    setInterval(updateAICard, 2000);      // كل 2 ثانية للذكاء الاصطناعي

    updateDashboardData();
    updateAICard();

    // 2. تشغيل زرار التسمية (ده اللي بيحل المشكلة)
    setupRenameModal();
}

// تحديث الأرقام (فولت، تيار، باور...)
async function updateDashboardData() {
    try {
        const res = await fetch('/latest');
        const data = await res.json();

        safeTxt('voltage-value', data.voltage + ' V');
        safeTxt('current-value', data.current + ' A');
        safeTxt('power-value', data.power + ' W');
        safeTxt('energy-value', data.energy + ' kWh');
        safeTxt('frequency-value', data.frequency + ' Hz');
        safeTxt('pf-value', data.pf);

        // تحديث حالة اللمبة (Active/Standby)
        const dot = document.getElementById('status-dot');
        const txt = document.getElementById('status-text');
        if (dot && txt) {
            if (data.power > 5) {
                dot.className = "status-dot status-on";
                txt.innerText = "Active";
                txt.style.color = "#4ade80";
            } else {
                dot.className = "status-dot status-off";
                txt.innerText = "Standby";
                txt.style.color = "#f87171";
            }
        }
    } catch (e) { console.error("Data Sync Error:", e); }
}

// ==================================================
// 🤖 AI ENGINE LOGIC (كارت الذكاء الاصطناعي)
// ==================================================

// 1. تحديث الكارت (بيجيب الاسم من السيرفر)
async function updateAICard() {
    const nameEl = document.getElementById('ai-device-name');
    const statusEl = document.getElementById('ai-device-status');
    const renameBtn = document.getElementById('rename-btn');
    const clusterInput = document.getElementById('current-cluster-id');

    if (!nameEl) return;

    try {
        const res = await fetch('/latest');
        const data = await res.json();

        if (data.ai_device_name) {
            nameEl.textContent = data.ai_device_name;

            // تخزين رقم الكلاستر عشان نستخدمه في التسمية
            if (clusterInput) clusterInput.value = data.ai_cluster_id;

            // تغيير الألوان والزرار حسب الحالة
            if (data.ai_device_name.includes("Unknown")) {
                // جهاز جديد -> اظهر زرار "Name It"
                statusEl.textContent = "New Pattern";
                statusEl.style.background = "#fef08a";
                statusEl.style.color = "#854d0e";
                if (renameBtn) {
                    renameBtn.style.display = "inline-block";
                    renameBtn.innerHTML = '<i class="fa-solid fa-plus"></i> Name It';
                }
            } else if (data.ai_device_name === "Idle") {
                // وضع خمول
                statusEl.textContent = "Standby";
                statusEl.style.background = "#e2e8f0";
                statusEl.style.color = "#475569";
                if (renameBtn) renameBtn.style.display = "none";
            } else {
                // جهاز معروف -> اظهر زرار "Edit"
                statusEl.textContent = "Identified";
                statusEl.style.background = "#bbf7d0";
                statusEl.style.color = "#166534";
                if (renameBtn) {
                    renameBtn.style.display = "inline-block";
                    renameBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Edit';
                }
            }
        }
    } catch (e) { console.error("AI Update Error:", e); }
}

// 2. إرسال الاسم الجديد للسيرفر
window.userRenamesDevice = async function (clusterId, newName) {
    try {
        const response = await fetch('/rename_device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cluster_id: parseInt(clusterId),
                new_name: newName
            })
        });

        const result = await response.json();
        if (result.status === 'success') {
            alert(`✅ Saved! Device is now: "${newName}"`);
            // تحديث فوري للاسم في الصفحة
            const nameEl = document.getElementById('ai-device-name');
            if (nameEl) nameEl.textContent = newName;
            return true;
        } else {
            alert("❌ Error: " + result.message);
            return false;
        }
    } catch (error) {
        console.error("Renaming Error:", error);
        alert("⚠️ Connection Error");
        return false;
    }
};

// ==================================================
// 🪟 MODAL LOGIC (النافذة المنبثقة)
// ==================================================
function setupRenameModal() {
    const modal = document.getElementById("renameModal");
    if (!modal) return;

    // تعريف دالة الفتح عشان الـ HTML يشوفها
    window.openRenameModal = function () {
    const clusterIdInput = document.getElementById("current-cluster-id");
    const modalIdSpan = document.getElementById("modal-cluster-id");
    
    const clusterId = clusterIdInput ? clusterIdInput.value : "?";
    if (modalIdSpan) modalIdSpan.textContent = clusterId;

    // تنظيف الخانة
    const input = document.getElementById("new-device-name-input");
    if (input) input.value = "";

    // --- التغيير الجوهري هنا ---
    // نستخدم flex بدلاً من block ليعمل التوسيط العمودي والأفقي
    modal.style.display = "flex"; 
};

    // دالة الغلق
    window.closeRenameModal = function () {
        modal.style.display = "none";
    };

    // دالة الحفظ (لما تدوس Save في النافذة)
    window.submitRename = async function () {
        const clusterId = document.getElementById("current-cluster-id").value;
        const newName = document.getElementById("new-device-name-input").value;

        if (!newName) return alert("Please enter a name!");

        const success = await window.userRenamesDevice(clusterId, newName);
        if (success) {
            window.closeRenameModal();
        }
    };

    // إغلاق لو ضغطت بره الصندوق
    window.onclick = function (event) {
        if (event.target == modal) window.closeRenameModal();
    };
}
// ==================================================
// 3. CONSUMPTION LOGIC (صفحة الاستهلاك)
// ==================================================
// let livePowerChart, liveEnergyChart;

// function initConsumption() {
//     console.log("🔹 Initializing Consumption Page...");

//     // 1. التعامل مع التبويبات (Tabs)
//     const tabs = document.querySelectorAll('.tab');
//     tabs.forEach(tab => {
//         tab.addEventListener('click', () => {
//             // إخفاء كل المحتوى
//             document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
//             document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

//             // إظهار المحتوى المختار
//             const targetId = tab.getAttribute('data-tab') + '-tab'; // live-tab or historical-tab
//             const targetContent = document.getElementById(targetId);
//             if (targetContent) {
//                 targetContent.style.display = 'block';
//                 tab.classList.add('active');
//             }
//         });
//     });

//     // 2. تهيئة الجرافات اللايف (Live Charts)
//     const pCtx = document.getElementById('powerChart');
//     const eCtx = document.getElementById('energyChart');

//     if (pCtx && eCtx) {
//         // إعدادات مشتركة للجرافات
//         const commonOptions = {
//             responsive: true,
//             maintainAspectRatio: false,
//             scales: { x: { display: false }, y: { beginAtZero: true } },
//             animation: { duration: 0 } // إلغاء الانيميشن عشان الأداء
//         };

//         livePowerChart = new Chart(pCtx.getContext('2d'), {
//             type: 'line',
//             data: { labels: [], datasets: [{ label: 'Power (W)', data: [], borderColor: '#3b82f6', tension: 0.4 }] },
//             options: commonOptions
//         });

//         liveEnergyChart = new Chart(eCtx.getContext('2d'), {
//             type: 'bar',
//             data: { labels: [], datasets: [{ label: 'Energy (kWh)', data: [], backgroundColor: '#10b981' }] },
//             options: commonOptions
//         });

//         // 3. تحديث البيانات اللايف
//         setInterval(async () => {
//             // نحدث بس لو التبويب اللايف مفتوح
//             if (document.getElementById('live-tab').style.display !== 'none') {
//                 try {
//                     const res = await fetch('/latest');
//                     const data = await res.json();

//                     const now = new Date().toLocaleTimeString();

//                     // تحديث الأرقام
//                     safeTxt('livePowerValue', data.power + ' kW'); // أو W حسب رغبتك
//                     safeTxt('liveEnergyValue', data.energy + ' kWh');

//                     // تحديث الجرافات
//                     updateChart(livePowerChart, now, data.power);
//                     updateChart(liveEnergyChart, now, data.energy);

//                 } catch (e) { console.error("Live Data Error:", e); }
//             }
//         }, 2000);
//     }
// }

let powerMiniChart;
function initPowerMiniChart() {
    const ctx = document.getElementById('powerMiniChart').getContext('2d');
    
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
                pointRadius: 4,           // كبرنا النقطة عشان تبان
                pointBackgroundColor: '#fff', // لون النقطة أبيض عشان تبرز
                fill: true,
                backgroundColor: gradient,
                tension: 0.4
            }]
        },
        options: {
    responsive: true,
    maintainAspectRatio: false,
    
    // هذا الجزء هو المسؤول عن كيفية التقاط الماوس للنقطة
    interaction: {
        mode: 'index',
        intersect: false, // يجعل الرقم يظهر حتى لو لم تلمسي النقطة بالضبط (بمجرد القرب منها)
    },

    plugins: {
        legend: { display: false },
        tooltip: {
            enabled: true,         // تفعيل ظهور المربع الأسود (التول تيب)
            backgroundColor: 'rgba(0, 0, 0, 0.8)', // لون خلفية المربع
            titleColor: '#fff',
            bodyColor: '#fff',
            padding: 10,
            displayColors: false,  // إخفاء مربعات الألوان الصغيرة داخل التول تيب
            callbacks: {
                label: function(context) {
                    return `Power: ${context.parsed.y} W`;
                }
            }
        }
    },

    // ابحثي عن جزء الـ scales في الكود الخاص بكِ وقومي بتعديله كالتالي:

    scales: {
        x: { 
            display: true, 
            grid: { display: false },
            ticks: { color: 'rgba(255,255,255,0.5)', font: { size: 10 } }
        },
        y: { 
            display: true, 
            position: 'left', // تم التغيير من right إلى left هنا
            grid: { color: 'rgba(255,255,255,0.1)' },
            ticks: { 
                color: 'rgba(255,255,255,0.7)', 
                font: { size: 12 },
                padding: 10 // أضفت لكِ مسافة بسيطة لتبدو الأرقام منظمة
            }
        }
    }
}
    });
}
// 2. تحديث التابع setInterval الأصلي لديكِ
setInterval(async () => {
    try {
        const res = await fetch('/latest');
        const data = await res.json();
        const now = new Date().toLocaleTimeString();

        // تحديث الأرقام (باستخدام IDs الكود الخاص بكِ)
        if (document.getElementById('livePowerValue')) {
            document.getElementById('livePowerValue').innerText = data.power + ' W';
        }

        // --- السحر هنا: رسم النقطة الجديدة في الجراف ---
        if (powerMiniChart) {
            powerMiniChart.data.labels.push(now);
            powerMiniChart.data.datasets[0].data.push(data.power);

            // الحفاظ على آخر 20 نقطة فقط عشان الجراف ميزحمش الشاشة
            if (powerMiniChart.data.labels.length > 20) {
                powerMiniChart.data.labels.shift();
                powerMiniChart.data.datasets[0].data.shift();
            }
            powerMiniChart.update();
        }
        // ------------------------------------------

    } catch (e) { 
        console.error("خطأ في جلب البيانات:", e); 
    }
}, 2000); // تحديث كل ثانيتين

// لا تنسي استدعاء دالة التهيئة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', initPowerMiniChart);


// دالة مساعدة لتحديث الجرافات
function updateChart(chart, label, value) {
    if (!chart) return;
    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(value);

    if (chart.data.labels.length > 20) { // عرض آخر 20 قراءة بس
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
    }
    chart.update();
}

// دالة توليد الداتا التاريخية (مربوطة بالزرار في HTML)
let historicalChartInstance = null;

window.generateHistoricalData = async function () {
    const start = document.getElementById('start-date').value;
    const end = document.getElementById('end-date').value;

    if (!start) return alert("Please select a start date!");

    // تغيير نص الزرار لـ "Loading..."
    const btn = document.getElementById('hist-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
    btn.disabled = true;

    try {
        const res = await fetch(`/historical?start=${start}&end=${end}`);
        const data = await res.json();

        if (data.values.length === 0) {
            alert("No data found for this date range.");
            btn.innerHTML = originalText;
            btn.disabled = false;
            return;
        }

        // === رسم الجراف (The Magic Part) ===
        const ctx = document.getElementById('historicalChart');
        if (ctx) {
            // لو فيه جراف قديم، دمره الأول عشان ميركبوش فوق بعض
            if (historicalChartInstance) historicalChartInstance.destroy();

            historicalChartInstance = new Chart(ctx.getContext('2d'), {
                type: 'bar', // نوع الجراف: أعمدة
                data: {
                    labels: data.labels, // التواريخ والساعات
                    datasets: [
                        {
                            label: 'Energy Consumption (kWh)',
                            data: data.values, // قيم الاستهلاك
                            backgroundColor: '#3b82f6',
                            borderRadius: 4,
                            order: 1
                        },
                        {
                            label: 'Average Power (W)', // خط إضافي للباور
                            data: data.power, // قيم الباور
                            type: 'line',
                            borderColor: '#ef4444',
                            borderWidth: 2,
                            pointRadius: 0,
                            yAxisID: 'y1', // محور Y منفصل
                            order: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: { display: true, text: 'Energy (kWh)' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: { drawOnChartArea: false }, // عشان الخطوط متدخلش في بعض
                            title: { display: true, text: 'Power (W)' }
                        }
                    }
                }
            });
        }

    } catch (e) {
        console.error("History Error:", e);
        alert("Failed to load data.");
    } finally {
        // إرجاع الزرار لحالته الأصلية
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};
// ==================================================
// 4. REPORTS LOGIC (صفحة التقارير)
// ==================================================
let reportChartInstance;

function initReports() {
    console.log("🔹 Initializing Reports Page...");
    // تحميل التقرير اليومي افتراضياً
    window.generateReport('daily');
}

window.generateReport = async function (type, btnElement) {
    // 1. تنسيق الأزرار
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    if (btnElement) btnElement.classList.add('active');

    try {
        const res = await fetch(`/report/${type}`);
        const data = await res.json();

        // 2. تحديث الكروت
        // ملاحظة: HTML بتاعك فيه id="avgConsumption" بس إحنا هنعرض التكلفة مكانه
        safeTxt('totalConsumption', data.total_consumption + ' kWh');
        safeTxt('avgConsumption', data.total_cost + ' EGP'); // عرضنا التكلفة في خانة المتوسط
        safeTxt('peakConsumption', data.peak_consumption + ' kWh');

        // تحديث العنوان
        safeTxt('reportTitle', type.charAt(0).toUpperCase() + type.slice(1) + ' Summary');

        // 3. رسم الجراف
        const ctx = document.getElementById('reportChart');
        if (ctx) {
            if (reportChartInstance) reportChartInstance.destroy();

            reportChartInstance = new Chart(ctx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Consumption (kWh)',
                        data: data.values,
                        backgroundColor: '#3b82f6',
                        borderRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });
        }

    } catch (e) { console.error("Report Fetch Error:", e); }
};

// ==================================================
// 5. SETTINGS & TIMER LOGIC (صفحة الإعدادات)
// ==================================================
function initSettings() {
    console.log("🔹 Initializing Settings Page...");

    // 1. تحديث التايمر كل ثانية
    setInterval(syncTimerUI, 1000);

    // 2. جلب الحد الحالي للطاقة
    fetch('/esp_limit')
        .then(r => r.json())
        .then(data => {
            const el = document.getElementById('ww'); // العنصر اللي بيعرض القيمة الحالية
            if (el && data.power_limit) el.innerText = data.power_limit;

            const input = document.getElementById('power-limit');
            if (input && data.power_limit) input.value = data.power_limit;
        });
}

// دوال التحكم (متاحة في window)
window.submitPowerLimit = async function () {
    const val = document.getElementById('power-limit').value;
    if (!val) return alert("Please enter a value!");

    await fetch('/set_limit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: val })
    });
    alert("Power Limit Updated!");
    // تحديث العرض
    safeTxt('ww', val);
};

window.onSetTimeClick = async function () {
    const min = document.getElementById('timer-duration').value;
    if (!min) return alert("Enter duration in minutes!");

    await fetch('/set_timer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration_minutes: min })
    });
    syncTimerUI(); // تحديث فوري
};

window.onPauseClick = async () => { await fetch('/pause_timer', { method: 'POST' }); syncTimerUI(); };
window.onCancelClick = async () => { await fetch('/reset_timer', { method: 'POST' }); syncTimerUI(); };
window.sendCommand = async (cmd) => {
    await fetch('/set_command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
    });
    alert(`Command Sent: ${cmd.toUpperCase()}`);
};

// دالة مزامنة واجهة التايمر
async function syncTimerUI() {
    try {
        const res = await fetch('/get_timer');
        const data = await res.json();

        const remaining = data.remaining_seconds || 0;
        const isPaused = data.paused || false;

        // تحديث حقول الوقت (Hours, Minutes, Seconds)
        const h = Math.floor(remaining / 3600);
        const m = Math.floor((remaining % 3600) / 60);
        const s = remaining % 60;

        // تحديث الحقول لو موجودة (فقط في صفحة Settings)
        const hEl = document.getElementById('hours');
        if (hEl) {
            hEl.value = h.toString().padStart(2, '0');
            document.getElementById('minutes').value = m.toString().padStart(2, '0');
            document.getElementById('seconds').value = s.toString().padStart(2, '0');

            // التحكم في ظهور الأزرار
            const setBtn = document.getElementById('set-time-btn');
            const pauseBtn = document.getElementById('pause-btn');
            const cancelBtn = document.getElementById('cancel-btn');

            if (remaining > 0 || isPaused) {
                // التايمر شغال
                if (setBtn) setBtn.style.display = 'none';
                if (pauseBtn) {
                    pauseBtn.style.display = 'inline-block';
                    pauseBtn.innerText = isPaused ? "Resume" : "Pause";
                }
                if (cancelBtn) cancelBtn.style.display = 'inline-block';
            } else {
                // التايمر واقف
                if (setBtn) setBtn.style.display = 'inline-block';
                if (pauseBtn) pauseBtn.style.display = 'none';
                if (cancelBtn) cancelBtn.style.display = 'none';
            }
        }
    } catch (e) { /* Ignore errors if elements missing */ }
}

// ==================================================
// 6. CONTACT PAGE LOGIC
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
// 7. HELPER FUNCTIONS (SHARED)
// ==================================================
function initSidebar() {
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');

    if (toggle && sidebar) {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('open');
            document.body.classList.toggle('sidebar-open');
        });

        // إغلاق السايدبار عند الضغط في أي مكان خارجه
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
                sidebar.classList.remove('open');
                document.body.classList.remove('sidebar-open');
            }
        });
    }
}

function initNotifications() {
    // كود بسيط لفتح وغلق الإشعارات
    const bell = document.querySelector('.fa-bell');
    const popup = document.getElementById('notification-popup');
    if (bell && popup) {
        bell.addEventListener('click', (e) => {
            e.stopPropagation();
            popup.style.display = (popup.style.display === 'none') ? 'block' : 'none';
        });
    }
}

// دالة أمان: بتكتب في العنصر لو موجود بس
function safeTxt(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}



// ==================================================
// 8. AI RENAMING LOGIC (تسمية الأجهزة الجديدة)
// ==================================================

// // الدالة دي مربوطة بـ dashboard.html عشان تسمي الجهاز
// window.userRenamesDevice = async function (clusterId, newName) {
//     console.log(`📝 Renaming Cluster ${clusterId} to "${newName}"...`);

//     try {
//         const response = await fetch('/rename_device', {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({
//                 cluster_id: parseInt(clusterId), // لازم نتأكد إنه رقم
//                 new_name: newName
//             })
//         });

//         const result = await response.json();

//         if (result.status === 'success') {
//             alert(`✅ Done! System now knows this device as "${newName}".`);

//             // تحديث الاسم فوراً في الصفحة عشان اليوزر يشوف النتيجة
//             const nameEl = document.getElementById('ai-device-name');
//             if (nameEl) nameEl.textContent = newName;

//             // إخفاء زرار التسمية لأنه خلاص بقى معروف
//             const btn = document.getElementById('rename-btn');
//             if (btn) btn.style.display = 'none';

//         } else {
//             alert("❌ Error: " + result.message);
//         }
//     } catch (error) {
//         console.error("Renaming Error:", error);
//         alert("⚠️ Network Error. Check console.");
//     }
// };

// // // تحديث بيانات كارت الـ AI في الداشبورد
// // async function updateAICard() {
//     const nameEl = document.getElementById('ai-device-name');
//     const statusEl = document.getElementById('ai-device-status');
//     const renameBtn = document.getElementById('rename-btn');
//     const clusterInput = document.getElementById('current-cluster-id');

//     if (!nameEl) return; // لو إحنا مش في الداشبورد، اخرج

//     try {
//         // بنجيب القراءة العادية، وهنفترض إن الـ API هيرجع لنا اسم الجهاز وكود الكلاستر
//         // ملحوظة: لازم نعدل api.py عشان يرجع المعلومات دي، أو نعمل endpoint جديد
//         // حالياً هنستخدم /latest وهنفترض إننا ضفنا البيانات دي فيه
//         const res = await fetch('/latest');
//         const data = await res.json();

//         // بيانات تجريبية (لحد ما نحدث الـ api.py)
//         // data.ai_device_name = "Unknown Device #3"; 
//         // data.ai_cluster_id = 3;

//         if (data.ai_device_name) {
//             nameEl.textContent = data.ai_device_name;

//             if (clusterInput) clusterInput.value = data.ai_cluster_id;

//             // لو الجهاز غير معروف، اظهر زرار التسمية
//             if (data.ai_device_name.includes("Unknown")) {
//                 statusEl.textContent = "New Pattern";
//                 statusEl.style.background = "#fef08a"; // أصفر
//                 if (renameBtn) renameBtn.style.display = "inline-block";
//             } else {
//                 statusEl.textContent = "Identified";
//                 statusEl.style.background = "#bbf7d0"; // أخضر
//                 if (renameBtn) renameBtn.style.display = "none";
//             }
//         }
//     } catch (e) { console.error("AI Update Error", e); }
// }

// // ضيف السطر ده جوه دالة initDashboard عشان يشتغل أوتوماتيك
// // setInterval(updateAICard, 2000);





// ==================================================
// 9. MODAL LOGIC (نقلنا كود النافذة هنا)
// ==================================================

// function setupRenameModal() {
//     const modal = document.getElementById("renameModal");
//     const renameBtn = document.getElementById("rename-btn"); // زرار "Name It"
//     const cancelBtn = document.getElementById("modal-cancel-btn");
//     const saveBtn = document.getElementById("modal-save-btn");

//     if (!modal) return; // لو مش في الداشبورد اخرج

//     // 1. فتح النافذة
//     window.openRenameModal = function () { // خليناها global عشان لو لسه مستخدمة في onclick
//         const clusterId = document.getElementById("current-cluster-id").value;
//         document.getElementById("modal-cluster-id").textContent = clusterId;
//         document.getElementById("new-device-name-input").value = "";
//         modal.style.display = "block";
//     };

//     // 2. غلق النافذة
//     window.closeRenameModal = function () {
//         modal.style.display = "none";
//     };

//     // ربط زرار الإغلاق
//     if (cancelBtn) cancelBtn.onclick = window.closeRenameModal;

//     // 3. تنفيذ الحفظ
//     if (saveBtn) {
//         saveBtn.onclick = async function () {
//             const clusterId = document.getElementById("current-cluster-id").value;
//             const newName = document.getElementById("new-device-name-input").value;

//             if (!newName) return alert("Please enter a name!");

//             if (window.userRenamesDevice) {
//                 await window.userRenamesDevice(clusterId, newName);
//                 window.closeRenameModal();
//             }
//         };
//     }

//     // 4. إغلاق عند الضغط خارج الصندوق
//     window.onclick = function (event) {
//         if (event.target == modal) window.closeRenameModal();
//     };
// }

// // استدعي الدالة دي جوه initDashboard
// // initDashboard() { ... setupRenameModal(); ... }