

document.addEventListener('DOMContentLoaded', function () {
    // ==========================
    // NavBar (nav-page)
    // ==========================
    if (document.body.classList.contains('nav-page')) {
        const links = document.querySelectorAll('.nav-links a');
        links.forEach(link => {
            link.addEventListener('click', function () {
                links.forEach(l => l.classList.remove('active'));
                this.classList.add('active');
            });
        });

        // ==========================
        // Sidebar toggle
        // ==========================
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');

        if (sidebarToggle && sidebar) {
            // عند الضغط على زر التبديل
            sidebarToggle.addEventListener('click', function (e) {
                e.stopPropagation();
                const isOpen = sidebar.classList.contains('open');
                if (isOpen) {
                    sidebar.classList.remove('open');
                    document.body.classList.remove('sidebar-open');
                } else {
                    sidebar.classList.add('open');
                    document.body.classList.add('sidebar-open');
                }
            });

            // عند الضغط خارج الـ sidebar
            document.addEventListener('click', function (e) {
                const isClickInsideSidebar = sidebar.contains(e.target);
                const isClickOnToggle = sidebarToggle.contains(e.target);
                if (!isClickInsideSidebar && !isClickOnToggle) {
                    sidebar.classList.remove('open');
                    document.body.classList.remove('sidebar-open');
                }
            });
        }

    }



    // ==========================
    // Dashboard (dashboard-page)
    // ==========================
    if (document.body.classList.contains('dashboard-page')) {

        // Store chart instances
        const chartInstances = {
            voltage: null,
            current: null,
            power: null,
            energy: null,
            frequency: null,
            powerFactor: null
        };

        // Initialize all charts with empty data
        function initCharts() {
            const emptyLabels = [];  // لا نستخدم labels ثابتة

            // Voltage Chart
            const voltageCtx = document.getElementById('voltage-chart').getContext('2d');
            chartInstances.voltage = new Chart(voltageCtx, {
                type: 'line',
                data: {
                    labels: emptyLabels,
                    datasets: [{
                        data: [],
                        borderColor: '#1a73e8',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4
                    }]
                },
                options: getChartOptions()
            });

            // Current Chart
            const currentCtx = document.getElementById('current-chart').getContext('2d');
            chartInstances.current = new Chart(currentCtx, {
                type: 'line',
                data: {
                    labels: emptyLabels,
                    datasets: [{
                        data: [],
                        borderColor: '#1a73e8',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4
                    }]
                },
                options: getChartOptions()
            });

            // Power Chart
            const powerCtx = document.getElementById('power-chart').getContext('2d');
            chartInstances.power = new Chart(powerCtx, {
                type: 'line',
                data: {
                    labels: emptyLabels,
                    datasets: [{
                        data: [],
                        borderColor: '#1a73e8',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4
                    }]
                },
                options: getChartOptions()
            });

            // Energy Chart
            const energyCtx = document.getElementById('energy-chart').getContext('2d');
            chartInstances.energy = new Chart(energyCtx, {
                type: 'line',
                data: {
                    labels: emptyLabels,
                    datasets: [{
                        data: [],
                        borderColor: '#1a73e8',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4
                    }]
                },
                options: getChartOptions()
            });

            // Frequency Chart
            const frequencyCtx = document.getElementById('frequency-chart').getContext('2d');
            chartInstances.frequency = new Chart(frequencyCtx, {
                type: 'line',
                data: {
                    labels: emptyLabels,
                    datasets: [{
                        data: [],
                        borderColor: '#1a73e8',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4
                    }]
                },
                options: getChartOptions()
            });

            // Power Factor Chart
            const powerFactorCtx = document.getElementById('power-factor-chart').getContext('2d');
            chartInstances.powerFactor = new Chart(powerFactorCtx, {
                type: 'line',
                data: {
                    labels: emptyLabels,
                    datasets: [{
                        data: [],
                        borderColor: '#1a73e8',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4
                    }]
                },
                options: getChartOptions()
            });
        }


        function getChartOptions() {
            return {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: true
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        display: true,
                        grid: {
                            display: true
                        },
                        beginAtZero: false
                    }
                },
                elements: {
                    point: {
                        radius: 3,
                        hoverRadius: 5
                    }
                }
            };
        }

        // Function to fetch real sensor data from your backend
        async function fetchSensorData() {
            try {
                // Replace with your actual API endpoint
                const response = await fetch('/latest');
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                const data = await response.json();

                return data;
            } catch (error) {
                console.error('Error fetching sensor data:', error);
                return null;
            }
        }

function generateHourlyLabels(count) {
    const labels = [];

    // نبدأ من أقرب 12 (AM أو PM) في الماضي
    const now = new Date();
    now.setMinutes(0, 0, 0);

    const currentHour = now.getHours();
    let startHour;

    if (currentHour >= 12) {
        startHour = 12;
    } else {
        startHour = 0;
    }

    // اضبط الوقت ليبدأ من أقرب 12 (AM أو PM)
    now.setHours(startHour);

    for (let i = 0; i < count; i++) {
        const labelTime = new Date(now.getTime() + i * 6 * 60 * 60 * 1000); // كل 6 ساعات
        const label = labelTime.toLocaleTimeString([], {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
        labels.push(label);
    }

    return labels;
}





        function updateCharts(data) {
            if (!data) return;

            const count = data.voltage.history.length;
            const labels = generateHourlyLabels(count);  // توليد الـlabels الديناميكية

            chartInstances.voltage.data.labels = labels;
            chartInstances.current.data.labels = labels;
            chartInstances.power.data.labels = labels;
            chartInstances.energy.data.labels = labels;
            chartInstances.frequency.data.labels = labels;
            chartInstances.powerFactor.data.labels = labels;

            chartInstances.voltage.data.datasets[0].data = data.voltage.history;
            chartInstances.current.data.datasets[0].data = data.current.history;
            chartInstances.power.data.datasets[0].data = data.power.history;
            chartInstances.energy.data.datasets[0].data = data.energy.history;
            chartInstances.frequency.data.datasets[0].data = data.frequency.history;
            chartInstances.powerFactor.data.datasets[0].data = data.powerFactor.history;

            chartInstances.voltage.update();
            chartInstances.current.update();
            chartInstances.power.update();
            chartInstances.energy.update();
            chartInstances.frequency.update();
            chartInstances.powerFactor.update();
        }


        function updateTrendIndicator(elementId, trendValue) {
            const element = document.getElementById(elementId);
            const icon = element.querySelector('.trend-icon');
            const text = element.querySelector('span:not(.trend-icon)');

            icon.className = 'trend-icon';
            text.className = '';

            if (trendValue > 0) {
                icon.textContent = '↑';
                text.classList.add('trend-up');
                text.textContent = `Last 24 Hours +${Math.abs(trendValue)}%`;
            } else if (trendValue < 0) {
                icon.textContent = '↓';
                text.classList.add('trend-down');
                text.textContent = `Last 24 Hours -${Math.abs(trendValue)}%`;
            } else {
                icon.textContent = '';
                text.classList.add('trend-neutral');
                text.textContent = 'Last 24 Hours';
            }
        }

        async function updateDashboard() {
            const data = await fetchSensorData();

            if (data) {
                // Update current values
                document.getElementById('voltage-value').textContent = data.voltage.current + 'V';
                document.getElementById('current-value').textContent = data.current.current + 'A';
                document.getElementById('power-value').textContent = data.power.current + ' W';
                document.getElementById('energy-value').textContent = data.energy.current + 'kWh';
                document.getElementById('frequency-value').textContent = data.frequency.current + 'Hz';
                document.getElementById('power-factor-value').textContent = data.powerFactor.current;

                // Update trend values
                document.getElementById('voltage-trend-value').textContent = data.voltage.current + 'V';
                document.getElementById('current-trend-value').textContent = data.current.current + 'A';
                document.getElementById('power-trend-value').textContent = data.power.current + ' W';
                document.getElementById('energy-trend-value').textContent = data.energy.current + 'kWh';
                document.getElementById('frequency-trend-value').textContent = data.frequency.current + 'Hz';
                document.getElementById('power-factor-trend-value').textContent = data.powerFactor.current;

                // Update trend indicators
                updateTrendIndicator('voltage-trend', data.voltage.trend);
                updateTrendIndicator('current-trend', data.current.trend);
                updateTrendIndicator('power-trend', data.power.trend);
                updateTrendIndicator('energy-trend', data.energy.trend);
                updateTrendIndicator('frequency-trend', data.frequency.trend);
                updateTrendIndicator('power-factor-trend', data.powerFactor.trend);

                // Update charts
                updateCharts(data);
            }
        }

        window.addEventListener('resize', () => {
            Object.values(chartInstances).forEach(chart => {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            });
        });


        // Initialize the dashboard

        initCharts();
        updateDashboard();
        setInterval(updateDashboard, 5000); // Update every 5 seconds


    }

    // ==========================
    // Consumption (consumption-page)
    // ==========================

    if (document.body.classList.contains('consumption-page')) {

        let powerChart, energyChart, historicalPowerChart, historicalEnergyChart;

        const tabs = document.querySelectorAll(".tab");
        const underline = document.getElementById("tabUnderline");

        function moveUnderline(tab) {
            if (tab && underline) {
                underline.style.width = `${tab.offsetWidth}px`;
                underline.style.left = `${tab.offsetLeft}px`;
            }
        }

        function showTab(tabName) {
            document.getElementById("live-tab").style.display = tabName === "live" ? "block" : "none";
            document.getElementById("historical-tab").style.display = tabName === "historical" ? "block" : "none";

            tabs.forEach(t => t.classList.remove("active"));
            const clickedTab = document.getElementById(tabName + "TabBtn");
            if (clickedTab) {
                clickedTab.classList.add("active");
                moveUnderline(clickedTab);
            }

            if (tabName === "live") {
                startLiveCharts();
            } else {
                stopLiveCharts();
            }
        }
        window.showTab = showTab;

        function startLiveCharts() {
            fetchLiveData();
            clearInterval(window.liveInterval);
            window.liveInterval = setInterval(fetchLiveData, 5000);
        }

        function stopLiveCharts() {
            clearInterval(window.liveInterval);
        }

        // تخزين بيانات اللايف في localStorage
        function saveLiveDataToLocalStorage() {
            const liveData = {
                powerLabels: powerChart.data.labels,
                powerData: powerChart.data.datasets[0].data,
                energyLabels: energyChart.data.labels,
                energyData: energyChart.data.datasets[0].data
            };
            localStorage.setItem('liveChartData', JSON.stringify(liveData));
        }

        // تحميل بيانات اللايف من localStorage
        function loadLiveDataFromLocalStorage() {
            const saved = localStorage.getItem('liveChartData');
            if (saved) {
                try {
                    return JSON.parse(saved);
                } catch {
                    return null;
                }
            }
            return null;
        }

        function fetchLiveData() {
            fetch('/latest')
                .then(response => response.json())
                .then(data => {
                    // تحديث أرقام Power
                    const currentPower = data.power.current;
                    const powerTrend = data.power.trend;
                    document.getElementById('livePowerValue').textContent = `${currentPower} kW`;
                    const powerChangeEl = document.getElementById('livePowerChange');
                    powerChangeEl.textContent = `Live ${powerTrend >= 0 ? '+' : ''}${powerTrend}%`;
                    if (powerTrend > 0) {
                        powerChangeEl.classList.remove('red');
                        powerChangeEl.classList.add('green');
                    } else if (powerTrend < 0) {
                        powerChangeEl.classList.remove('green');
                        powerChangeEl.classList.add('red');
                    } else {
                        powerChangeEl.classList.remove('green', 'red');
                    }

                    // تحديث أرقام Energy
                    const currentEnergy = data.energy.current;
                    const energyTrend = data.energy.trend;
                    document.getElementById('liveEnergyValue').textContent = `${currentEnergy} kWh`;
                    const energyChangeEl = document.getElementById('liveEnergyChange');
                    energyChangeEl.textContent = `Live ${energyTrend >= 0 ? '+' : ''}${energyTrend}%`;
                    if (energyTrend > 0) {
                        energyChangeEl.classList.remove('red');
                        energyChangeEl.classList.add('green');
                    } else if (energyTrend < 0) {
                        energyChangeEl.classList.remove('green');
                        energyChangeEl.classList.add('red');
                    } else {
                        energyChangeEl.classList.remove('green', 'red');
                    }

                    // تحديث بيانات الجرافات بشكل تراكمي

                    // POWER Chart
                    const newPowerValue = currentPower;
                    powerChart.data.datasets[0].data.push(newPowerValue);
                    if (powerChart.data.datasets[0].data.length > 20) {
                        powerChart.data.datasets[0].data.shift();
                    }

                    // تحديث labels
                    const timeLabel = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    powerChart.data.labels.push(timeLabel);
                    if (powerChart.data.labels.length > 20) {
                        powerChart.data.labels.shift();
                    }

                    powerChart.update();

                    // ENERGY Chart
                    const newEnergyValue = currentEnergy;
                    energyChart.data.datasets[0].data.push(newEnergyValue);
                    if (energyChart.data.datasets[0].data.length > 20) {
                        energyChart.data.datasets[0].data.shift();
                    }

                    energyChart.data.labels.push(timeLabel);
                    if (energyChart.data.labels.length > 20) {
                        energyChart.data.labels.shift();
                    }

                    energyChart.update();

                    // حفظ بيانات اللايف بعد التحديث
                    saveLiveDataToLocalStorage();

                })
                .catch(err => {
                    console.error("Error fetching live data:", err);
                });
        }


        function generateDateLabels(startDate, endDate) {
            const labels = [];
            let current = new Date(startDate);
            const end = new Date(endDate);

            while (current <= end) {
                labels.push(current.toISOString().split('T')[0]);
                current.setDate(current.getDate() + 1);
            }
            return labels;
        }

        function generateHistoricalData() {
            const start = document.getElementById("start-date").value;
            const end = document.getElementById("end-date").value;

            if (!start || !end) {
                alert("Please select both start and end dates.");
                return;
            }

            fetch(`/historical?start=${start}&end=${end}`)
                .then(res => res.json())
                .then(histData => {
                    if (histData.message) {
                        alert(histData.message);
                        return;
                    }

                    fetch(`/device_energy?start=${start}&end=${end}`)
                        .then(res => res.json())
                        .then(devData => {

                            // استدعاء بيانات الباور لكل جهاز
                            fetch(`/device_power?start=${start}&end=${end}`)
                                .then(res => res.json())
                                .then(powerData => {

                                    // إتلاف الرسوم القديمة إن وجدت
                                    if (historicalPowerChart) historicalPowerChart.destroy();
                                    if (historicalEnergyChart) historicalEnergyChart.destroy();

                                    // رسم مخطط Power لكل جهاز (line)
                                    const powerCtx = document.getElementById("historicalPowerChart").getContext("2d");
                                    historicalPowerChart = new Chart(powerCtx, {
                                        type: "line",
                                        data: {
                                            labels: powerData.labels,
                                            datasets: powerData.datasets.map(ds => ({
                                                label: ds.label,
                                                data: ds.data,
                                                borderColor: getRandomColor(),
                                                fill: false,
                                                tension: 0.4
                                            }))
                                        },
                                        options: {
                                            plugins: {
                                                legend: {
                                                    display: true,
                                                    position: "bottom"
                                                }
                                            },
                                            scales: {
                                                x: {
                                                    title: { display: true, text: "Time" },
                                                    ticks: { maxRotation: 45, minRotation: 30 },
                                                    grid: { display: false }
                                                },
                                                y: {
                                                    title: { display: true, text: "Power (W)" },
                                                    grid: { display: false }
                                                }
                                            }
                                        }
                                    });

                                    // رسم مخطط استهلاك الطاقة لكل جهاز (bar)
                                    const energyCtx = document.getElementById("historicalEnergyChart").getContext("2d");
                                    historicalEnergyChart = new Chart(energyCtx, {
                                        type: "bar",
                                        data: {
                                            labels: devData.device_names,
                                            datasets: [{
                                                label: "Energy Consumption (kWh)",
                                                data: devData.device_energy,
                                                backgroundColor: devData.device_energy.map(() => getRandomColor())
                                            }]

                                        },
                                        options: {
                                            indexAxis: 'x',
                                            plugins: { legend: { display: false } },
                                            scales: {
                                                x: {
                                                    title: { display: true, text: "Device" },
                                                    ticks: { autoSkip: false, maxRotation: 45, minRotation: 30 },
                                                    grid: { display: false }
                                                },
                                                y: {
                                                    title: { display: true, text: "Energy (kWh)" },
                                                    grid: { display: false }
                                                }
                                            }
                                        }
                                    });

                                    // تحديث القيم النصية
                                    const latestPower = histData.power[histData.power.length - 1];
                                    const totalEnergy = devData.device_energy.reduce((sum, val) => sum + val, 0).toFixed(2);

                                    document.getElementById("histPowerValue").textContent = `${latestPower} kW`;
                                    document.getElementById("histEnergyValue").textContent = `${totalEnergy} kWh`;
                                    document.getElementById("histPowerChange").textContent = `Today`;
                                    document.getElementById("histEnergyChange").textContent = `Today`;

                                })
                                .catch(err => {
                                    console.error("Error fetching /device_power data:", err);
                                    alert("Failed to load device power data.");
                                });

                        })
                        .catch(err => {
                            console.error("Error fetching /device_energy data:", err);
                            alert("Failed to load device energy data.");
                        });

                })
                .catch(err => {
                    console.error("Error fetching /historical data:", err);
                    alert("Failed to load historical data.");
                });
        }

        // دالة توليد لون عشوائي
        function getRandomColor() {
            const colors = ["#007bff", "#28a745", "#ffc107", "#dc3545", "#6f42c1", "#17a2b8", "#6610f2", "#fd7e14"];
            return colors[Math.floor(Math.random() * colors.length)];
        }

        window.addEventListener("load", () => {
            const powerCtx = document.getElementById('powerChart').getContext('2d');
            const energyCtx = document.getElementById('energyChart').getContext('2d');

            // تحميل بيانات اللايف من التخزين المحلي لو موجودة
            const savedData = loadLiveDataFromLocalStorage();

            powerChart = new Chart(powerCtx, {
                type: 'line',
                data: {
                    labels: savedData?.powerLabels || ['00:00', '00:05', '00:10', '00:15', '00:20', '00:25', '00:30'],
                    datasets: [{
                        data: savedData?.powerData || [],
                        borderColor: '#007bff',
                        tension: 0.4,
                        fill: false
                    }]
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { display: false, grid: { display: false }, ticks: { display: false } },
                        x: { display: true, grid: { display: false }, ticks: { display: true } }
                    }
                }
            });

            energyChart = new Chart(energyCtx, {
                type: 'bar',
                data: {
                    labels: savedData?.energyLabels || ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
                    datasets: [{
                        data: savedData?.energyData || [],
                        backgroundColor: '#007bff'
                    }]
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { display: false, grid: { display: false }, ticks: { display: false } },
                        x: { display: true, grid: { display: false }, ticks: { display: true } }
                    }
                }
            });

            tabs.forEach(tab => {
                tab.addEventListener("click", () => {
                    const tabName = tab.getAttribute("data-tab");
                    showTab(tabName);
                });
            });

            const firstTab = document.querySelector(".tab.active");
            if (firstTab) {
                showTab(firstTab.getAttribute("data-tab"));
            } else {
                showTab("live");
            }
        });

        window.generateHistoricalData = generateHistoricalData;
    }

    // ==========================
    // Reports (reports-page)
    // ==========================

    if (document.body.classList.contains('reports-page')) {

        let reportChartInstance = null;

        function destroyAndRecreateChart(chartId) {
            if (reportChartInstance) {
                reportChartInstance.destroy();
                reportChartInstance = null;
            }

            const oldCanvas = document.getElementById(chartId);
            const newCanvas = oldCanvas.cloneNode(true);
            oldCanvas.parentNode.replaceChild(newCanvas, oldCanvas);

            return newCanvas.getContext('2d');
        }

        function createReportChart(ctx, labels, data) {
            return new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Average Power (W)',
                        data: data,
                        backgroundColor: 'rgba(0, 0, 0, 0.7)',
                        borderColor: 'rgba(0, 0, 0, 1)',
                        borderWidth: 1,
                        borderRadius: 6,
                        barPercentage: 0.6,
                        categoryPercentage: 0.5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 1000,
                        easing: 'easeOutBounce'
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            enabled: true,
                            backgroundColor: '#fff',
                            titleColor: '#007bff',
                            bodyColor: '#000',
                            borderColor: '#007bff',
                            borderWidth: 1,
                            callbacks: {
                                label: function (context) {
                                    return `${context.raw} kWh`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                color: '#333',
                                font: { size: 12 }
                            }
                        },
                        y: {
                            grid: { display: false },   // ✅ أخفي خطوط الشبكة بالكامل
                            border: { display: false }, // ✅ أخفي الحدود الخارجية للمحور
                            ticks: { display: false }   // ✅ أخفي الأرقام من على المحور
                        }
                    }
                }
            });
        }


        function updateReportUI(data, reportType) {
            const titles = {
                daily: "Daily Report",
                weekly: "Weekly Report",
                monthly: "Monthly Report"
            };

            document.getElementById("reportTitle").textContent = titles[reportType] || "Report";
            document.getElementById("totalConsumption").textContent = `${data.total_consumption} kWh`;
            document.getElementById("avgConsumption").textContent = `${data.avg_consumption} kWh`;
            document.getElementById("peakConsumption").textContent = `${data.peak_consumption} kWh`;

            const ctx = destroyAndRecreateChart("reportChart");
            reportChartInstance = createReportChart(ctx, data.labels, data.avg_energy_data);
        }

        function activateTab(element) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            if (element) {
                element.classList.add('active');

                const underline = document.getElementById("tabUnderline");
                if (underline) {
                    underline.style.width = `${element.offsetWidth}px`;
                    underline.style.left = `${element.offsetLeft}px`;
                }
            }
        }

        function loadDeviceBreakdown(reportType) {
            fetch(`/report/device_breakdown/${reportType}`)
                .then(res => res.json())
                .then(result => {
                    const tableIds = {
                        daily: "deviceTableDaily",
                        weekly: "deviceTableWeekly",
                        monthly: "deviceTableMonthly"
                    };

                    const bodyIds = {
                        daily: "deviceTableBodyDaily",
                        weekly: "deviceTableBodyWeekly",
                        monthly: "deviceTableBodyMonthly"
                    };

                    // إخفاء كل الجداول
                    Object.values(tableIds).forEach(tableId => {
                        document.getElementById(tableId).style.display = "none";
                    });

                    // إظهار الجدول المطلوب
                    document.getElementById(tableIds[reportType]).style.display = "table";

                    const tableBody = document.getElementById(bodyIds[reportType]);
                    tableBody.innerHTML = "";

                    if (result.devices && result.devices.length > 0) {
                        result.devices.forEach(device => {
                            const row = document.createElement("tr");
                            row.innerHTML = `
                        <td>${device.device}</td>
                        <td>${device.consumption}</td>
                        <td>${device.cost}</td>
                    `;
                            tableBody.appendChild(row);
                        });
                    } else {
                        tableBody.innerHTML = '<tr><td colspan="3">No data available.</td></tr>';
                    }
                })
                .catch(err => {
                    console.error("Error loading device breakdown:", err);
                });
        }


        function generateReport(reportType, element) {
            activateTab(element);

            fetch(`/report/${reportType}`)
                .then(res => res.json())
                .then(data => {
                    if (data.message) {
                        alert(data.message);
                        return;
                    }
                    updateReportUI(data, reportType);
                    loadDeviceBreakdown(reportType);

                })
                .catch(err => {
                    console.error("Error fetching report:", err);
                });
        }

        window.generateReport = generateReport;
        generateReport('daily', document.querySelector('.tab'));
    }

});


