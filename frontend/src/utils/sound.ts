/**
 * Web Audio API + Local Realistic Stadium Crowd Audio Engine for Hand Cricket
 * 
 * Features:
 * - Hybrid engine: Uses authentic local sports-stadium crowd recordings (WAV) from CC0 & CC-BY sources.
 * - Resilient synthesized Web Audio API fallbacks for every effect (zero crashes, 100% test isolation).
 * - Master mute control with localStorage persistence.
 * - Browser autoplay compliance with gesture-based context resumption.
 * - Crowd audio channel manager that prevents overlapping crowd audio pile-up.
 * - Balanced volume mastering per sports hierarchy specification.
 */

class SoundManager {
  private ctx: AudioContext | null = null;
  private muted: boolean = false;
  private bufferCache: Map<string, AudioBuffer> = new Map();
  private loadingPromises: Map<string, Promise<AudioBuffer | null>> = new Map();
  private activeCrowdSource: AudioBufferSourceNode | null = null;
  private activeCrowdGain: GainNode | null = null;

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
    if (this.muted) {
      this.stopActiveCrowd();
    } else {
      this.preloadAll();
    }
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
      this.preloadAll();
    }
    return this.muted;
  }

  private stopActiveCrowd(): void {
    if (this.activeCrowdGain && this.ctx) {
      try {
        const now = this.ctx.currentTime;
        this.activeCrowdGain.gain.setValueAtTime(this.activeCrowdGain.gain.value, now);
        this.activeCrowdGain.gain.linearRampToValueAtTime(0.001, now + 0.12);
      } catch {}
    }
    if (this.activeCrowdSource) {
      try {
        this.activeCrowdSource.stop(this.ctx ? this.ctx.currentTime + 0.13 : 0);
      } catch {}
      this.activeCrowdSource = null;
      this.activeCrowdGain = null;
    }
  }

  public isBufferLoaded(fileName: string): boolean {
    return this.bufferCache.has(fileName);
  }

  public getLoadedCount(): number {
    return this.bufferCache.size;
  }

  public setCachedBuffer(fileName: string, buffer: AudioBuffer): void {
    this.bufferCache.set(fileName, buffer);
  }

  public clearBufferCache(): void {
    this.bufferCache.clear();
  }

  public resetContextForTesting(): void {
    this.stopActiveCrowd();
    this.ctx = null;
    this.bufferCache.clear();
    this.loadingPromises.clear();
  }

  public preloadAudio(fileName: string): Promise<AudioBuffer | null> {
    if (this.bufferCache.has(fileName)) {
      return Promise.resolve(this.bufferCache.get(fileName)!);
    }
    if (this.loadingPromises.has(fileName)) {
      return this.loadingPromises.get(fileName)!;
    }
    if (typeof window === 'undefined' || typeof fetch === 'undefined') {
      return Promise.resolve(null);
    }
    if (!this.initContext() || !this.ctx) {
      return Promise.resolve(null);
    }

    const promise = fetch('/audio/' + fileName)
      .then((res) => {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.arrayBuffer();
      })
      .then((arrayBuffer) => {
        if (!this.ctx) return null;
        return new Promise<AudioBuffer | null>((resolve) => {
          try {
            const promiseOrVoid = this.ctx!.decodeAudioData(
              arrayBuffer,
              (buf) => resolve(buf),
              () => resolve(null)
            );
            if (promiseOrVoid && typeof (promiseOrVoid as any).then === 'function') {
              (promiseOrVoid as any).then(resolve).catch(() => resolve(null));
            }
          } catch {
            resolve(null);
          }
        });
      })
      .then((decoded) => {
        if (decoded) {
          this.bufferCache.set(fileName, decoded);
        }
        return decoded;
      })
      .catch(() => null)
      .finally(() => {
        this.loadingPromises.delete(fileName);
      });

    this.loadingPromises.set(fileName, promise);
    return promise;
  }

  public async preloadAll(): Promise<void> {
    if (this.muted) return;
    if (typeof window === 'undefined' || typeof fetch === 'undefined') return;
    if (!this.initContext() || !this.ctx) return;

    const files = [
      'crowd_four.wav',
      'crowd_six.wav',
      'crowd_wicket.wav',
      'crowd_fifty.wav',
      'crowd_century.wav',
      'crowd_win.wav',
      'crowd_loss.wav',
    ];
    await Promise.all(files.map((f) => this.preloadAudio(f)));
  }

  private playCrowdSound(fileName: string, volume: number, fallbackSynthesizer: () => void): void {
    if (!this.initContext() || !this.ctx) return;

    this.stopActiveCrowd();

    const buffer = this.bufferCache.get(fileName);
    if (buffer && this.ctx) {
      try {
        const source = this.ctx.createBufferSource();
        source.buffer = buffer;
        const gainNode = this.ctx.createGain();
        gainNode.gain.setValueAtTime(volume, this.ctx.currentTime);

        source.connect(gainNode);
        gainNode.connect(this.ctx.destination);

        source.start();
        this.activeCrowdSource = source;
        this.activeCrowdGain = gainNode;

        source.onended = () => {
          if (this.activeCrowdSource === source) {
            this.activeCrowdSource = null;
            this.activeCrowdGain = null;
          }
        };
        return;
      } catch {}
    }

    // Preload for next time if not already cached
    this.preloadAudio(fileName);

    // Fall back to synthetic crowd sound
    fallbackSynthesizer();
  }

  /**
   * Crisp UI click for keypad, buttons, and navigation (Volume: subtle, 0.12).
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
   * Clean wooden bat hit sound for deliveries.
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
   * Wooden / metallic stump strike clatter.
   */
  private playStumpClatter(): void {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
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
  }

  /**
   * Resonant boundary crack + loud celebratory stadium cheer for FOUR!
   * Volume: 0.50 (strong cheer per hierarchy).
   */
  public playFour(): void {
    if (!this.initContext() || !this.ctx) return;
    this.playBatHit(4);
    this.playCrowdSound('crowd_four.wav', 0.50, () => this.synthesizeFourCrowd());
  }

  private synthesizeFourCrowd(): void {
    if (!this.ctx) return;
    try {
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
   * Heavy power smash + biggest/loudest sports crowd roar for SIX!
   * Volume: 0.75 (very loud roar per hierarchy).
   */
  public playSix(): void {
    if (!this.initContext() || !this.ctx) return;

    try {
      const t = this.ctx.currentTime;
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

      this.playBatHit(6);
    } catch {}

    this.playCrowdSound('crowd_six.wav', 0.75, () => this.synthesizeSixCrowd());
  }

  private synthesizeSixCrowd(): void {
    if (!this.ctx) return;
    try {
      const cheerT = this.ctx.currentTime + 0.06;
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
   * Dramatic stump clatter + loud crowd reaction / roar for WICKET!
   * Volume: 0.55 (strong dramatic reaction per hierarchy).
   */
  public playWicket(): void {
    if (!this.initContext() || !this.ctx) return;
    try {
      this.playStumpClatter();
    } catch {}
    this.playCrowdSound('crowd_wicket.wav', 0.55, () => this.synthesizeWicketCrowd());
  }

  private synthesizeWicketCrowd(): void {
    if (!this.ctx) return;
    try {
      const gaspT = this.ctx.currentTime + 0.1;
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
   * Strong celebratory crowd cheer for 50 RUNS half-century milestone!
   * Volume: 0.60 (strong milestone celebration per hierarchy).
   */
  public playFifty(): void {
    if (!this.initContext() || !this.ctx) return;
    this.playCrowdSound('crowd_fifty.wav', 0.60, () => this.synthesizeFiftyCrowd());
  }

  private synthesizeFiftyCrowd(): void {
    if (!this.ctx) return;
    try {
      const t = this.ctx.currentTime;
      const duration = 1.2;
      const bufferSize = this.ctx.sampleRate * duration;
      const buf = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        const p = i / bufferSize;
        data[i] = (Math.random() * 2 - 1) * Math.sin(p * Math.PI);
      }
      const noise = this.ctx.createBufferSource();
      noise.buffer = buf;
      const filter = this.ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(1100, t);
      filter.frequency.linearRampToValueAtTime(1600, t + 0.4);
      filter.frequency.linearRampToValueAtTime(850, t + duration);
      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.02, t);
      gain.gain.linearRampToValueAtTime(0.24, t + 0.25);
      gain.gain.exponentialRampToValueAtTime(0.001, t + duration);

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);
      noise.start(t);
      noise.stop(t + duration);
    } catch {}
  }

  /**
   * HUGE sustained stadium roar for 100 RUNS century milestone!
   * Volume: 0.85 (HUGE sustained roar per hierarchy).
   */
  public playCentury(): void {
    if (!this.initContext() || !this.ctx) return;
    this.playCrowdSound('crowd_century.wav', 0.85, () => this.synthesizeCenturyCrowd());
  }

  private synthesizeCenturyCrowd(): void {
    if (!this.ctx) return;
    try {
      const t = this.ctx.currentTime;
      const duration = 2.0;
      const bufferSize = this.ctx.sampleRate * duration;
      const buf = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        const p = i / bufferSize;
        data[i] = (Math.random() * 2 - 1) * Math.sin(p * Math.PI);
      }
      const noise = this.ctx.createBufferSource();
      noise.buffer = buf;
      const filter = this.ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(950, t);
      filter.frequency.linearRampToValueAtTime(2400, t + 0.5);
      filter.frequency.linearRampToValueAtTime(900, t + duration);
      filter.Q.value = 1.0;
      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.02, t);
      gain.gain.linearRampToValueAtTime(0.32, t + 0.4);
      gain.gain.exponentialRampToValueAtTime(0.001, t + duration);

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);
      noise.start(t);
      noise.stop(t + duration);
    } catch {}
  }

  /**
   * Loud sustained victory celebration for MATCH WIN!
   * Volume: 0.90 (biggest victory celebration per hierarchy).
   */
  public playMatchWin(): void {
    if (!this.initContext() || !this.ctx) return;
    this.playCrowdSound('crowd_win.wav', 0.90, () => this.synthesizeWinCrowd());
  }

  private synthesizeWinCrowd(): void {
    if (!this.ctx) return;
    try {
      const t = this.ctx.currentTime;
      const duration = 2.2;
      const bufferSize = this.ctx.sampleRate * duration;
      const buf = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        const p = i / bufferSize;
        data[i] = (Math.random() * 2 - 1) * Math.sin(p * Math.PI);
      }
      const noise = this.ctx.createBufferSource();
      noise.buffer = buf;
      const filter = this.ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(1000, t);
      filter.frequency.linearRampToValueAtTime(2200, t + 0.6);
      filter.frequency.linearRampToValueAtTime(900, t + duration);
      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.02, t);
      gain.gain.linearRampToValueAtTime(0.34, t + 0.5);
      gain.gain.exponentialRampToValueAtTime(0.001, t + duration);

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);
      noise.start(t);
      noise.stop(t + duration);
    } catch {}
  }

  /**
   * Realistic disappointed / low crowd reaction for MATCH LOSS!
   * Volume: 0.35 (noticeably subdued per hierarchy).
   */
  public playMatchLoss(): void {
    if (!this.initContext() || !this.ctx) return;
    this.playCrowdSound('crowd_loss.wav', 0.35, () => this.synthesizeLossCrowd());
  }

  private synthesizeLossCrowd(): void {
    if (!this.ctx) return;
    try {
      const t = this.ctx.currentTime;
      const duration = 1.4;
      const bufferSize = this.ctx.sampleRate * duration;
      const buf = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        const p = i / bufferSize;
        // Falling groan envelope
        data[i] = (Math.random() * 2 - 1) * Math.exp(-p * 2.5);
      }
      const noise = this.ctx.createBufferSource();
      noise.buffer = buf;
      const filter = this.ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(800, t);
      filter.frequency.exponentialRampToValueAtTime(250, t + duration);
      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.16, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + duration);

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);
      noise.start(t);
      noise.stop(t + duration);
    } catch {}
  }

  /**
   * Subtle tick / urgency chime when countdown timer reaches <= 3 seconds (Volume: 0.09).
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

if (typeof window !== 'undefined') {
  (window as any).soundManager = soundManager;
}
