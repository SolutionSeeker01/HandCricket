import React, { useEffect, useState } from 'react';

interface IntroScreenProps {
  onFinish: () => void;
  durationMs?: number;
}

export const IntroScreen: React.FC<IntroScreenProps> = ({
  onFinish,
  durationMs = 2600,
}) => {
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    // Start fadeout slightly before duration ends for seamless transition
    const fadeTimer = window.setTimeout(() => {
      setIsFadingOut(true);
    }, Math.max(durationMs - 400, 1000));

    const finishTimer = window.setTimeout(() => {
      onFinish();
    }, durationMs);

    return () => {
      window.clearTimeout(fadeTimer);
      window.clearTimeout(finishTimer);
    };
  }, [durationMs, onFinish]);

  const handleSkip = () => {
    setIsFadingOut(true);
    setTimeout(onFinish, 150);
  };

  return (
    <div
      onClick={handleSkip}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'Escape') handleSkip();
      }}
      className={`relative w-full h-[100dvh] flex flex-col items-center justify-between p-6 overflow-hidden select-none bg-[url('/stadium_bg.jpg')] bg-cover bg-center transition-opacity duration-500 cursor-pointer ${
        isFadingOut ? 'opacity-0 scale-105' : 'opacity-100 scale-100'
      }`}
    >
      {/* Stadium Atmospheric Lighting Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-slate-950/40 via-black/30 to-slate-950/70 pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-amber-500/10 via-transparent to-black/60 pointer-events-none" />

      {/* Top spacing */}
      <div className="relative z-10 pt-8 sm:pt-12 text-center" />

      {/* Center Cinematic Title Block */}
      <div className="relative z-10 flex flex-col items-center text-center animate-intro-title my-auto">
        <span className="text-sm sm:text-xl md:text-2xl font-black uppercase tracking-[0.35em] text-amber-300 drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] mb-1 sm:mb-2">
          WELCOME TO
        </span>

        <h1 className="text-5xl sm:text-7xl md:text-8xl font-black italic tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-yellow-100 via-amber-300 to-amber-500 drop-shadow-[0_8px_20px_rgba(0,0,0,0.95)]">
          HAND CRICKET
        </h1>

        <span className="text-base sm:text-2xl font-black tracking-[0.3em] text-amber-400 uppercase drop-shadow-[0_4px_12px_rgba(0,0,0,0.9)] mt-3 sm:mt-4">
          BY SRW
        </span>
      </div>

      {/* Footer / Skip hint */}
      <div className="relative z-10 pb-8 text-center">
        <p className="text-xs text-slate-300/80 font-medium tracking-wider animate-pulse">
          TAP ANYWHERE TO CONTINUE
        </p>
      </div>
    </div>
  );
};