function sendCommand(cmd) {
    fetch('/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
    })
        .then(() => {
            console.log("Command sent:", cmd);
            updateButtons(cmd);
        })
        .catch(error => {
            console.error('Error sending command:', error);
            alert('Failed to send the command. Please check the server or try again later.');
        });
}

function updateButtons(active) {
    const onBtn = document.getElementById('on-btn');
    const offBtn = document.getElementById('off-btn');

    if (active === 'on') {
        onBtn.style.backgroundColor = 'green';
        onBtn.style.color = 'white';
        offBtn.style.backgroundColor = 'lightgray';
        offBtn.style.color = 'black';
    } else {
        offBtn.style.backgroundColor = 'red';
        offBtn.style.color = 'white';
        onBtn.style.backgroundColor = 'lightgray';
        onBtn.style.color = 'black';
    }
}
const notificationHistory = [];


function addNotification(message) {
    // لو الإشعار اتكرر، منضيفوش
    if (notificationHistory.includes(message)) return;

    // أضف الرسالة لأول القائمة
    notificationHistory.unshift(message);

    const list = document.getElementById('notification-list');
    if (!list) return;

    const li = document.createElement('li');
    li.textContent = message;
    list.prepend(li);
}


function toggleNotificationPopup() {
    const popup = document.getElementById('notification-popup');
    if (!popup) return;

    popup.style.display = (popup.style.display === 'none') ? 'block' : 'none';
}

