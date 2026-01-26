document.addEventListener('DOMContentLoaded', function () {
    console.log("🚀 Safe Power System Loaded");

    // ==================================================
    // 1. تحديد الصفحة الحالية وتشغيل الكود الخاص بها فقط
    // ==================================================
    const body = document.body;

    if (body.classList.contains('dashboard-page')) initDashboard();
    if (body.classList.contains('reports-page')) initReports();
    if (body.classList.contains('consumption-page')) initConsumption();
    if (body.classList.contains('settings-page')) initSettings();
    if (body.classList.contains('contact-page')) initContact();

    // تشغيل الـ Sidebar (موجود في كل الصفحات)
    initSidebar();

    // تشغيل الإشعارات (Global Notifications)
    initNotifications();
});

// ==================================================
// 2. DASHBOARD LOGIC (الصفحة الرئيسية)
// ==================================================
function initDashboard() {
    console.log("🔹 Initializing Dashboard...");

    // دالة تحديث البيانات
    const updateDashboardData = async () => {
        try {
            const res = await fetch('/latest');
            const data = await res.json();

            // تحديث الكروت (مع فحص الأمان)
            safeTxt('voltage-value', data.voltage + ' V');
            safeTxt('current-value', data.current + ' A');
            safeTxt('power-value', data.power + ' W');
            safeTxt('energy-value', data.energy + ' kWh');
            safeTxt('frequency-value', data.frequency + ' Hz');
            safeTxt('power-factor-value', data.pf);

            // تحديث الجرافات الصغيرة (Sparklines) لو موجودة
            // (ممكن نضيف كود Chart.js هنا لو حابب تفعل الجرافات الصغيرة اللي في HTML)

        } catch (e) { console.error("Dashboard Sync Error:", e); }
    };

    // تحديث كل 2 ثانية
    setInterval(updateDashboardData, 2000);
    updateDashboardData(); // تحديث فوري عند التحميل
}

// ==================================================
// 3. CONSUMPTION LOGIC (صفحة الاستهلاك)
// ==================================================
let livePowerChart, liveEnergyChart;

function initConsumption() {
    console.log("🔹 Initializing Consumption Page...");

    // 1. التعامل مع التبويبات (Tabs)
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // إخفاء كل المحتوى
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

            // إظهار المحتوى المختار
            const targetId = tab.getAttribute('data-tab') + '-tab'; // live-tab or historical-tab
            const targetContent = document.getElementById(targetId);
            if (targetContent) {
                targetContent.style.display = 'block';
                tab.classList.add('active');
            }
        });
    });

    // 2. تهيئة الجرافات اللايف (Live Charts)
    const pCtx = document.getElementById('powerChart');
    const eCtx = document.getElementById('energyChart');

    if (pCtx && eCtx) {
        // إعدادات مشتركة للجرافات
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: { x: { display: false }, y: { beginAtZero: true } },
            animation: { duration: 0 } // إلغاء الانيميشن عشان الأداء
        };

        livePowerChart = new Chart(pCtx.getContext('2d'), {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Power (W)', data: [], borderColor: '#3b82f6', tension: 0.4 }] },
            options: commonOptions
        });

        liveEnergyChart = new Chart(eCtx.getContext('2d'), {
            type: 'bar',
            data: { labels: [], datasets: [{ label: 'Energy (kWh)', data: [], backgroundColor: '#10b981' }] },
            options: commonOptions
        });

        // 3. تحديث البيانات اللايف
        setInterval(async () => {
            // نحدث بس لو التبويب اللايف مفتوح
            if (document.getElementById('live-tab').style.display !== 'none') {
                try {
                    const res = await fetch('/latest');
                    const data = await res.json();

                    const now = new Date().toLocaleTimeString();

                    // تحديث الأرقام
                    safeTxt('livePowerValue', data.power + ' kW'); // أو W حسب رغبتك
                    safeTxt('liveEnergyValue', data.energy + ' kWh');

                    // تحديث الجرافات
                    updateChart(livePowerChart, now, data.power);
                    updateChart(liveEnergyChart, now, data.energy);

                } catch (e) { console.error("Live Data Error:", e); }
            }
        }, 2000);
    }
}

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