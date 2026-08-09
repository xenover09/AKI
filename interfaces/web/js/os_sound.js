/**
 * AKI 2035 Synthetic Web Audio Sound Engine
 * Procedurally synthesizes futuristic UI audio feedback (Glass tick, Digital tap, EDITH ping, Scan sound, Boot riser)
 * with zero external asset dependencies and zero load latency.
 */

(function (window) {
    "use strict";

    let audioCtx = null;
    let soundEnabled = true;

    function getAudioContext() {
        if (!audioCtx) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (AudioContextClass) {
                audioCtx = new AudioContextClass();
            }
        }
        if (audioCtx && audioCtx.state === "suspended") {
            audioCtx.resume();
        }
        return audioCtx;
    }

    const SoundEngine = {
        isEnabled: function () {
            return soundEnabled;
        },

        setEnabled: function (enabled) {
            soundEnabled = !!enabled;
        },

        toggle: function () {
            soundEnabled = !soundEnabled;
            return soundEnabled;
        },

        /**
         * Glass Tick Hover Effect
         */
        playHover: function () {
            if (!soundEnabled) return;
            try {
                const ctx = getAudioContext();
                if (!ctx) return;

                const osc = ctx.createOscillator();
                const gain = ctx.createGain();

                osc.type = "sine";
                osc.frequency.setValueAtTime(2400, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(1800, ctx.currentTime + 0.03);

                gain.gain.setValueAtTime(0.015, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.03);

                osc.connect(gain);
                gain.connect(ctx.destination);

                osc.start();
                osc.stop(ctx.currentTime + 0.03);
            } catch (e) {
                // Ignore audio context autoplay restriction
            }
        },

        /**
         * Digital Tap Click Effect
         */
        playClick: function () {
            if (!soundEnabled) return;
            try {
                const ctx = getAudioContext();
                if (!ctx) return;

                const osc = ctx.createOscillator();
                const gain = ctx.createGain();

                osc.type = "triangle";
                osc.frequency.setValueAtTime(1400, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(300, ctx.currentTime + 0.05);

                gain.gain.setValueAtTime(0.04, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.05);

                osc.connect(gain);
                gain.connect(ctx.destination);

                osc.start();
                osc.stop(ctx.currentTime + 0.05);
            } catch (e) {}
        },

        /**
         * EDITH Soft Notification Ping
         */
        playNotification: function () {
            if (!soundEnabled) return;
            try {
                const ctx = getAudioContext();
                if (!ctx) return;

                const now = ctx.currentTime;
                
                // Note 1
                const osc1 = ctx.createOscillator();
                const gain1 = ctx.createGain();
                osc1.type = "sine";
                osc1.frequency.setValueAtTime(880, now); // A5
                gain1.gain.setValueAtTime(0.05, now);
                gain1.gain.exponentialRampToValueAtTime(0.0001, now + 0.3);
                osc1.connect(gain1);
                gain1.connect(ctx.destination);

                // Note 2
                const osc2 = ctx.createOscillator();
                const gain2 = ctx.createGain();
                osc2.type = "sine";
                osc2.frequency.setValueAtTime(1318.51, now + 0.08); // E6
                gain2.gain.setValueAtTime(0.06, now + 0.08);
                gain2.gain.exponentialRampToValueAtTime(0.0001, now + 0.4);
                osc2.connect(gain2);
                gain2.connect(ctx.destination);

                osc1.start(now);
                osc1.stop(now + 0.3);

                osc2.start(now + 0.08);
                osc2.stop(now + 0.4);
            } catch (e) {}
        },

        /**
         * Voice Scan Effect
         */
        playVoice: function () {
            if (!soundEnabled) return;
            try {
                const ctx = getAudioContext();
                if (!ctx) return;

                const now = ctx.currentTime;
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();

                osc.type = "sine";
                osc.frequency.setValueAtTime(500, now);
                osc.frequency.linearRampToValueAtTime(1200, now + 0.15);
                osc.frequency.linearRampToValueAtTime(800, now + 0.3);

                gain.gain.setValueAtTime(0.03, now);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.3);

                osc.connect(gain);
                gain.connect(ctx.destination);

                osc.start(now);
                osc.stop(now + 0.3);
            } catch (e) {}
        },

        /**
         * Cinematic Startup Boot Riser
         */
        playBoot: function () {
            if (!soundEnabled) return;
            try {
                const ctx = getAudioContext();
                if (!ctx) return;

                const now = ctx.currentTime;
                const freqs = [130.81, 196.00, 261.63, 392.00, 523.25]; // C3 chord

                freqs.forEach((freq, idx) => {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();

                    osc.type = idx % 2 === 0 ? "sine" : "triangle";
                    osc.frequency.setValueAtTime(freq * 0.5, now);
                    osc.frequency.exponentialRampToValueAtTime(freq, now + 0.8);

                    gain.gain.setValueAtTime(0.001, now);
                    gain.gain.linearRampToValueAtTime(0.02, now + 0.6);
                    gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.4);

                    osc.connect(gain);
                    gain.connect(ctx.destination);

                    osc.start(now + idx * 0.05);
                    osc.stop(now + 1.4);
                });
            } catch (e) {}
        }
    };

    window.AKISound = SoundEngine;

    // Attach user interaction listener to unblock Web Audio Autoplay Policy
    const unlockAudio = function () {
        getAudioContext();
        window.removeEventListener("pointerdown", unlockAudio);
        window.removeEventListener("keydown", unlockAudio);
    };
    window.addEventListener("pointerdown", unlockAudio);
    window.addEventListener("keydown", unlockAudio);

})(window);
