/**
 * AKI 2035 Desktop AI Operating System - Master OS Shell Controller
 * Connects PySide6 QWebChannel IPC to the hero workspace, multi-view stack, sound engine, and native window behaviors.
 */

(function () {
    "use strict";

    let bridge = null;
    let isVoiceListening = false;
    let currentAttachedFile = "";
    let lastHoveredElement = null;
    let orbSpeakTimer = null;
    let activeTypingBubble = null;
    let activeRequestId = "";

    // DOM Elements Cache
    const elements = {
        osClockTime: document.getElementById("osClockTime"),
        osClockDate: document.getElementById("osClockDate"),
        greetingTitle: document.getElementById("greetingTitle"),
        
        osCpuVal: document.getElementById("osCpuVal"),
        osRamVal: document.getElementById("osRamVal"),
        osGpuVal: document.getElementById("osGpuVal"),
        osHealthLabel: document.getElementById("osHealthLabel"),
        
        cmdInput: document.getElementById("cmdInput"),
        btnVoice: document.getElementById("btnVoice"),
        btnAttach: document.getElementById("btnAttach"),
        btnSubmit: document.getElementById("btnSubmit"),
        attachmentPill: document.getElementById("attachmentPill"),
        attachmentName: document.getElementById("attachmentName"),
        waveformContainer: document.getElementById("waveformContainer"),
        
        btnMin: document.getElementById("btnMin"),
        btnMax: document.getElementById("btnMax"),
        btnClose: document.getElementById("btnClose"),
        btnSoundToggle: document.getElementById("btnSoundToggle"),

        chatInput: document.getElementById("chatInput"),
        btnChatSubmit: document.getElementById("btnChatSubmit")
    };

    // 1. Adaptive Greeting & Live System Clock
    function updateClockAndGreeting() {
        const now = new Date();
        const hoursNum = now.getHours();
        const hours = String(hoursNum).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        
        if (elements.osClockTime) {
            elements.osClockTime.textContent = `${hours}:${minutes}:${seconds}`;
        }
        if (elements.osClockDate) {
            const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
            elements.osClockDate.textContent = now.toLocaleDateString('en-US', options).toUpperCase();
        }

        // Adaptive Greeting for User AETHER
        if (elements.greetingTitle) {
            let greeting = "Good Evening, AETHER";
            if (hoursNum < 12) {
                greeting = "Good Morning, AETHER";
            } else if (hoursNum < 18) {
                greeting = "Good Afternoon, AETHER";
            }
            elements.greetingTitle.textContent = greeting;
        }
    }

    // 2. Real-time Telemetry Renderer
    function renderTelemetry(data) {
        if (!data || !data.system) return;

        const cpu = data.system.cpu_percent || 18;
        const ram = data.system.ram_percent || 32;
        const gpu = Math.round(cpu * 0.6 + 6);

        if (elements.osCpuVal) elements.osCpuVal.textContent = `${cpu}%`;
        if (elements.osRamVal) elements.osRamVal.textContent = `${ram}%`;
        if (elements.osGpuVal) elements.osGpuVal.textContent = `${gpu}%`;
        if (elements.osHealthLabel) elements.osHealthLabel.textContent = data.system.status_label || "EXCELLENT";
    }

    // 3. Multi-View Stack Navigation Manager
    function switchView(targetViewId) {
        const allViews = document.querySelectorAll(".os-view-panel");
        const allNavBtns = document.querySelectorAll(".os-nav-icon");

        allViews.forEach(view => {
            if (view.id === targetViewId) {
                view.classList.add("active");
            } else {
                view.classList.remove("active");
            }
        });

        allNavBtns.forEach(btn => {
            if (btn.dataset.targetView === targetViewId) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });
    }

    // 4. File Attachment Handler
    function handleSelectAttachment() {
        if (bridge && typeof bridge.selectAttachment === "function") {
            bridge.selectAttachment().then(result => {
                if (result && result.selected) {
                    currentAttachedFile = result.name;
                    if (elements.attachmentName) elements.attachmentName.textContent = result.name;
                    if (elements.attachmentPill) elements.attachmentPill.classList.add("active");
                    if (window.AKISound) window.AKISound.playNotification();
                }
            });
        } else {
            // Browser preview simulated file upload
            currentAttachedFile = "project_spec.py";
            if (elements.attachmentName) elements.attachmentName.textContent = currentAttachedFile;
            if (elements.attachmentPill) elements.attachmentPill.classList.add("active");
            if (window.AKISound) window.AKISound.playNotification();
        }
    }

    function clearAttachment() {
        currentAttachedFile = "";
        if (elements.attachmentPill) elements.attachmentPill.classList.remove("active");
    }

    // 5. Orb Intelligence State Machine
    // Drives the reactor visual states: idle -> thinking -> speaking -> idle.
    function setOrbState(state) {
        const core = document.querySelector(".aki-core-container");
        if (!core) return;

        core.classList.remove("state-thinking", "state-speaking");
        if (state === "thinking" || state === "speaking") {
            core.classList.add("state-" + state);
        }

        const waveform = document.querySelector(".aki-waveform");
        if (waveform) {
            waveform.classList.toggle("waveform-speaking", state === "speaking");
        }
    }

    function estimateSpeakDurationMs(text) {
        // Roughly 2.5 words per second, clamped to a natural range.
        const words = String(text).trim().split(/\s+/).length;
        return Math.max(1400, Math.min(900 + words * 260, 8000));
    }

    function speakResponse(text) {
        setOrbState("speaking");
        if (window.AKISound) window.AKISound.playVoice();

        if (orbSpeakTimer) clearTimeout(orbSpeakTimer);
        orbSpeakTimer = setTimeout(() => setOrbState("idle"), estimateSpeakDurationMs(text));
    }

    // 6. Execute Command & Append Chat Response
    function executeCommand(customText, options) {
        const fromKeyboard = !!(options && options.fromKeyboard);
        let query = customText || (elements.cmdInput ? elements.cmdInput.value.trim() : "");
        if (!query && elements.chatInput) {
            query = elements.chatInput.value.trim();
        }

        if (!query) return;

        if (fromKeyboard && window.AKISound) window.AKISound.playClick();

        if (elements.cmdInput) elements.cmdInput.value = "";
        if (elements.chatInput) elements.chatInput.value = "";

        // Append to Chat view
        appendChatMessage("user", query, currentAttachedFile);
        setOrbState("thinking");
        activeRequestId = "";
        dismissTypingIndicator();
        activeTypingBubble = showTypingIndicator();

        const activeAttachment = currentAttachedFile;
        clearAttachment();

        // Process response
        if (bridge && typeof bridge.sendAiPrompt === "function") {
            bridge.sendAiPrompt(query, activeAttachment).then(res => {
                if (!res) return;

                if (res.status === "PENDING") {
                    // Real AI working in background; reply arrives via aiResponseReady.
                    if (res.request_id) activeRequestId = res.request_id;
                    return;
                }

                handleAiPayload(res);
            });
        } else {
            // Simulated AI Response (browser preview mode)
            setTimeout(() => {
                const fakeResponses = [
                    `AKI OS Core initialized. Running operation: "${query}". All systems nominal.`,
                    `Analyzed query "${query}". Autonomous workflow activated. System efficiency optimized.`,
                    `JARVIS Protocol engaged for "${query}". Screen and memory context synchronized.`
                ];
                const reply = fakeResponses[Math.floor(Math.random() * fakeResponses.length)];
                deliverReply(reply);
            }, 900 + Math.floor(Math.random() * 700));
        }
    }

    function handleAiPayload(payload) {
        if (!payload || !payload.response) return;

        // Drop stale replies from an older request.
        if (
            payload.request_id &&
            activeRequestId &&
            payload.request_id !== activeRequestId
        ) {
            return;
        }

        deliverReply(payload.response);
    }

    function deliverReply(text) {
        dismissTypingIndicator();
        appendChatMessage("aki", text);
        speakResponse(text);
    }

    function getChatPanel() {
        return document.getElementById("chatPanel");
    }

    function getChatMessages() {
        return document.getElementById("chatMessages");
    }

    function showTypingIndicator() {
        const feed = getChatMessages();
        if (!feed) return null;

        getChatPanel().classList.add("visible");

        const bubble = document.createElement("div");
        bubble.className = "os-chat-bubble typing";
        bubble.innerHTML = "<span class='dot'></span><span class='dot'></span><span class='dot'></span>";
        feed.appendChild(bubble);
        feed.scrollTop = feed.scrollHeight;

        return bubble;
    }

    function dismissTypingIndicator() {
        if (activeTypingBubble && activeTypingBubble.parentNode) {
            activeTypingBubble.parentNode.removeChild(activeTypingBubble);
        }
        activeTypingBubble = null;
    }

    function appendChatMessage(sender, text, attachmentName) {
        const feed = getChatMessages();
        if (!feed) return;

        getChatPanel().classList.add("visible");

        const bubble = document.createElement("div");
        bubble.className = `os-chat-bubble ${sender}`;

        let content = text;
        if (attachmentName) {
            content += `<br><span style="font-family: var(--os-font-mono); font-size: 11px; color: var(--os-cyan);">📎 Attached: ${attachmentName}</span>`;
        }

        bubble.innerHTML = content;
        feed.appendChild(bubble);
        feed.scrollTop = feed.scrollHeight;
    }

    function clearConversation() {
        dismissTypingIndicator();
        activeRequestId = "";
        setOrbState("idle");

        const feed = getChatMessages();
        if (feed) feed.innerHTML = "";

        const panel = getChatPanel();
        if (panel) panel.classList.remove("visible");

        if (bridge && typeof bridge.clearConversation === "function") {
            bridge.clearConversation();
        }
        if (window.AKISound) window.AKISound.playClick();
    }

    // 6. Voice Mode Toggle
    function toggleVoice() {
        isVoiceListening = !isVoiceListening;
        if (window.AKISound) window.AKISound.playVoice();

        if (elements.btnVoice) {
            elements.btnVoice.style.background = isVoiceListening ? "var(--os-cyan)" : "";
            elements.btnVoice.style.color = isVoiceListening ? "#030712" : "";
        }
        if (elements.waveformContainer) {
            elements.waveformContainer.style.opacity = isVoiceListening ? "1" : "0.5";
        }
    }

    // 7. QWebChannel Setup
    function initWebChannel() {
        if (typeof qt !== "undefined" && typeof QWebChannel !== "undefined") {
            new QWebChannel(qt.webChannelTransport, function (channel) {
                bridge = channel.objects.aki_bridge;
                if (bridge) {
                    bridge.telemetryUpdated.connect(renderTelemetry);
                    bridge.getSystemTelemetry().then(renderTelemetry);

                bridge.windowStateChanged.connect(state => {
                    if (elements.btnMax) {
                        elements.btnMax.textContent = state === "maximized" ? "❐" : "▢";
                    }
                });

                // Real AI replies arrive here from the Python worker thread.
                bridge.aiResponseReady.connect(handleAiPayload);

                    if (elements.btnMin) elements.btnMin.onclick = () => bridge.minimizeWindow();
                    if (elements.btnMax) elements.btnMax.onclick = () => bridge.maximizeWindow();
                    if (elements.btnClose) elements.btnClose.onclick = () => bridge.closeWindow();
                }
            });
        } else {
            // Simulated telemetry for browser mode
            setInterval(() => {
                const fakeCpu = Math.round(16 + Math.sin(Date.now() / 2500) * 8);
                const fakeRam = Math.round(32 + Math.cos(Date.now() / 3500) * 4);
                renderTelemetry({ system: { cpu_percent: fakeCpu, ram_percent: fakeRam, status_label: "EXCELLENT" } });
            }, 2000);
        }
    }

    // 8. Global Sound Feedback (EDITH-style)
    // Event delegation covers every current and future interactive
    // element instead of binding listeners per node at startup.
    const HOVER_SOUND_SELECTOR = [
        "button",
        ".aki-glass-chip",
        ".aki-nav-btn",
        ".aki-dock-item",
        ".aki-win-btn",
        ".aki-glass-panel",
        ".aki-topbar-icon",
        ".aki-cmd-voice",
        ".aki-events-list li"
    ].join(", ");

    function isSoundInteractive(node) {
        return !!(node && node.closest && node.closest(HOVER_SOUND_SELECTOR));
    }

    function attachSoundEffects() {
        document.addEventListener("pointerover", (event) => {
            const target = event.target;
            if (!isSoundInteractive(target)) return;

            const element = target.closest(HOVER_SOUND_SELECTOR);
            if (element === lastHoveredElement) return;

            lastHoveredElement = element;
            if (window.AKISound) window.AKISound.playHover();
        });

        document.addEventListener("pointerout", (event) => {
            if (
                lastHoveredElement &&
                event.relatedTarget &&
                lastHoveredElement.contains(event.relatedTarget)
            ) {
                return;
            }
            lastHoveredElement = null;
        });

        document.addEventListener("click", (event) => {
            if (isSoundInteractive(event.target)) {
                if (window.AKISound) window.AKISound.playClick();
            }
        });
    }

    // DOM Ready Initialization
    document.addEventListener("DOMContentLoaded", function () {
        updateClockAndGreeting();
        setInterval(updateClockAndGreeting, 1000);
        initWebChannel();
        attachSoundEffects();

        // Sound Boot Riser
        setTimeout(() => {
            if (window.AKISound) window.AKISound.playBoot();
        }, 300);

        // View Switchers
        document.querySelectorAll(".os-nav-icon").forEach(btn => {
            btn.addEventListener("click", function () {
                const targetView = this.dataset.targetView;
                if (targetView) switchView(targetView);
            });
        });

        // Event Listeners
        if (elements.btnSubmit) elements.btnSubmit.onclick = () => executeCommand();
        if (elements.btnChatSubmit) elements.btnChatSubmit.onclick = () => executeCommand();
        if (elements.btnVoice) elements.btnVoice.onclick = () => toggleVoice();
        if (elements.btnAttach) elements.btnAttach.onclick = () => handleSelectAttachment();

        const btnChatClear = document.getElementById("btnChatClear");
        if (btnChatClear) btnChatClear.onclick = () => clearConversation();

        if (elements.cmdInput) {
            elements.cmdInput.onkeydown = (e) => {
                if (e.key === "Enter") executeCommand(null, { fromKeyboard: true });
            };
        }
        if (elements.chatInput) {
            elements.chatInput.onkeydown = (e) => {
                if (e.key === "Enter") executeCommand(null, { fromKeyboard: true });
            };
        }

        // Sound Toggle Button
        if (elements.btnSoundToggle) {
            elements.btnSoundToggle.onclick = () => {
                const enabled = window.AKISound ? window.AKISound.toggle() : false;
                elements.btnSoundToggle.textContent = enabled ? "🔊" : "🔇";
            };
        }

        // Titlebar native double click and drag fallback
        const topbar = document.querySelector(".aki-layout-topbar");
        if (topbar) {
            topbar.addEventListener("dblclick", (e) => {
                if (e.target.closest(".aki-win-btn, .aki-topbar-icon, button, input")) return;
                if (bridge && typeof bridge.maximizeWindow === "function") {
                    bridge.maximizeWindow();
                }
            });
            topbar.addEventListener("mousedown", (e) => {
                if (e.target.closest(".aki-win-btn, .aki-topbar-icon, button, input")) return;
                if (e.button === 0 && bridge && typeof bridge.startWindowMove === "function") {
                    bridge.startWindowMove();
                }
            });
        }

        // Quick action pills
        document.querySelectorAll(".aki-glass-chip").forEach(pill => {
            pill.onclick = () => {
                const query = pill.textContent.trim();
                executeCommand(query);
            };
        });
    });

})();
