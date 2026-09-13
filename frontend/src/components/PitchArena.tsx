import React from 'react';
import { EventFeedback, MatchState } from '../types';

interface PitchArenaProps {
  matchState: MatchState | null;
  selectedNumber: number | null;
  isWaiting: boolean;
  eventFeedback: EventFeedback | null;
  onSelectNumber: (num: number) => void;
}

export const PitchArena: React.FC<PitchArenaProps> = ({
  matchState,
  selectedNumber,
  isWaiting,
  eventFeedback,
  onSelectNumber,
}) => {
  const userIsBatting = matchState ? matchState.user_is_batting : true;
  const isTurnInteractive =
    matchState &&
    !isWaiting &&
    !eventFeedback &&
    matchState.status !== 'INNINGS_BREAK' &&
    matchState.status !== 'COMPLETED';

  return (
    <div className="relative w-full flex-1 flex flex-col items-center justify-between overflow-hidden select-none px-2 py-1 sm:py-2">
      {/* 1. STADIUM & DUSK ATMOSPHERE BACKGROUND */}
      <div className="absolute inset-0 -z-10 overflow-hidden pointer-events-none">
        {/* Sky gradient: Deep twilight into stadium atmosphere */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#080d1a] via-[#101b33] to-[#0c1424]" />

        {/* Floodlight Beams Left & Right */}
        <div className="absolute -top-10 left-1/4 w-72 h-96 bg-sky-400/10 blur-3xl rounded-full transform -rotate-12 pointer-events-none" />
        <div className="absolute -top-10 right-1/4 w-72 h-96 bg-amber-300/10 blur-3xl rounded-full transform rotate-12 pointer-events-none" />

        {/* Stadium Floodlight Towers */}
        <div className="absolute top-1 left-3 sm:left-12 flex flex-col items-center opacity-80">
          <div className="w-12 h-6 bg-slate-800 rounded-sm border border-slate-600 grid grid-cols-4 gap-0.5 p-0.5 shadow-lg shadow-sky-400/20">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="bg-amber-100/90 rounded-[1px] h-2 shadow-sm shadow-white" />
            ))}
          </div>
          <div className="w-1 h-16 sm:h-24 bg-gradient-to-b from-slate-600 to-transparent" />
        </div>

        <div className="absolute top-1 right-3 sm:right-12 flex flex-col items-center opacity-80">
          <div className="w-12 h-6 bg-slate-800 rounded-sm border border-slate-600 grid grid-cols-4 gap-0.5 p-0.5 shadow-lg shadow-sky-400/20">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="bg-amber-100/90 rounded-[1px] h-2 shadow-sm shadow-white" />
            ))}
          </div>
          <div className="w-1 h-16 sm:h-24 bg-gradient-to-b from-slate-600 to-transparent" />
        </div>

        {/* Stadium Tier / Crowd Silhouette Curve */}
        <div className="absolute top-16 sm:top-20 inset-x-0 h-28 bg-gradient-to-b from-[#18233d] to-[#0d1627] rounded-b-[40%] opacity-90 border-b border-sky-500/20 shadow-inner flex items-center justify-center">
          <div className="w-full h-full opacity-20 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:12px_12px]" />
        </div>

        {/* Ground Turf Field */}
        <div className="absolute bottom-0 inset-x-0 h-[65%] bg-gradient-to-t from-[#15602a] via-[#1b7334] to-[#124d22] rounded-t-[35%] border-t-2 border-emerald-400/20 shadow-2xl">
          {/* Subtle grass texture stripes */}
          <div className="absolute inset-0 opacity-15 bg-[repeating-linear-gradient(90deg,#000,#000_30px,#fff_30px,#fff_60px)]" />
        </div>
      </div>

      {/* 2. CENTRAL CRICKET PITCH (SVG Canvas for crisp perspective) */}
      <div className="relative w-full max-w-sm sm:max-w-md h-40 sm:h-52 flex items-center justify-center mt-2 sm:mt-4">
        {/* Pitch Graphic */}
        <svg
          viewBox="0 0 400 240"
          className="w-full h-full drop-shadow-2xl overflow-visible"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Pitch dirt surface with perspective trapezoid */}
          <polygon
            points="140,20 260,20 320,220 80,220"
            fill="url(#pitchGradient)"
            stroke="#b45309"
            strokeWidth="1.5"
            strokeOpacity="0.4"
          />

          {/* Gradients */}
          <defs>
            <linearGradient id="pitchGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#ca8a04" stopOpacity="0.8" />
              <stop offset="40%" stopColor="#d97706" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#b45309" stopOpacity="1" />
            </linearGradient>
            <linearGradient id="stumpGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#fef08a" />
              <stop offset="50%" stopColor="#facc15" />
              <stop offset="100%" stopColor="#ca8a04" />
            </linearGradient>
          </defs>

          {/* Crease Markings (Popping & Bowling crease lines) */}
          <line x1="110" y1="180" x2="290" y2="180" stroke="white" strokeWidth="3" strokeOpacity="0.9" />
          <line x1="130" y1="200" x2="270" y2="200" stroke="white" strokeWidth="2" strokeOpacity="0.7" />
          <line x1="150" y1="40" x2="250" y2="40" stroke="white" strokeWidth="2" strokeOpacity="0.6" />

          {/* 3 Wickets & Bails (Stumps) */}
          <g transform="translate(165, 120)">
            {/* Wicket shadow */}
            <ellipse cx="35" cy="62" rx="45" ry="5" fill="#000" opacity="0.3" />

            {/* Stump 1 (Off) */}
            <rect
              x="14"
              y="5"
              width="7"
              height="55"
              rx="3"
              fill="url(#stumpGradient)"
              className={eventFeedback?.type === 'WICKET' ? 'animate-spin transform origin-bottom' : ''}
            />

            {/* Stump 2 (Middle) */}
            <rect
              x="32"
              y="5"
              width="7"
              height="55"
              rx="3"
              fill="url(#stumpGradient)"
              className={eventFeedback?.type === 'WICKET' ? 'animate-ping transform origin-center' : ''}
            />

            {/* Stump 3 (Leg) */}
            <rect
              x="50"
              y="5"
              width="7"
              height="55"
              rx="3"
              fill="url(#stumpGradient)"
              className={eventFeedback?.type === 'WICKET' ? 'animate-bounce transform origin-bottom' : ''}
            />

            {/* Bails */}
            <rect
              x="11"
              y="2"
              width="24"
              height="4"
              rx="2"
              fill="#fef08a"
              className={eventFeedback?.type === 'WICKET' ? '-translate-y-8 translate-x-4 rotate-45 transition-transform' : ''}
            />
            <rect
              x="36"
              y="2"
              width="24"
              height="4"
              rx="2"
              fill="#fef08a"
              className={eventFeedback?.type === 'WICKET' ? '-translate-y-10 -translate-x-4 -rotate-45 transition-transform' : ''}
            />
          </g>
        </svg>

        {/* 3. EVENT CELEBRATION OVERLAYS (FOUR / SIX / WICKET) */}
        {eventFeedback && (
          <div className="absolute inset-0 flex flex-col items-center justify-center z-30 pointer-events-none animate-in fade-in zoom-in duration-200">
            {/* FOUR CELEBRATION */}
            {eventFeedback.type === 'FOUR' && (
              <div className="flex flex-col items-center">
                <div className="text-7xl sm:text-9xl font-black text-sky-400 drop-shadow-[0_0_35px_rgba(56,189,248,0.8)] italic tracking-tighter scale-110 animate-bounce">
                  4
                </div>
                <div className="text-3xl sm:text-5xl font-black italic tracking-widest text-white drop-shadow-[0_4px_12px_rgba(0,0,0,0.9)] bg-gradient-to-r from-sky-400 via-blue-200 to-sky-400 bg-clip-text text-transparent -mt-2">
                  FOUR!
                </div>
              </div>
            )}

            {/* SIX CELEBRATION */}
            {eventFeedback.type === 'SIX' && (
              <div className="flex flex-col items-center">
                <div className="text-7xl sm:text-9xl font-black text-amber-400 drop-shadow-[0_0_40px_rgba(251,191,36,0.9)] italic tracking-tighter scale-110 animate-bounce">
                  6
                </div>
                <div className="text-3xl sm:text-5xl font-black italic tracking-widest text-white drop-shadow-[0_4px_12px_rgba(0,0,0,0.9)] bg-gradient-to-r from-amber-300 via-yellow-100 to-amber-400 bg-clip-text text-transparent -mt-2">
                  SIX!
                </div>
              </div>
            )}

            {/* WICKET CELEBRATION */}
            {eventFeedback.type === 'WICKET' && (
              <div className="flex flex-col items-center animate-in zoom-in-95 duration-150">
                <div className="bg-red-600/90 border-2 border-red-400 px-6 py-1.5 rounded-2xl shadow-[0_0_40px_rgba(239,68,68,0.8)] text-3xl sm:text-5xl font-black italic tracking-wider text-white">
                  WICKET!
                </div>
                {eventFeedback.subtitle && (
                  <div className="mt-2 text-sm sm:text-lg font-bold text-amber-300 drop-shadow-md bg-black/60 px-4 py-1 rounded-full border border-amber-400/30">
                    {eventFeedback.subtitle}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 4. CENTRAL PROMPT & ACTION AREA */}
      <div className="w-full flex flex-col items-center justify-center my-1 sm:my-2 z-10">
        {/* Dynamic Header Prompt: "Your Call!" */}
        <h2 className="text-3xl sm:text-5xl font-black italic tracking-wide text-white drop-shadow-[0_2px_12px_rgba(0,0,0,0.8)] font-serif">
          {userIsBatting ? 'Your Call!' : 'Bowl Now!'}
        </h2>
        <p className="text-xs sm:text-sm font-semibold tracking-wide text-sky-200/90 drop-shadow mt-0.5">
          {userIsBatting
            ? 'Choose a number (1 – 6)'
            : 'Select your delivery (1 – 6)'}
        </p>

        {/* Non-disruptive waiting indicator within arena (NO separate screen!) */}
        {isWaiting && (
          <div className="flex items-center space-x-2 mt-1 px-3 py-1 rounded-full bg-slate-900/80 border border-sky-400/40 shadow-md animate-pulse">
            <div className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span className="text-xs font-semibold text-sky-200">
              Opponent is choosing…
            </span>
          </div>
        )}
      </div>

      {/* 5. NUMBER SELECTION BUTTONS (1, 2, 3, 4, 5, 6) */}
      <div className="w-full max-w-sm sm:max-w-md flex items-center justify-between gap-1.5 sm:gap-3 px-2 py-2 z-10">
        {[1, 2, 3, 4, 5, 6].map((num) => {
          const isSelected = selectedNumber === num;
          return (
            <button
              key={num}
              onClick={() => onSelectNumber(num)}
              disabled={!isTurnInteractive}
              className={`
                relative flex-1 aspect-square max-w-[56px] sm:max-w-[64px]
                flex items-center justify-center rounded-full font-black text-xl sm:text-2xl
                transition-all duration-150 shadow-xl select-none
                ${
                  isSelected
                    ? 'bg-gradient-to-b from-amber-300 to-amber-500 text-slate-950 scale-110 ring-4 ring-amber-300/80 shadow-amber-500/50'
                    : isTurnInteractive
                    ? 'bg-gradient-to-b from-white via-slate-100 to-sky-100 text-slate-900 hover:scale-105 active:scale-95 hover:border-sky-400 border-2 border-white/80 shadow-sky-900/50'
                    : 'bg-slate-700/60 text-slate-400 border border-slate-600/40 cursor-not-allowed opacity-75'
                }
              `}
              aria-label={`Select ${num}`}
            >
              <span>{num}</span>
              {isSelected && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-sky-400 rounded-full animate-ping" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
