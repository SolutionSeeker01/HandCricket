import React from 'react';
import { EventFeedback, MatchState, MilestoneFeedback, TurnCountdown } from '../types';

interface PitchArenaProps {
  matchState: MatchState | null;
  selectedNumber: number | null;
  isWaiting: boolean;
  eventFeedback: EventFeedback | null;
  milestoneFeedback?: MilestoneFeedback | null;
  turnCountdown?: TurnCountdown | null;
  waitingTitle?: string;
  waitingSubtitle?: string;
  onSelectNumber: (num: number) => void;
}

export const PitchArena: React.FC<PitchArenaProps> = ({
  matchState,
  selectedNumber,
  isWaiting,
  eventFeedback,
  milestoneFeedback,
  turnCountdown,
  waitingTitle,
  waitingSubtitle,
  onSelectNumber,
}) => {
  const userIsBatting = matchState ? matchState.user_is_batting : true;
  const isTurnInteractive =
    matchState &&
    !isWaiting &&
    !eventFeedback &&
    !milestoneFeedback &&
    matchState.status !== 'INNINGS_BREAK' &&
    matchState.status !== 'COMPLETED';

  // Reveal ONLY the batter's number:
  // When user is batting -> userChoice (or batsmanChoice)
  // When computer is batting -> computerChoice (or batsmanChoice)
  // Opponent bowling number is NEVER displayed.
  const batterNumber = eventFeedback
    ? (eventFeedback.batsmanChoice ?? (userIsBatting ? eventFeedback.userChoice : eventFeedback.computerChoice) ?? eventFeedback.number ?? null)
    : null;

  return (
    <div className="relative w-full flex-1 flex flex-col items-center justify-end overflow-hidden select-none px-2 pb-2 sm:pb-3">
      {/* 1. NATURAL ON-FIELD BALL RESULT (BATTER'S NUMBER ONLY, NO BLUE CARD, BRIGHT STADIUM VISIBLE) */}
      {eventFeedback && (
        <div
          data-testid="onfield-ball-result"
          className="absolute top-12 sm:top-20 inset-x-0 flex flex-col items-center justify-center z-30 pointer-events-none px-4 animate-in fade-in zoom-in-95 duration-150"
        >
          {/* 1. NORMAL BALL (0, 1, 2, 3, 5 RUNS) */}
          {eventFeedback.type === 'NORMAL' && batterNumber !== null && (
            <div className="flex flex-col items-center text-center">
              <div className="text-7xl sm:text-9xl font-black text-white drop-shadow-[0_4px_24px_rgba(0,0,0,0.95)] tracking-tight leading-none font-sans">
                {batterNumber}
              </div>
              <div className="mt-2 sm:mt-3 text-2xl sm:text-4xl font-black tracking-wider text-amber-300 drop-shadow-[0_3px_14px_rgba(0,0,0,0.95)] uppercase font-sans">
                {eventFeedback.runs === 0 ? 'DOT BALL (0 Runs)' : `+${eventFeedback.runs} ${eventFeedback.runs === 1 ? 'RUN' : 'RUNS'}`}
              </div>
            </div>
          )}

          {/* 2. FOUR BOUNDARY */}
          {eventFeedback.type === 'FOUR' && batterNumber !== null && (
            <div className="relative flex flex-col items-center text-center animate-bounce">
              <div className="absolute -inset-8 bg-amber-400/20 rounded-full blur-2xl -z-10 animate-pulse pointer-events-none" />
              <div className="text-8xl sm:text-9xl font-black text-amber-300 drop-shadow-[0_0_40px_rgba(251,191,36,0.85)] tracking-tight leading-none font-sans">
                {batterNumber}
              </div>
              <div className="mt-2 sm:mt-3 px-6 sm:px-10 py-1.5 sm:py-2 rounded-full bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-400 text-slate-950 font-black text-2xl sm:text-4xl tracking-wider shadow-[0_6px_30px_rgba(251,191,36,0.6)] uppercase font-sans">
                FOUR! <span className="text-base sm:text-2xl font-bold ml-1">+4 RUNS</span>
              </div>
            </div>
          )}

          {/* 3. SIX MAXIMUM */}
          {eventFeedback.type === 'SIX' && batterNumber !== null && (
            <div className="relative flex flex-col items-center text-center animate-bounce">
              <div className="absolute -inset-10 bg-yellow-400/25 rounded-full blur-3xl -z-10 animate-pulse pointer-events-none" />
              <div className="text-8xl sm:text-9xl font-black text-yellow-300 drop-shadow-[0_0_45px_rgba(234,179,8,0.9)] tracking-tight leading-none font-sans">
                {batterNumber}
              </div>
              <div className="mt-2 sm:mt-3 px-7 sm:px-12 py-1.5 sm:py-2.5 rounded-full bg-gradient-to-r from-amber-500 via-yellow-300 to-amber-500 text-slate-950 font-black text-3xl sm:text-5xl tracking-widest shadow-[0_6px_35px_rgba(234,179,8,0.7)] uppercase font-sans">
                SIX! <span className="text-lg sm:text-3xl font-bold ml-1">+6 RUNS</span>
              </div>
            </div>
          )}

          {/* 4. WICKET (NO BATTER NUMBER DISPLAYED PER SPECIFICATION) */}
          {eventFeedback.type === 'WICKET' && (
            <div className="relative flex flex-col items-center text-center animate-in zoom-in-95 duration-150">
              <div className="absolute -inset-10 bg-red-600/30 rounded-full blur-3xl -z-10 animate-ping pointer-events-none" />
              <div className="px-8 sm:px-12 py-2 sm:py-3 rounded-full bg-red-600 text-white font-black text-3xl sm:text-5xl tracking-widest shadow-[0_6px_35px_rgba(220,38,38,0.75)] uppercase font-sans border-2 border-red-400/50">
                WICKET!
              </div>
              {eventFeedback.subtitle && (
                <div className="mt-2 text-base sm:text-lg font-extrabold text-red-100 drop-shadow-[0_2px_10px_rgba(0,0,0,0.95)]">
                  {eventFeedback.subtitle}
                </div>
              )}
            </div>
          )}

          {/* 5. OVER COMPLETE BANNER */}
          {eventFeedback.title === 'OVER COMPLETE' && (
            <div className="flex flex-col items-center text-center animate-in fade-in zoom-in-95 duration-200">
              <div className="px-8 sm:px-12 py-2 sm:py-3 rounded-full bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600 text-white font-black text-2xl sm:text-4xl tracking-widest shadow-[0_6px_35px_rgba(59,130,246,0.7)] uppercase font-sans border border-blue-300/40">
                OVER COMPLETE
              </div>
              <div className="mt-2 text-xs sm:text-sm font-bold text-slate-200 drop-shadow">
                Strike rotated • Preparing next over
              </div>
            </div>
          )}

          {/* Auto-Timeout indicator */}
          {eventFeedback.userTimedOut && (
            <div
              data-testid="timeout-auto-picked-badge"
              className="mt-3 inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-amber-500/20 border border-amber-400/80 text-amber-300 font-extrabold text-xs sm:text-sm tracking-wider uppercase drop-shadow-[0_0_12px_rgba(245,158,11,0.5)] animate-pulse"
            >
              <span>⏱️</span>
              <span>TIMEOUT — AUTO-PICKED</span>
            </div>
          )}
        </div>
      )}

      {/* 2. BATSMAN MILESTONE CELEBRATION (50 / 100) */}
      {milestoneFeedback && (
        <div
          data-testid="batsman-milestone-celebration"
          className="absolute top-12 sm:top-20 inset-x-0 flex flex-col items-center justify-center z-30 pointer-events-none px-4 animate-in zoom-in-95 duration-200"
        >
          <div className="text-4xl sm:text-6xl mb-1 drop-shadow animate-bounce">
            {milestoneFeedback.milestone === 100 ? '👑' : '🎉'}
          </div>
          <div className="text-2xl sm:text-4xl font-black text-white drop-shadow-[0_2px_12px_rgba(0,0,0,0.95)] uppercase tracking-wider font-sans">
            {milestoneFeedback.batsmanName}
          </div>
          <div className="text-7xl sm:text-9xl font-black text-amber-300 drop-shadow-[0_0_35px_rgba(251,191,36,0.85)] tracking-tight leading-none my-1 font-sans">
            {milestoneFeedback.milestone}
          </div>
          <div className="px-7 sm:px-12 py-1.5 sm:py-2.5 rounded-full bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-400 text-slate-950 font-black text-2xl sm:text-4xl tracking-widest shadow-[0_6px_30px_rgba(251,191,36,0.65)] uppercase font-sans">
            {milestoneFeedback.label}
          </div>
        </div>
      )}

      {/* 3. DYNAMIC DUAL-TONE HEADING WITH YELLOW BRUSH UNDERLINE & COUNTDOWN TIMER */}
      <div className="w-full flex flex-col items-center justify-center mb-2 sm:mb-3 z-10">
        {/* Compact Visual Countdown Bar */}
        {isTurnInteractive && turnCountdown && (
          <div
            data-testid="turn-countdown-bar"
            className="w-full max-w-[260px] sm:max-w-xs px-2 mb-2 flex flex-col items-center animate-in fade-in duration-150"
          >
            <div className="w-full flex items-center justify-between text-[11px] font-black tracking-wider uppercase mb-1">
              <span
                className={`flex items-center gap-1 transition-colors duration-150 ${
                  turnCountdown.isUrgent
                    ? 'text-red-400 animate-pulse font-extrabold'
                    : 'text-emerald-300'
                }`}
              >
                <span>⏱️</span>
                <span>
                  {turnCountdown.remainingSeconds > 0
                    ? `${turnCountdown.remainingSeconds}s remaining`
                    : 'Waiting for delivery...'}
                </span>
              </span>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                  turnCountdown.isUrgent
                    ? 'bg-red-500/30 text-red-300 border border-red-500/50 animate-bounce'
                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                }`}
              >
                {turnCountdown.remainingSeconds}s
              </span>
            </div>
            <div className="w-full h-1.5 sm:h-2 bg-slate-900/80 rounded-full overflow-hidden border border-slate-700/60 p-0.5 shadow-inner">
              <div
                className={`h-full rounded-full transition-all duration-200 ease-linear ${
                  turnCountdown.isUrgent
                    ? 'bg-gradient-to-r from-amber-500 to-red-500 shadow-[0_0_10px_rgba(239,68,68,0.8)]'
                    : 'bg-gradient-to-r from-teal-400 to-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.5)]'
                }`}
                style={{
                  width: `${Math.min(100, Math.max(0, (turnCountdown.remainingSeconds / turnCountdown.totalSeconds) * 100))}%`,
                }}
              />
            </div>
          </div>
        )}

        {eventFeedback || milestoneFeedback ? (
          <div className="h-[72px] sm:h-[88px] flex items-center justify-center pointer-events-none" aria-hidden="true" />
        ) : isWaiting ? (
          <div className="flex flex-col items-center text-center">
            <h2 className="text-3xl sm:text-5xl font-black uppercase italic tracking-wide text-amber-400 drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)] font-sans">
              {waitingTitle || 'WAITING FOR OPPONENT'}
            </h2>
            <svg
              className="w-48 sm:w-64 h-3.5 text-amber-400 -mt-0.5 mb-1"
              viewBox="0 0 160 12"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M3 9C45 3 115 2 157 7C125 10 50 11 3 9Z"
                fill="currentColor"
                opacity="0.9"
              />
            </svg>
            <p className="text-xs sm:text-sm font-bold text-slate-200 drop-shadow flex items-center justify-center space-x-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping inline-block mr-1.5" />
              <span>{waitingSubtitle || 'Resolving delivery...'}</span>
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center text-center">
            {/* Heading: YOUR SHOT (white + gold) */}
            <div className="relative inline-flex flex-col items-center">
              <h2 className="text-4xl sm:text-6xl font-black uppercase italic tracking-wide drop-shadow-[0_4px_12px_rgba(0,0,0,0.9)] font-sans">
                <span className="sr-only">{userIsBatting ? 'YOUR SHOT' : 'YOUR DELIVERY'}</span>
                <span aria-hidden="true">
                  <span className="text-white">YOUR </span>
                  <span className="text-[#facc15]">{userIsBatting ? 'SHOT' : 'DELIVERY'}</span>
                </span>
              </h2>
              {/* Yellow Brush Underline under SHOT / DELIVERY */}
              <svg
                className="w-28 sm:w-44 h-3 sm:h-4 text-[#facc15] self-end mr-1 sm:mr-3 -mt-1 sm:-mt-1.5 mb-1"
                viewBox="0 0 140 14"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M4 11C35 4 85 2 136 7C105 11 50 12 4 11Z"
                  fill="currentColor"
                  opacity="0.95"
                />
              </svg>
            </div>
            <p className="text-xs sm:text-sm font-bold tracking-wide text-white drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)] mt-0.5">
              {userIsBatting
                ? 'Choose your number (1 – 6)'
                : 'Choose your delivery (1 – 6)'}
            </p>
          </div>
        )}
      </div>

      {/* 4. CIRCULAR WHITE KEYPAD (1 - 6) - GUARANTEED TRUE PERFECT CIRCLES */}
      <div className="w-full flex items-center justify-center z-10 mb-2 sm:mb-4 px-1 sm:px-2">
        <div className="flex items-center justify-center gap-1.5 min-[370px]:gap-2 sm:gap-4 max-w-full">
          {[1, 2, 3, 4, 5, 6].map((num) => {
            const isSelected = selectedNumber === num;
            return (
              <button
                key={num}
                onClick={() => onSelectNumber(num)}
                disabled={!isTurnInteractive}
                style={{ aspectRatio: '1 / 1' }}
                className={`
                  relative w-10 h-10 min-[370px]:w-12 min-[370px]:h-12 sm:w-16 sm:h-16 rounded-full aspect-square shrink-0
                  flex items-center justify-center font-black text-xl min-[370px]:text-2xl sm:text-3xl leading-none
                  transition-all duration-150 select-none
                  ${
                    isSelected
                      ? 'bg-gradient-to-b from-amber-300 to-amber-400 text-slate-950 scale-110 ring-4 ring-amber-400/90 shadow-[0_0_25px_rgba(251,191,36,0.6)] border-2 border-white'
                      : isTurnInteractive
                      ? 'bg-gradient-to-b from-white via-slate-50 to-slate-100 text-blue-700 hover:text-blue-800 hover:scale-105 active:scale-95 hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] border-2 border-white/95 shadow-[0_4px_18px_rgba(0,0,0,0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 cursor-pointer'
                      : 'bg-white/40 text-slate-400 border border-white/20 cursor-not-allowed opacity-45 scale-95'
                  }
                `}
                aria-label={`Select ${num}`}
              >
                <span className="translate-y-[-1px]">{num}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
