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
    let mediaRecorder = null;
    let audioChunks = [];
    let voiceOutputEnabled = true;
    let recordingStartedAt = 0;
    let micAlwaysOn = false;
    let micEverEngaged = false;
    let micStream = null;
    let silenceTimer = null;
    let audioContext = null;
    let speechDetected = false;

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

        // Adaptive Greeting for User SALAAR
        if (elements.greetingTitle) {
            let greeting = "Good Evening, SALAAR";
            if (hoursNum < 12) {
                greeting = "Good Morning, SALAAR";
            } else if (hoursNum < 18) {
                greeting = "Good Afternoon, SALAAR";
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

        // Typing indicator always sits at the very bottom of the flow.
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

    // Safe mini-markdown renderer: ChatGPT-style bubbles without raw ** **.
    function renderMarkdown(raw) {
        let text = String(raw || "");

        // Escape HTML first — never trust model output.
        text = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Fenced code blocks.
        text = text.replace(/```([\s\S]*?)```/g, (match, code) => {
            return `<pre class="os-code">${code.replace(/^\n+|\n+$/g, "")}</pre>`;
        });

        // Inline code.
        text = text.replace(/`([^`\n]+)`/g, '<code class="os-inline-code">$1</code>');

        // Bold, then italics.
        text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        text = text.replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>");

        // Numbered and bullet lists -> indented lines with markers kept.
        text = text.replace(/(^|\n)\s*(\d+\.)\s+/g, "$1<span class='os-li-num'>$2</span> ");
        text = text.replace(/(^|\n)\s*[-•]\s+/g, "$1<span class='os-li-bullet'>•</span> ");

        // Line breaks last.
        text = text.replace(/\n/g, "<br>");

        return text;
    }

    function appendChatMessage(sender, text, attachmentName) {
        const feed = getChatMessages();
        if (!feed) return;

        getChatPanel().classList.add("visible");

        // Keep strict chronological order: a pending typing bubble is
        // temporarily lifted so the new message lands before it.
        const pending = activeTypingBubble;

        const bubble = document.createElement("div");
        bubble.className = `os-chat-bubble ${sender}`;

        let content = renderMarkdown(text);
        if (attachmentName) {
            content += `<br><span style="font-family: var(--os-font-mono); font-size: 11px; color: var(--os-cyan);">📎 Attached: ${attachmentName}</span>`;
        }

        bubble.innerHTML = content;

        // Copy button on AI replies.
        if (sender === "aki") {
            const copyBtn = document.createElement("button");
            copyBtn.className = "os-copy-btn";
            copyBtn.title = "Copy reply";
            copyBtn.textContent = "⧉";
            copyBtn.onclick = (e) => {
                e.stopPropagation();
                const raw = text || bubble.innerText;
                if (bridge && typeof bridge.copyToClipboard === "function") {
                    bridge.copyToClipboard(raw);
                } else if (navigator.clipboard) {
                    navigator.clipboard.writeText(raw);
                }
                copyBtn.textContent = "✓";
                setTimeout(() => (copyBtn.textContent = "⧉"), 1200);
            };
            bubble.appendChild(copyBtn);
            bubble.classList.add("has-copy");
        }

        if (pending && pending.parentNode === feed) {
            feed.insertBefore(bubble, pending);
        } else {
            feed.appendChild(bubble);
        }

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

    // 7. Voice Input — always-on JARVIS listening
    async function toggleVoice() {
        if (isVoiceListening) {
            // User clicked to turn the always-on mic OFF.
            micAlwaysOn = false;
            stopVoiceRecording();
            updateMicButton();
            return;
        }

        micAlwaysOn = true;
        await startVoiceRecording();
    }

    async function startVoiceRecording() {
        if (isVoiceListening) return;

        if (!navigator.mediaDevices || !window.MediaRecorder) {
            deliverReply("Is device par voice input support nahi hai.");
            micAlwaysOn = false;
            updateMicButton();
            return;
        }

        if (bridge && typeof bridge.transcribeAudio !== "function") {
            deliverReply("Voice input ke liye Groq API key chahiye (.env mein AKI_AI_API_KEY).");
            micAlwaysOn = false;
            updateMicButton();
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            micStream = stream;
            micEverEngaged = true;
            beginRecording(stream);
            startSilenceWatch();
        } catch (error) {
            micAlwaysOn = false;
            updateMicButton();
            deliverReply("Microphone access nahi mila. Mic permission check karein.");
        }
    }

    function beginRecording(stream) {
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            const hadSpeech = speechDetected;
            const elapsed = Date.now() - recordingStartedAt;
            const streamRef = mediaRecorder ? mediaRecorder.stream : micStream;

            if (micAlwaysOn) {
                // JARVIS mode: instantly re-arm the mic for the next line.
                setTimeout(() => {
                    if (micAlwaysOn && !isVoiceListening) {
                        beginRecording(micStream || streamRef);
                        startSilenceWatch();
                    }
                }, 350);
            }

            if (!hadSpeech || elapsed < 800) {
                return; // silence chunk — ignore silently in always-on mode
            }

            sendRecordingToBridge();
        };

        mediaRecorder.start();
        recordingStartedAt = Date.now();
        speechDetected = false;
        isVoiceListening = true;

        setOrbState("listening");
        updateMicButton();
        setWaveformActive(true);
    }

    function startSilenceWatch() {
        if (silenceTimer) clearInterval(silenceTimer);

        try {
            audioContext = audioContext || new (window.AudioContext || window.webkitAudioContext)();
            const source = audioContext.createMediaStreamSource(micStream);
            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 512;
            source.connect(analyser);

            const buffer = new Uint8Array(analyser.frequencyBinCount);
            let quietTicks = 0;

            silenceTimer = setInterval(() => {
                if (!isVoiceListening) return;

                analyser.getByteTimeDomainData(buffer);

                let sum = 0;
                for (let i = 0; i < buffer.length; i++) {
                    const deviation = buffer[i] - 128;
                    sum += deviation * deviation;
                }
                const rms = Math.sqrt(sum / buffer.length);

                if (rms > 9) {
                    speechDetected = true;
                    quietTicks = 0;
                } else if (speechDetected) {
                    quietTicks++;
                    // ~1.4s of silence after speech = end of utterance.
                    if (quietTicks > 14) {
                        speechDetected = false;
                        quietTicks = 0;
                        stopVoiceRecording();
                    }
                }
            }, 100);
        } catch (error) {
            // Analyser unavailable — fall back to max-length recordings.
            silenceTimer = setInterval(() => {
                if (isVoiceListening && Date.now() - recordingStartedAt > 9000) {
                    stopVoiceRecording();
                }
            }, 500);
        }
    }

    function stopVoiceRecording() {
        isVoiceListening = false;
        updateMicButton();
        setWaveformActive(false);
        setOrbState("idle");

        if (silenceTimer) {
            clearInterval(silenceTimer);
            silenceTimer = null;
        }

        const elapsed = Date.now() - recordingStartedAt;

        if (elapsed < 800 && !micAlwaysOn) {
            if (mediaRecorder && mediaRecorder.state !== "inactive") {
                mediaRecorder.onstop = () => releaseStreamTracks(mediaRecorder.stream);
                mediaRecorder.stop();
            }
            deliverReply("Bohat mukhtasar tha — thora lamba bol kar mic dobara dabayen.");
            return;
        }

        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
        } else {
            releaseStreamTracks(mediaRecorder && mediaRecorder.stream);
        }
    }

    function updateMicButton() {
        if (!elements.btnVoice) return;

        // Red slash = user turned the always-on mic OFF.
        elements.btnVoice.classList.toggle(
            "mic-off",
            !isVoiceListening && micEverEngaged && !micAlwaysOn
        );
    }

    function releaseStreamTracks(stream) {
        if (stream) stream.getTracks().forEach((track) => track.stop());
    }

    function setWaveformActive(active) {
        const waveform = document.querySelector(".aki-waveform");
        if (waveform) waveform.classList.toggle("waveform-speaking", active);
    }

    function updateMicButton() {
        if (!elements.btnVoice) return;

        elements.btnVoice.style.background = isVoiceListening ? "var(--os-cyan)" : "";
        elements.btnVoice.style.color = isVoiceListening ? "#030712" : "";
        elements.btnVoice.textContent = isVoiceListening ? "⏹" : "🎙";
    }

    async function sendRecordingToBridge() {
        if (!audioChunks.length) {
            releaseStreamTracks(micStream);
            return;
        }

        // Listening indicator while Whisper does its work.
        setOrbState("thinking");
        dismissTypingIndicator();
        activeTypingBubble = showTypingIndicator();

        try {
            const blob = new Blob(audioChunks, { type: audioChunks[0].type || "audio/webm" });
            const buffer = await blob.arrayBuffer();
            const bytes = new Uint8Array(buffer);
            let binary = "";

            for (let i = 0; i < bytes.length; i += 0x8000) {
                binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
            }

            const encoded = btoa(binary);
            const result = await bridge.transcribeAudio(encoded, blob.type || "audio/webm");

            if (result && result.status === "NO_PROVIDER") {
                deliverReply(
                    "Voice input ke liye AI provider chahiye — .env mein AKI_AI_API_KEY set karein."
                );
                return;
            }
            // Transcript arrives via the transcriptionReady signal.
        } catch (error) {
            deliverReply("Awaaz bhejte waqt masla aaya. Dobara koshish karein.");
        }
    }

    function onTranscriptReady(requestId, transcript) {
        if (!transcript) {
            deliverReply("Awaaz samajh nahi aayi. Thora qareeb se dobara bolein.");
            return;
        }

        if (transcript.startsWith("__ERROR__")) {
            deliverReply("Speech service tak nahi pahunch saka: " + transcript.slice(9));
            return;
        }

        appendChatMessage("user", transcript);
        executeCommand(transcript);
    }

    // Reminder toast notification
    function showReminderToast(notification) {
        if (!notification) return;

        const toast = document.createElement("div");
        toast.className = "os-reminder-toast";
        toast.innerHTML =
            "<div class='os-toast-title'>⏰ " + (notification.title || "AKI Reminder") + "</div>" +
            "<div class='os-toast-body'>" + (notification.body || "") + "</div>";

        document.body.appendChild(toast);

        requestAnimationFrame(() => toast.classList.add("visible"));

        setTimeout(() => {
            toast.classList.remove("visible");
            setTimeout(() => toast.remove(), 400);
        }, 8000);

        if (window.AKISound) window.AKISound.playNotification();
    }

    // Settings drawer
    function initSettingsDrawer() {
        const drawer = document.getElementById("settingsDrawer");
        const backdrop = document.getElementById("settingsBackdrop");
        const btnOpen = document.getElementById("btnSettingsNav");
        const btnClose = document.getElementById("btnSettingsClose");
        const voiceToggle = document.getElementById("setVoiceOutput");
        const voiceSelect = document.getElementById("setTtsVoice");
        const inputBadge = document.getElementById("setVoiceInputBadge");
        const providerBadge = document.getElementById("setProviderBadge");
        const providerDesc = document.getElementById("setProviderDesc");

        if (!drawer || !btnOpen) return;

        function openDrawer() {
            if (window.AKISound) window.AKISound.playClick();
            loadSettings();
            drawer.classList.add("open");
            backdrop.classList.add("visible");
        }

        function closeDrawer() {
            drawer.classList.remove("open");
            backdrop.classList.remove("visible");
        }

        btnOpen.onclick = openDrawer;
        if (btnClose) btnClose.onclick = closeDrawer;
        if (backdrop) backdrop.onclick = closeDrawer;

        function loadSettings() {
            if (!bridge || typeof bridge.getSettings !== "function") return;

            bridge.getSettings().then((s) => {
                if (!s) return;

                if (voiceToggle) voiceToggle.checked = !!s.voice_output;

                if (voiceSelect) {
                    voiceSelect.innerHTML = "";
                    (s.available_voices || []).forEach((v) => {
                        const option = document.createElement("option");
                        option.value = v;
                        option.textContent = v.replace("Neural", "").replace(/^(ur|hi)-[A-Z]{2}-/, "");
                        if (v === s.tts_voice) option.selected = true;
                        voiceSelect.appendChild(option);
                    });
                }

                setBadge(inputBadge, !!s.voice_input);
                setBadge(providerBadge, !!s.ai_connected);

                if (providerDesc) {
                    providerDesc.textContent = s.ai_connected
                        ? `${s.ai_provider} · ${s.ai_model}`
                        : "Connected nahi — .env check karein";
                }
            });
        }

        function setBadge(el, on) {
            if (!el) return;
            el.textContent = on ? "ONLINE" : "OFF";
            el.className = "os-status-badge " + (on ? "on" : "off");
        }

        if (voiceToggle) {
            voiceToggle.onchange = () => {
                if (bridge && typeof bridge.setVoiceOutputEnabled === "function") {
                    voiceOutputEnabled = voiceToggle.checked;
                    bridge.setVoiceOutputEnabled(voiceToggle.checked);
                }
            };
        }

        if (voiceSelect) {
            voiceSelect.onchange = () => {
                if (bridge && typeof bridge.setTtsVoice === "function") {
                    bridge.setTtsVoice(voiceSelect.value);
                    if (window.AKISound) window.AKISound.playNotification();
                }
            };
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

                // Voice transcripts arrive here from the Whisper worker.
                if (typeof bridge.transcriptionReady !== "undefined") {
                    bridge.transcriptionReady.connect(onTranscriptReady);
                }

                // Reminders surface as cinematic toasts.
                if (typeof bridge.notificationPushed !== "undefined") {
                    bridge.notificationPushed.connect(showReminderToast);
                }

                // Speak replies aloud when a TTS engine exists; the
                // sound toggle controls both UI sounds and speech.
                if (bridge.isVoiceInputConfigured && typeof bridge.setVoiceOutputEnabled === "function") {
                    bridge.isVoiceInputConfigured().then((available) => {
                        appendLog(
                            available
                                ? "Voice input ready (Whisper)."
                                : "Voice input off: no AI provider configured.",
                            available ? "success" : "info"
                        );
                    });
                    bridge.setVoiceOutputEnabled(true);
                }

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

        // JARVIS mode: always-on mic arms itself after boot (once
        // permission has been granted at least once by the browser).
        setTimeout(() => {
            if (!micEverEngaged) {
                toggleVoice();
            }
        }, 3000);

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

    // Knowledge library window
    function initKnowledgePanel() {
        const window_el = document.getElementById("libraryWindow");
        const refreshBtn = document.getElementById("btnRefreshBooks");
        const btnNav = document.getElementById("btnLibraryNav");
        const btnMin = document.getElementById("btnLibMin");
        const btnMax = document.getElementById("btnLibMax");
        const btnClose = document.getElementById("btnLibClose");
        const emptyState = document.getElementById("libEmpty");
        const grid = document.getElementById("bookGrid");

        function addBook() {
            if (!bridge || typeof bridge.addBookFromDialog !== "function") return;

            if (window.AKISound) window.AKISound.playClick();

            bridge.addBookFromDialog().then((result) => {
                if (result && result.added) {
                    showReminderToast({
                        title: "Book Added",
                        body: `${result.title} — ${result.pages} pages ingested`,
                    });
                    refreshBooks();
                } else if (result && result.error) {
                    showReminderToast({
                        title: "Book Failed",
                        body: result.error,
                    });
                }
            });
        }

        function refreshBooks() {
            if (!bridge || typeof bridge.getBooks !== "function") return;

            bridge.getBooks().then((books) => {
                if (!grid) return;

                grid.innerHTML = "";

                // Square "+" tile first — like New Folder in Windows.
                const tile = document.createElement("button");
                tile.className = "os-lib-add-tile";
                tile.title = "Add a book (PDF/TXT)";
                tile.innerHTML =
                    "<span class='plus'>＋</span><span>ADD BOOK</span>";
                tile.onclick = addBook;
                grid.appendChild(tile);

                const hasBooks = books && books.length;

                if (emptyState) {
                    emptyState.classList.toggle("hidden", !!hasBooks);
                }

                (books || []).forEach((book) => {
                    const card = document.createElement("div");
                    card.className = "os-lib-card";
                    card.title = `${book.title} — ${book.pages} pages`;
                    const topics = (book.topics || []).slice(0, 3).join(", ");
                    card.innerHTML =
                        "<div class='os-lib-card-icon'>📁</div>" +
                        `<div class='os-lib-card-title'>${book.title}</div>` +
                        `<div class='os-lib-card-meta'>${book.pages} pages` +
                        (topics ? ` · ${topics}` : "") +
                        "</div>";
                    grid.appendChild(card);
                });
            });
        }

        function openLibrary() {
            if (window.AKISound) window.AKISound.playClick();
            window_el.classList.add("open");
            if (btnNav) btnNav.classList.add("active");
            refreshBooks();
        }

        function closeLibrary() {
            window_el.classList.remove("open");
            if (btnNav) btnNav.classList.remove("active");
        }

        if (btnNav) btnNav.onclick = openLibrary;
        if (btnClose) btnClose.onclick = closeLibrary;

        if (btnMin) {
            btnMin.onclick = () => {
                // Minimize collapses back to the desktop view.
                closeLibrary();
            };
        }

        if (btnMax) {
            btnMax.onclick = () => {
                window_el.classList.toggle("maximized");
            };
        }

        if (refreshBtn) refreshBtn.onclick = refreshBooks;
    }

    // Generic window helper (open/min/max/close pattern)
    function initAppWindow(windowId, navId, onOpen) {
        const win = document.getElementById(windowId);
        const nav = document.getElementById(navId);

        function open() {
            if (window.AKISound) window.AKISound.playClick();
            win.classList.add("open");
            if (nav) nav.classList.add("active");
            if (onOpen) onOpen();
        }

        function close() {
            win.classList.remove("open");
            if (nav) nav.classList.remove("active");
        }

        if (nav) nav.onclick = open;
        win.querySelector(".close").onclick = close;

        const min = win.querySelector("[id$='Min']");
        const max = win.querySelector("[id$='Max']");

        if (min) min.onclick = close;
        if (max) max.onclick = () => win.classList.toggle("maximized");

        return { open: open, close: close, element: win };
    }

    // Dev Agent window
    function initDevWindow() {
        const controller = initAppWindow("devWindow", "btnDevNav", refreshProjects);
        const grid = document.getElementById("devProjectGrid");
        const empty = document.getElementById("devEmpty");
        const viewer = document.getElementById("devViewer");
        const viewerTitle = document.getElementById("devViewerTitle");
        const fileList = document.getElementById("devFileList");
        const fileView = document.getElementById("devFileView");
        let activeProjectPath = "";

        function refreshProjects() {
            if (!bridge || typeof bridge.getDevProjects !== "function") return;

            bridge.getDevProjects().then((projects) => {
                if (!grid) return;
                grid.innerHTML = "";

                const has = projects && projects.length;
                if (empty) empty.classList.toggle("hidden", !!has);

                (projects || []).forEach((project) => {
                    const tile = document.createElement("div");
                    tile.className = "os-square-tile";
                    tile.innerHTML =
                        "<div class='tile-icon'>📂</div>" +
                        `<div class='tile-name'>${project.name}</div>` +
                        `<div class='tile-meta'>${project.file_count} files</div>`;

                    tile.onclick = () => showProjectOptions(project);
                    grid.appendChild(tile);
                });
            });
        }

        function showProjectOptions(project) {
            // JARVIS-style choice: open inside AKI or on the real PC.
            const choice = document.createElement("div");
            choice.className = "os-choice-popup";

            choice.innerHTML =
                `<div class='os-choice-title'>${project.name}</div>` +
                "<button data-act='aki'>🤖 AKI mein kholein</button>" +
                "<button data-act='pc'>💻 PC (Explorer) mein kholein</button>";

            choice.onclick = (e) => {
                const act = e.target.dataset && e.target.dataset.act;
                if (!act) return;

                if (act === "pc") {
                    bridge.openProjectFolder(project.path);
                } else {
                    openInAki(project);
                }
                choice.remove();
            };

            document.body.appendChild(choice);

            const rect = grid.getBoundingClientRect();
            choice.style.left = Math.max(20, rect.left + 40) + "px";
            choice.style.top = rect.top + 60 + "px";

            setTimeout(() => {
                document.addEventListener("click", function handler(ev) {
                    if (!choice.contains(ev.target)) {
                        choice.remove();
                        document.removeEventListener("click", handler);
                    }
                });
            }, 10);
        }

        function openInAki(project) {
            activeProjectPath = project.path;
            viewerTitle.textContent = project.name;

            bridge.getProjectFiles(project.path).then((files) => {
                fileList.innerHTML = "";

                (files || []).forEach((relative) => {
                    const item = document.createElement("div");
                    item.className = "os-dev-fileitem";
                    item.textContent = relative;
                    item.onclick = () => {
                        fileView.textContent = "Loading...";
                        bridge.readProjectFile(project.path, relative).then(
                            (content) => {
                                fileView.textContent = content || "[empty]";
                            }
                        );
                    };
                    fileList.appendChild(item);
                });

                fileView.textContent = "Select a file...";
                viewer.classList.add("open");
            });
        }

        const viewerClose = document.getElementById("btnDevViewerClose");
        if (viewerClose) viewerClose.onclick = () => viewer.classList.remove("open");

        const createBtn = document.getElementById("btnDevCreate");

        if (createBtn) {
            createBtn.onclick = () => {
                const description = document.getElementById("devDesc").value.trim();

                if (!description) {
                    showReminderToast({ title: "Dev Agent", body: "Pehle batao kya banana hai!" });
                    return;
                }

                if (window.AKISound) window.AKISound.playClick();
                createBtn.disabled = true;
                createBtn.textContent = "⏳ BUILDING...";

                setOrbState("thinking");

                bridge.createDevProject("", "", description).then(() => {
                    createBtn.disabled = false;
                    createBtn.textContent = "⚡ BUILD";
                    setTimeout(refreshProjects, 800);
                });
            };
        }

        if (bridge) {
            setTimeout(refreshProjects, 1500);
        }

        return controller;
    }

    // Cyber Suite window
    function initCyberWindow() {
        const output = document.getElementById("cyberOutput");
        const win = document.getElementById("cyberWindow");

        function appendResult(text) {
            if (!output) return;
            output.textContent += "\n\n" + text;
            output.scrollTop = output.scrollHeight;
        }

        function runTool(tool, parameter) {
            if (!bridge || typeof bridge.runSecurityTool !== "function") return;

            appendResult(`> Running ${tool}...`);

            bridge.runSecurityTool(tool, parameter || "").then((res) => {
                if (res && res.status && res.status !== "PENDING") {
                    appendResult(res.response || "");
                }
            });
        }

        document.querySelectorAll(".os-cyber-tool").forEach((btn) => {
            btn.onclick = () => runTool(btn.dataset.tool);
        });

        // Mirror tool results from chat into the console panel.
        setTimeout(() => {
            if (bridge && typeof bridge.aiResponseReady !== "undefined") {
                bridge.aiResponseReady.connect((payload) => {
                    if (
                        payload &&
                        payload.action &&
                        win.classList.contains("open")
                    ) {
                        appendResult(payload.response || "");
                    }
                });
            }
        }, 1000);

        return {};
    }

    // Settings drawer
        initSettingsDrawer();

        // Knowledge library panel
        initKnowledgePanel();

        // Dev Agent + Cyber Suite windows
        initDevWindow();
        initCyberWindow();

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

        // Sound Toggle Button — controls UI sounds AND spoken replies
        if (elements.btnSoundToggle) {
            elements.btnSoundToggle.onclick = () => {
                const enabled = window.AKISound ? window.AKISound.toggle() : false;
                elements.btnSoundToggle.textContent = enabled ? "🔊" : "🔇";

                if (bridge && typeof bridge.setVoiceOutputEnabled === "function") {
                    voiceOutputEnabled = enabled;
                    bridge.setVoiceOutputEnabled(enabled);
                } else {
                    voiceOutputEnabled = enabled;
                }
            };
        }

        // Clicking the orb while AKI talks silences it immediately.
        const coreOrb = document.querySelector(".aki-core-container");
        if (coreOrb) {
            coreOrb.addEventListener("click", () => {
                setOrbState("idle");
                if (bridge && typeof bridge.stopSpeaking === "function") {
                    bridge.stopSpeaking();
                }
            });
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