let lastPowerAlert = false;
// To prevent repeated notifications

function pollData() {
    Promise.all([
        fetch('/esp_command').then(res => res.json()),
        fetch('/latest').then(res => res.json()),
        fetch('/esp_limit').then(res => res.json())
    ])
        .then(([commandData, latestData, limitData]) => {
            const power = latestData.power.current;
            const command = commandData.command;  // 'on' or 'off'
            const powerState = power > 0 ? 'on' : 'off';

            const powerLimit = limitData.power_limit;

            // تحديد الحالة الحقيقية للجهاز بناءً على الأمر والتيار الفعلي

            // تحديث الأزرار فقط في صفحة الإعدادات


            // Notification: device is ON but no power
            if (command === 'on' && powerState === 'on') {
                addNotification(" ❇️ Device is ON ");
                if (document.body.classList.contains('settings-page')) {
                    updateButtons('on');
                }
            }
            if (powerState === 'on') {
                addNotification(" ❇️ Device is ON ");
                if (document.body.classList.contains('settings-page')) {
                    updateButtons('on');
                }
            }

            // Notification: device is OFF but still using power
            if (command === 'off' && powerState === 'off') {
                addNotification("⚠️ Device is OFF ");
                if (document.body.classList.contains('settings-page')) {
                    updateButtons('off');
                }
            }
            // Notification: device is OFF but still using power
            if (powerState === 'off') {
                addNotification("⚠️ Device is OFF ");
                if (document.body.classList.contains('settings-page')) {
                    updateButtons('off');
                }
            }

            // Notification: power exceeded limit
            if (power > powerLimit) {
                if (!lastPowerAlert) {
                    addNotification(`🚨 Power exceeded safe limit! Current: ${power} W (Limit: ${powerLimit} W)`);
                    lastPowerAlert = true;
                }
            } else {
                lastPowerAlert = false;
            }

        })
        .catch(err => console.error('Error polling data:', err));
}


