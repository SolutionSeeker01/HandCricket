/**
 * Web Audio API Sound Effects Engine for Hand Cricket (Slice 14)
 * 
 * Features:
 * - 100% synthesized sound effects (zero external audio file downloads, zero 404s, zero latency).
 * - Autoplay-compliant: AudioContext is initialized/resumed on user gesture.
 * - Master mute/unmute control with localStorage persistence.
 * - Safe in non-browser/Vitest environments (no-op fallback).
 */

class SoundManager {
  private ctx: AudioContext | null = null;
  private muted: boolean = false;

  constructor() {
    // Read persisted mute setting if available
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('hc_audio_muted');
        if (stored !== null) {
          this.muted = stored === 'true';
        }
      } catch {
        this.muted = false;
      }
    }
  }

  private initContext(): boolean {
    if (this.muted) return false;
    if (typeof window === 'undefined') return false;

    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        try {
          this.ctx = new AudioCtx();
        } catch {
          return false;
        }
      }
    }

    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }

    return this.ctx !== null;
  }

  public isMuted(): boolean {
    return this.muted;
  }

  public setMuted(muted: boolean): void {
    this.muted = muted;
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('hc_audio_muted', String(muted));
      } catch {}
    }
  }

  public toggleMute(): boolean {
    this.setMuted(!this.muted);
    if (!this.muted) {
      this.initContext();
      this.playClick();
    }
    return this.muted;
  }

  /**
   * Crisp UI click for keypad, buttons, and navigation.
   */
  public playClick(): void {
    if (!this.initContext() || !this.ctx) return;

    try {
      const t = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(800, t);
      osc.frequency.exponentialRampToValueAtTime(400, t + 0.04);

      gain.gain.setValueAtTime(0.12, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.04);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(t);
      osc.stop(t + 0.04);
    } catch {}
  }

  /**
   * Coin toss metallic chime / spin.
   */
  public playCoinToss(): void {
    if (!this.initContext() || !this.ctx) return;

    try {
      const t = this.ctx.currentTime;
      const freqs = [1800, 2400, 3200];
      freqs.forEach((f, idx) => {
        const osc = this.ctx!.createOscillator();
        const gain = this.ctx!.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(f, t);
        osc.frequency.exponentialRampToValueAtTime(f * 0.95, t + 0.35 + idx * 0.05);

        gain.gain.setValueAtTime(0.08 / (idx + 1), t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.35 + idx * 0.05);

        osc.connect(gain);
        gain.connect(this.ctx!.destination);

        osc.start(t);
        osc.stop(t + 0.4);
      });
    } catch {}
  }

  /**
   * Clean wooden bat hit sound for normal deliveries (0, 1, 2, 3 runs).
   */
  public playBatHit(runs: number = 1): void {
    if (!this.initContext() || !this.ctx) return;

    try {
      const t = this.ctx.currentTime;

      // 1. Resonant wood thump
      const osc = this.ctx.createOscillator();
      const oscGain = this.ctx.createGain();

      const baseFreq = runs === 0 ? 180 : 220 + runs * 25;
      osc.type = 'sine';
      osc.frequency.setValueAtTime(baseFreq, t);
      osc.frequency.exponentialRampToValueAtTime(70, t + 0.09);

      oscGain.gain.setValueAtTime(0.28, t);
      oscGain.gain.exponentialRampToValueAtTime(0.001, t + 0.09);

      osc.connect(oscGain);
      oscGain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.09);

      // 2. High-frequency crack noise
      const bufferSize = this.ctx.sampleRate * 0.04;
      const noiseBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const output = noiseBuffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        output[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.2));
      }

      const whiteNoise = this.ctx.createBufferSource();
      whiteNoise.buffer = noiseBuffer;

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.value = 1600;
      filter.Q.value = 2.0;

      const noiseGain = this.ctx.createGain();
      noiseGain.gain.setValueAtTime(0.18, t);
      noiseGain.gain.exponentialRampToValueAtTime(0.001, t + 0.04);

      whiteNoise.connect(filter);
      filter.connect(noiseGain);
      noiseGain.connect(this.ctx.destination);

      whiteNoise.start(t);
      whiteNoise.stop(t + 0.04);
    } catch {}
  }

  /**
   * Resonant boundary crack + energetic crowd cheer for FOUR!
   */
  public playFour(): void {
    if (!this.initContext() || !this.ctx) return;

    try {
      // 1. Solid bat crack
      this.playBatHit(4);

      // 2. Synthesized rising crowd cheer
      const t = this.ctx.currentTime + 0.05;
      const duration = 0.9;
      const bufferSize = this.ctx.sampleRate * duration;
      const cheerBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = cheerBuffer.getChannelData(0);

      for (let i = 0; i < bufferSize; i++) {
        const progress = i / bufferSize;
        const envelope = Math.sin(progress * Math.PI);
        data[i] = (Math.random() * 2 - 1) * envelope;
      }

      const noiseSource = this.ctx.createBufferSource();
      noiseSource.buffer = cheerBuffer;

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(900, t);
      filter.frequency.linearRampToValueAtTime(1800, t + 0.4);
      filter.frequency.linearRampToValueAtTime(700, t + duration);

      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.01, t);
      gain.gain.linearRampToValueAtTime(0.22, t + 0.25);
      gain.gain.exponentialRampToValueAtTime(0.001, t + duration);

      noiseSource.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);

      noiseSource.start(t);
      noiseSource.stop(t + duration);
    } catch {}
  }

  /**
   * Heavy power smash + roaring stadium crowd cheer for SIX!
   */
  public playSix(): void {
    if (!this.initContext() || !this.ctx) return;

    try {
      const t = this.ctx.currentTime;

      // 1. Deep explosive power thump
      const subOsc = this.ctx.createOscillator();
      const subGain = this.ctx.createGain();
      subOsc.type = 'sine';
      subOsc.frequency.setValueAtTime(320, t);
      subOsc.frequency.exponentialRampToValueAtTime(50, t + 0.16);
      subGain.gain.setValueAtTime(0.35, t);
      subGain.gain.exponentialRampToValueAtTime(0.001, t + 0.16);

      subOsc.connect(subGain);
      subGain.connect(this.ctx.destination);
      subOsc.start(t);
      subOsc.stop(t + 0.16);

      // 2. High-impact crack
      this.playBatHit(6);

      // 3. Roaring extended stadium cheer
      const cheerT = t + 0.06;
      const duration = 1.3;
      const bufferSize = this.ctx.sampleRate * duration;
      const cheerBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = cheerBuffer.getChannelData(0);

      for (let i = 0; i < bufferSize; i++) {
        const progress = i / bufferSize;
        const envelope = Math.sin(progress * Math.PI);
        data[i] = (Math.random() * 2 - 1) * envelope;
      }

      const noiseSource = this.ctx.createBufferSource();
      noiseSource.buffer = cheerBuffer;

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(1000, cheerT);
      filter.frequency.linearRampToValueAtTime(2200, cheerT + 0.35);
      filter.frequency.linearRampToValueAtTime(800, cheerT + duration);
      filter.Q.value = 1.2;

      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.02, cheerT);
      gain.gain.linearRampToValueAtTime(0.28, cheerT + 0.3);
      gain.gain.exponentialRampToValueAtTime(0.001, cheerT + duration);

      noiseSource.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);

      noiseSource.start(cheerT);
      noiseSource.stop(cheerT + duration);
    } catch {}
  }

  /**
   * Dramatic stump rattle & crowd reaction for WICKET!
   */
  public playWicket(): void {
    if (!this.initContext() || !this.ctx) return;

    try {
      const t = this.ctx.currentTime;

      // 1. Metallic/wooden stump strike clatter
      const clatterTimes = [0, 0.03, 0.07];
      const clatterPitches = [360, 480, 290];

      clatterTimes.forEach((delay, idx) => {
        const osc = this.ctx!.createOscillator();
        const gain = this.ctx!.createGain();

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(clatterPitches[idx], t + delay);
        osc.frequency.exponentialRampToValueAtTime(110, t + delay + 0.08);

        gain.gain.setValueAtTime(0.26, t + delay);
        gain.gain.exponentialRampToValueAtTime(0.001, t + delay + 0.08);

        osc.connect(gain);
        gain.connect(this.ctx!.destination);

        osc.start(t + delay);
        osc.stop(t + delay + 0.08);
      });

      // 2. Crowd gasp / reaction
      const gaspT = t + 0.1;
      const duration = 0.8;
      const bufferSize = this.ctx.sampleRate * duration;
      const gaspBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = gaspBuffer.getChannelData(0);

      for (let i = 0; i < bufferSize; i++) {
        const p = i / bufferSize;
        data[i] = (Math.random() * 2 - 1) * Math.sin(p * Math.PI);
      }

      const noise = this.ctx.createBufferSource();
      noise.buffer = gaspBuffer;

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(1400, gaspT);
      filter.frequency.exponentialRampToValueAtTime(450, gaspT + duration);

      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.02, gaspT);
      gain.gain.linearRampToValueAtTime(0.2, gaspT + 0.15);
      gain.gain.exponentialRampToValueAtTime(0.001, gaspT + duration);

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);

      noise.start(gaspT);
      noise.stop(gaspT + duration);
    } catch {}
  }

  /**
   * Subtle tick / urgency chime when countdown timer reaches <= 3 seconds.
   */
  public playTimerWarning(seconds: number = 3): void {
    if (!this.initContext() || !this.ctx) return;

    try {
      const t = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      const freq = seconds <= 1 ? 980 : 880;
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, t);

      gain.gain.setValueAtTime(0.09, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.07);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(t);
      osc.stop(t + 0.07);
    } catch {}
  }
}

export const soundManager = new SoundManager();
