class ParticleSwarm {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        
        this.numParticles = 6000;
        this.particles = [];
        this.states = [];
        this.currentStateIndex = 0;
        this.nextStateIndex = 0;
        this.morphProgress = 1; // 0 to 1
        
        this.width = window.innerWidth;
        this.height = window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        
        this.reduceMotion = false;
        
        this.init();
        
        window.addEventListener('resize', () => {
            this.width = window.innerWidth;
            this.height = window.innerHeight;
            this.canvas.width = this.width;
            this.canvas.height = this.height;
            this.generateStates();
        });
    }

    init() {
        this.generateStates();
        
        // Initialize particles at CORE state
        for (let i = 0; i < this.numParticles; i++) {
            this.particles.push({
                x: this.states[0][i].x,
                y: this.states[0][i].y,
                z: this.states[0][i].z,
                originX: this.states[0][i].x,
                originY: this.states[0][i].y,
                originZ: this.states[0][i].z,
                targetX: this.states[0][i].x,
                targetY: this.states[0][i].y,
                targetZ: this.states[0][i].z,
                vx: 0, vy: 0, vz: 0,
                colorIndex: Math.random()
            });
        }
        
        this.animate();
        this.startMorphCycle();
    }

    generateStates() {
        this.states = [];
        let cx = this.width / 2; // Center of screen
        let cy = this.height / 2;
        
        // State 0: CORE (dense orb)
        let state0 = [];
        for (let i = 0; i < this.numParticles; i++) {
            let u = Math.random();
            let v = Math.random();
            let theta = u * 2.0 * Math.PI;
            let phi = Math.acos(2.0 * v - 1.0);
            let r = Math.cbrt(Math.random()) * 180; // Max radius
            // concentrate at center
            r = r * Math.pow(Math.random(), 1.5);
            
            state0.push({
                x: cx + r * Math.sin(phi) * Math.cos(theta),
                y: cy + r * Math.sin(phi) * Math.sin(theta),
                z: r * Math.cos(phi)
            });
        }
        this.states.push(state0);

        // State 1: FIGURE-A (Female silhouette)
        let state1 = [];
        for (let i = 0; i < this.numParticles; i++) {
            let part = Math.random();
            let x, y, z;
            if (part < 0.25) {
                // Head
                let r = Math.random() * 65;
                let angle = Math.random() * Math.PI * 2;
                x = cx + r * Math.cos(angle);
                y = cy - 120 + r * Math.sin(angle) * 1.25; 
                z = (Math.random() - 0.5) * 60;
            } else {
                // Shoulders / torso (soft, narrow)
                let w = (Math.random() - 0.5) * 300;
                let h = Math.random() * 250;
                let slope = Math.abs(w) * 0.5; // Steep slope
                x = cx + w;
                y = cy - 40 + slope + h;
                z = (Math.random() - 0.5) * 80;
            }
            state1.push({x, y, z});
        }
        this.states.push(state1);

        // State 2: FIGURE-B (Male silhouette)
        let state2 = [];
        for (let i = 0; i < this.numParticles; i++) {
            let part = Math.random();
            let x, y, z;
            if (part < 0.2) {
                // Head
                let r = Math.random() * 75;
                let angle = Math.random() * Math.PI * 2;
                x = cx + r * Math.cos(angle);
                y = cy - 130 + r * Math.sin(angle) * 1.15; 
                z = (Math.random() - 0.5) * 70;
            } else {
                // Broad shoulders
                let w = (Math.random() - 0.5) * 450;
                let h = Math.random() * 250;
                let slope = Math.abs(w) * 0.15; // Flat slope
                x = cx + w;
                y = cy - 30 + slope + h;
                z = (Math.random() - 0.5) * 100;
            }
            state2.push({x, y, z});
        }
        this.states.push(state2);
    }

    startMorphCycle() {
        setInterval(() => {
            if (this.reduceMotion) return;
            this.currentStateIndex = this.nextStateIndex;
            this.nextStateIndex = (this.currentStateIndex + 1) % this.states.length;
            this.morphProgress = 0;
            
            for (let i = 0; i < this.numParticles; i++) {
                this.particles[i].originX = this.particles[i].x;
                this.particles[i].originY = this.particles[i].y;
                this.particles[i].originZ = this.particles[i].z;
                
                this.particles[i].targetX = this.states[this.nextStateIndex][i].x;
                this.particles[i].targetY = this.states[this.nextStateIndex][i].y;
                this.particles[i].targetZ = this.states[this.nextStateIndex][i].z;
            }
        }, 6000); 
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        
        this.ctx.clearRect(0, 0, this.width, this.height);
        
        if (this.reduceMotion) {
            this.morphProgress = 1;
        } else {
            if (this.morphProgress < 1) {
                this.morphProgress += 0.006; 
                if (this.morphProgress > 1) this.morphProgress = 1;
            }
        }

        let ease = this.morphProgress < 0.5 ? 4 * Math.pow(this.morphProgress, 3) : 1 - Math.pow(-2 * this.morphProgress + 2, 3) / 2;
        let time = Date.now() * 0.001;

        for (let i = 0; i < this.numParticles; i++) {
            let p = this.particles[i];
            
            let bx = p.originX + (p.targetX - p.originX) * ease;
            let by = p.originY + (p.targetY - p.originY) * ease;
            let bz = p.originZ + (p.targetZ - p.originZ) * ease;
            
            let noiseX = Math.sin(time + i) * 1.5;
            let noiseY = Math.cos(time + i * 0.8) * 1.5;
            
            if (this.reduceMotion) {
                noiseX = 0;
                noiseY = 0;
            }
            
            p.x = bx + noiseX;
            p.y = by + noiseY;
            p.z = bz;
            
            let perspective = 800 / (800 + p.z);
            let projX = (p.x - this.width / 2) * perspective + this.width / 2;
            let projY = (p.y - this.height / 2) * perspective + this.height / 2;
            
            let size = Math.max(0.1, 1.2 * perspective);
            
            let colorStr = '#A259FF';
            if (p.colorIndex > 0.9) {
                colorStr = '#ffffff';
            } else if (p.colorIndex > 0.6) {
                colorStr = '#d1a8ff';
            } 
            
            let alpha = Math.min(1, Math.max(0.1, perspective - 0.2));
            this.ctx.globalAlpha = Math.min(1, alpha * 0.55); // Keep opacity low
            this.ctx.fillStyle = colorStr;
            
            this.ctx.beginPath();
            this.ctx.arc(projX, projY, size, 0, Math.PI * 2);
            this.ctx.fill();
        }
        
        this.ctx.globalAlpha = 1;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.akiParticleSwarm = new ParticleSwarm("aki-particle-canvas");
});