// ← تشغيل كل ثانية
setInterval(pollData, 1000);
pollData();




function submitPowerLimit() {
    const input = document.getElementById('power-limit');
    const powerLimit = parseFloat(input.value);

    if (isNaN(powerLimit)) {
        alert("Please enter a valid number.");
        return;
    }

    fetch('/set_limit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: powerLimit })
    })
        .then(res => res.json())
        .then(data => {
            console.log("Power limit sent:", powerLimit);
            document.getElementById('ww').innerText = `${powerLimit} W`;
        })
        .catch(error => {
            console.error('Error sending power limit:', error);
        });
}

let timerPaused = false;
let remainingSeconds = 0;
let countdownInterval; // Global variable to track the countdown interval

function startTimer() {
    const minutes = parseInt(document.getElementById("timer-duration").value);
    if (isNaN(minutes) || minutes <= 0) {
        alert("Enter valid minutes");
        return;
    }

    fetch('/set_timer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration_minutes: minutes })
    })
        .then(res => res.text())
        .then(response => {
            console.log(response);
            startCountdown(minutes * 60); // Convert to seconds
        })
        .catch(err => {
            console.error("Error", err);
        });
}

function startCountdown(seconds) {
    clearInterval(countdownInterval); // Clear previous if any

    countdownInterval = setInterval(() => {
        if (timerPaused) return;
        let hrs = Math.floor(seconds / 3600);
        let mins = Math.floor((seconds % 3600) / 60);
        let secs = seconds % 60;

        document.getElementById("hours").value = String(hrs).padStart(2, '0');
        document.getElementById("minutes").value = String(mins).padStart(2, '0');
        document.getElementById("seconds").value = String(secs).padStart(2, '0');

        remainingSeconds = seconds;

        if (seconds <= 0) {
            clearInterval(countdownInterval);
            setTimeout(() => {
                document.getElementById("hours").value = "00";
                document.getElementById("minutes").value = "00";
                document.getElementById("seconds").value = "00";
            }, 1000);
            // إخفاء زر Pause و Cancel وإظهار زر Set Time
            document.getElementById("set-time-btn").style.display = "inline-block";
            document.getElementById("pause-btn").style.display = "none";
            document.getElementById("cancel-btn").style.display = "none";
            return;
        }

        seconds--;
    }, 1000);
}

