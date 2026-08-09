/**
 * AKI 2035 Futuristic AI OS - Dashboard UI Controller
 * Integrates with PySide6 backend via QWebChannel with automatic browser fallback.
 */

(function () {
    "use strict";

    // Global Bridge Reference
    let bridge = null;
    let isWebChannelConnected = false;

    // UI Element References
    const elements = {
        clockTime: document.getElementById("clockTime"),
        clockDate: document.getElementById("clockDate"),
        uptimeVal: document.getElementById("uptimeVal"),
        
        cpuVal: document.getElementById("cpuVal"),
        cpuBar: document.getElementById("cpuBar"),
        ramVal: document.getElementById("ramVal"),
        ramBar: document.getElementById("ramBar"),
        processRamVal: document.getElementById("processRamVal"),
        
        aiStatusBadge: document.getElementById("aiStatusBadge"),
        aiFreqVal: document.getElementById("aiFreqVal"),
        aiHeartbeatVal: document.getElementById("aiHeartbeatVal"),
        aiNeuralLoadVal: document.getElementById("aiNeuralLoadVal"),
        aiThreadsVal: document.getElementById("aiThreadsVal"),

        reactorLoad: document.getElementById("reactorLoad"),

        memAllocVal: document.getElementById("memAllocVal"),
        memVectorVal: document.getElementById("memVectorVal"),
        
        automationTasksVal: document.getElementById("automationTasksVal"),
        automationStatusVal: document.getElementById("automationStatusVal"),
        
        consoleLogs: document.getElementById("consoleLogs"),
        
        btnDiagnostics: document.getElementById("btnDiagnostics"),
        btnRefresh: document.getElementById("btnRefresh"),
        
        btnMin: document.getElementById("btnMin"),
        btnMax: document.getElementById("btnMax"),
        btnClose: document.getElementById("btnClose")
    };

    // Initialize System Clock
    function startLiveClock() {
        function updateClock() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            
            if (elements.clockTime) {
                elements.clockTime.textContent = `${hours}:${minutes}:${seconds}`;
            }

            if (elements.clockDate) {
                const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
                elements.clockDate.textContent = now.toLocaleDateString('en-US', options).toUpperCase();
            }
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    // Append Cyber Telemetry Console Entry
    function appendLog(msg, type = "info") {
        if (!elements.consoleLogs) return;
        
        const now = new Date();
        const timestamp = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0').slice(0,2);
        
        const logEntry = document.createElement("div");
        logEntry.className = `log-entry ${type}`;
        logEntry.innerHTML = `<span class="log-time">[${timestamp}]</span> <span class="log-msg">${msg}</span>`;
        
        elements.consoleLogs.appendChild(logEntry);
        elements.consoleLogs.scrollTop = elements.consoleLogs.scrollHeight;

        // Keep last 30 log lines
        while (elements.consoleLogs.children.length > 30) {
            elements.consoleLogs.removeChild(elements.consoleLogs.firstChild);
        }
    }

    // Update Telemetry UI Payload
    function renderTelemetry(data) {
        if (!data) return;

        // System Telemetry
        if (data.system) {
            const cpu = data.system.cpu_percent || 0;
            const ram = data.system.ram_percent || 0;

            if (elements.cpuVal) elements.cpuVal.textContent = `${cpu}%`;
            if (elements.cpuBar) elements.cpuBar.style.width = `${cpu}%`;

            if (elements.ramVal) elements.ramVal.textContent = `${ram}% (${data.system.ram_used_gb || 0} / ${data.system.ram_total_gb || 0} GB)`;
            if (elements.ramBar) elements.ramBar.style.width = `${ram}%`;

            if (elements.processRamVal) elements.processRamVal.textContent = `${data.system.process_ram_mb || 0} MB`;
            
            if (elements.reactorLoad) elements.reactorLoad.textContent = `${Math.min(100, Math.round(cpu * 0.8 + 15))}%`;
        }

        // Uptime
        if (data.uptime && elements.uptimeVal) {
            elements.uptimeVal.textContent = data.uptime;
        }

        // AI Core Status
        if (data.ai_core) {
            if (elements.aiFreqVal) elements.aiFreqVal.textContent = `${data.ai_core.frequency_ghz || 3.82} GHz`;
            if (elements.aiHeartbeatVal) elements.aiHeartbeatVal.textContent = data.ai_core.heartbeat || 0;
            if (elements.aiNeuralLoadVal) elements.aiNeuralLoadVal.textContent = `${data.ai_core.neural_load_percent || 0}%`;
            if (elements.aiThreadsVal) elements.aiThreadsVal.textContent = data.ai_core.active_threads || 8;
        }

        // Memory Subsystem
        if (data.memory_subsystem) {
            if (elements.memAllocVal) elements.memAllocVal.textContent = `${data.memory_subsystem.allocated_mb || 0} MB`;
            if (elements.memVectorVal) elements.memVectorVal.textContent = data.memory_subsystem.vector_index_size || "1,024 Nodes";
        }

        // Automation
        if (data.automation) {
            if (elements.automationTasksVal) elements.automationTasksVal.textContent = `${data.automation.active_tasks || 0} Active`;
            if (elements.automationStatusVal) elements.automationStatusVal.textContent = data.automation.status || "READY";
        }
    }

    // Connect to Qt WebChannel
    function initWebChannel() {
        if (typeof qt !== "undefined" && typeof QWebChannel !== "undefined") {
            new QWebChannel(qt.webChannelTransport, function (channel) {
                bridge = channel.objects.aki_bridge;
                if (bridge) {
                    isWebChannelConnected = true;
                    appendLog("QWebChannel connected to AKI Python Core.", "success");

                    // Connect telemetry signal
                    bridge.telemetryUpdated.connect(function (data) {
                        renderTelemetry(data);
                    });

                    // Fetch initial snapshot
                    bridge.getSystemTelemetry(function (data) {
                        renderTelemetry(data);
                    });

                    // Hook Window Controls
                    if (elements.btnMin) elements.btnMin.onclick = () => bridge.minimizeWindow();
                    if (elements.btnMax) elements.btnMax.onclick = () => bridge.maximizeWindow();
                    if (elements.btnClose) elements.btnClose.onclick = () => bridge.closeWindow();
                    if (elements.btnDiagnostics) {
                        elements.btnDiagnostics.onclick = () => {
                            appendLog("Initiating Cyber Diagnostics scan...", "info");
                            bridge.triggerDiagnosticScan("full", function (result) {
                                appendLog(`Diagnostics Complete: Threats: ${result.threats_found}, Integrity: ${result.integrity}`, "success");
                            });
                        };
                    }
                }
            });
        } else {
            // Standalone Browser Preview Mode
            appendLog("Running in Browser Standalone Mode (Simulated Telemetry).", "info");
            startSimulatedTelemetry();

            if (elements.btnDiagnostics) {
                elements.btnDiagnostics.onclick = () => {
                    appendLog("Simulated Diagnostics Scan Executed.", "success");
                };
            }
        }
    }

    // Simulated Telemetry for Browser Preview
    function startSimulatedTelemetry() {
        let heartbeat = 0;
        let startSec = Math.floor(Date.now() / 1000);

        setInterval(() => {
            heartbeat++;
            const elapsed = Math.floor(Date.now() / 1000) - startSec;
            const hours = String(Math.floor(elapsed / 3600)).padStart(2, '0');
            const mins = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
            const secs = String(elapsed % 60).padStart(2, '0');
            
            const fakeCpu = Math.round(18 + Math.sin(heartbeat * 0.4) * 12 + Math.random() * 5);
            const fakeRam = Math.round(42 + Math.cos(heartbeat * 0.2) * 4);

            renderTelemetry({
                uptime: `${hours}:${mins}:${secs}`,
                system: {
                    cpu_percent: fakeCpu,
                    cpu_count: 8,
                    ram_percent: fakeRam,
                    ram_used_gb: (16 * (fakeRam / 100)).toFixed(1),
                    ram_total_gb: 16.0,
                    process_ram_mb: (140 + fakeCpu * 2).toFixed(1),
                    status_label: "NOMINAL"
                },
                ai_core: {
                    status: "ONLINE",
                    heartbeat: heartbeat,
                    frequency_ghz: (3.8 + (heartbeat % 5) * 0.04).toFixed(2),
                    active_threads: 8,
                    neural_load_percent: Math.round(fakeCpu * 0.8 + 10)
                },
                memory_subsystem: {
                    allocated_mb: 184.2,
                    vector_index_size: "1,024 Nodes"
                },
                automation: {
                    active_tasks: 0,
                    status: "READY"
                }
            });

            if (heartbeat % 8 === 0) {
                appendLog(`AI Quantum Core ping: ${fakeCpu}% CPU // ${fakeRam}% RAM`, "info");
            }
        }, 1500);
    }

    // DOM Ready Bootstrap
    document.addEventListener("DOMContentLoaded", function () {
        startLiveClock();
        appendLog("AKI 2035 Neural Interface initialized.", "success");
        initWebChannel();
    });

})();