function stopTimer() {
    clearInterval(countdownInterval);
    document.getElementById("timer").style.backgroundColor = "";
    document.getElementById("timer").style.border = "";
    var stopBtn = document.querySelector('button[onclick="stopTimer()"]');
    if (stopBtn) {
        stopBtn.style.backgroundColor = "#b71c1c";
        stopBtn.style.color = "#fff";
        setTimeout(function () {
            stopBtn.style.backgroundColor = "";
            stopBtn.style.color = "";
        }, 700);
    }
}
function onSetTimeClick() {
    // إخفاء زر Set Time
    document.getElementById("set-time-btn").style.display = "none";
    // إظهار زري Pause و Cancel
    document.getElementById("pause-btn").style.display = "inline-block";
    document.getElementById("cancel-btn").style.display = "inline-block";

    startTimer();
}

function onPauseClick() {
    const pauseBtn = document.getElementById("pause-btn");
    if (!timerPaused) {
        timerPaused = true;
        pauseBtn.textContent = "Resume";
        clearInterval(countdownInterval);
        fetch('/pause_timer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(res => res.json())
            .then(data => {
                console.log("Timer paused on server:", data);
            })
            .catch(err => {
                console.error("Error pausing timer on server:", err);
            });
    } else {
        timerPaused = false;
        pauseBtn.textContent = "Pause";
        startCountdown(remainingSeconds);
        fetch('/resume_timer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(res => res.json())
            .then(data => {
                console.log("Timer resumed on server:", data);
            })
            .catch(err => {
                console.error("Error resuming timer on server:", err);
            });
    }
}

function onCancelClick() {
    document.getElementById("set-time-btn").style.display = "inline-block";
    document.getElementById("pause-btn").style.display = "none";
    document.getElementById("cancel-btn").style.display = "none";

    clearInterval(countdownInterval);
    timerPaused = false;
    remainingSeconds = 0;

    // Reset the timer display
    document.getElementById("hours").value = "00";
    document.getElementById("minutes").value = "00";
    document.getElementById("seconds").value = "00";

    // إرسال طلب إلى الخادم لتصفير المؤقت في ملف JSON
    fetch('/reset_timer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reset: true })
    })
        .then(res => res.json())
        .then(data => {
            console.log("Timer reset on server:", data);
        })
        .catch(err => {
            console.error("Error resetting timer on server:", err);
        });
}

function fetchTimer() {
    fetch('/get_timer')
        .then(res => res.json())
        .then(data => {
            // تحديث العداد بناءً على البيانات القادمة من السيرفر
            let seconds = data.remaining_seconds || 0;
            let hrs = Math.floor(seconds / 3600);
            let mins = Math.floor((seconds % 3600) / 60);
            let secs = seconds % 60;
            document.getElementById("hours").value = String(hrs).padStart(2, '0');
            document.getElementById("minutes").value = String(mins).padStart(2, '0');
            document.getElementById("seconds").value = String(secs).padStart(2, '0');
        })
        .catch(err => {
            console.error("Error fetching timer:", err);
        });
}
window.addEventListener('DOMContentLoaded', function () {

    function fetchPowerLimit() {
        fetch('/esp_limit')
            .then(res => res.json())
            .then(data => {
                if ('power_limit' in data) {
                    powerLimit = parseFloat(data.power_limit); // ← نخزنها هنا

                    const wwEl = document.getElementById('ww');
                    if (wwEl) {
                        wwEl.innerText = `${powerLimit} W`;
                    }
                } else {
                    powerLimit = null;
                    const wwEl = document.getElementById('ww');
                    if (wwEl) {
                        wwEl.innerText = '--';
                    }
                }
            })
            .catch(error => {
                console.error('Error fetching power limit:', error);
                powerLimit = null;
                const wwEl = document.getElementById('ww');
                if (wwEl) {
                    wwEl.innerText = '--';
                }
            });
    }


    function fetchRemainingTime() {
        fetch('/get_timer')
            .then(res => res.json())
            .then(data => {
                const remaining = parseInt(data.remaining_seconds);
                const hoursEl = document.getElementById("hours");
                const minutesEl = document.getElementById("minutes");
                const secondsEl = document.getElementById("seconds");
                if (hoursEl && minutesEl && secondsEl) {
                    if (!isNaN(remaining) && remaining > 0) {
                        let hrs = Math.floor(remaining / 3600);
                        let mins = Math.floor((remaining % 3600) / 60);
                        let secs = remaining % 60;
                        hoursEl.value = String(hrs).padStart(2, '0');
                        minutesEl.value = String(mins).padStart(2, '0');
                        secondsEl.value = String(secs).padStart(2, '0');
                    } else {
                        // إذا المؤقت خلص أو مش موجود
                        hoursEl.value = "00";
                        minutesEl.value = "00";
                        secondsEl.value = "00";
                    }
                }
            })
            .catch(error => {
                console.error('Error fetching timer:', error);
                const hoursEl = document.getElementById("hours");
                const minutesEl = document.getElementById("minutes");
                const secondsEl = document.getElementById("seconds");
                if (hoursEl && minutesEl && secondsEl) {
                    hoursEl.value = "--";
                    minutesEl.value = "--";
                    secondsEl.value = "--";
                }
            });
    }

    // أول مرة
    fetchPowerLimit();
    fetchRemainingTime();

    // كل 2 ثانية
    setInterval(fetchPowerLimit, 2000);
    setInterval(fetchRemainingTime, 1000); // التايمر كل ثانية

});

// ==========================
// Contact Form (contact-page)
// ==========================
document.addEventListener('DOMContentLoaded', function () {
    if (document.body.classList.contains('contact-page')) {
        const contactForm = document.getElementById('contactForm');
        if (contactForm) {
            contactForm.addEventListener('submit', function (e) {
                e.preventDefault();

                const name = document.getElementById('name').value;
                const email = document.getElementById('email').value;
                const subject = document.getElementById('subject').value;

                const message = document.getElementById('message').value;

                fetch('/contact_message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, subject, message })
                })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') {
                            alert('Your message has been sent successfully!');
                            contactForm.reset();
                        } else {
                            alert('An error occurred while sending. Please try again.');
                        }
                    })
                    .catch(err => {
                        alert('Unable to connect to the server.');
                        console.error(err);
                    });
            });
        }
    }
});
