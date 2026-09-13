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
    <div className="relative w-full flex-1 flex flex-col items-center justify-end overflow-hidden select-none px-2 pb-2 sm:pb-3">
      {/* 1. BALL RESULT REVEAL OVERLAY (EVERY BALL SHOWS YOU vs COMPUTER) */}
      {eventFeedback && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-30 pointer-events-none px-4 animate-in fade-in zoom-in-95 duration-150">
          <div className="bg-slate-950/95 border-2 border-amber-400/80 rounded-3xl p-4 sm:p-5 shadow-[0_0_60px_rgba(0,0,0,0.9)] flex flex-col items-center text-center backdrop-blur-md max-w-xs sm:max-w-sm w-full">
            <span className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-amber-400/90 mb-1.5">
              Delivery Reveal
            </span>

            {/* YOU vs COMPUTER NUMBERS */}
            <div className="flex items-center justify-center space-x-5 sm:space-x-7 my-1.5">
              {/* YOU */}
              <div className="flex flex-col items-center">
                <span className="text-[11px] font-black uppercase tracking-wider text-slate-300 mb-1">
                  You
                </span>
                <div className="w-13 h-13 sm:w-16 sm:h-16 rounded-2xl bg-slate-900 border-2 border-amber-400 flex items-center justify-center text-3xl sm:text-4xl font-black text-amber-300 shadow-md">
                  {eventFeedback.userChoice ?? '-'}
                </div>
              </div>

              {/* VS */}
              <div className="text-sm sm:text-base font-black italic text-slate-500 pt-5">
                VS
              </div>

              {/* COMPUTER */}
              <div className="flex flex-col items-center">
                <span className="text-[11px] font-black uppercase tracking-wider text-slate-300 mb-1">
                  Computer
                </span>
                <div className="w-13 h-13 sm:w-16 sm:h-16 rounded-2xl bg-slate-900 border-2 border-slate-600 flex items-center justify-center text-3xl sm:text-4xl font-black text-slate-100 shadow-md">
                  {eventFeedback.computerChoice ?? '-'}
                </div>
              </div>
            </div>

            {/* CONTEXTUAL OUTCOME BADGE */}
            <div className="mt-3 w-full">
              {eventFeedback.type === 'WICKET' && (
                <div className="bg-red-600 border border-red-400 text-white font-black text-base sm:text-lg py-1.5 px-3 rounded-xl shadow-lg">
                  WICKET!
                  {eventFeedback.subtitle && (
                    <div className="text-xs font-semibold text-red-100 mt-0.5">
                      {eventFeedback.subtitle}
                    </div>
                  )}
                </div>
              )}
              {eventFeedback.type === 'SIX' && (
                <div className="bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-500 text-slate-950 font-black text-base sm:text-lg py-1.5 px-3 rounded-xl shadow-lg">
                  <span>SIX!</span> <span className="text-xs font-bold">+6 RUNS</span>
                </div>
              )}
              {eventFeedback.type === 'FOUR' && (
                <div className="bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-400 text-slate-950 font-black text-base sm:text-lg py-1.5 px-3 rounded-xl shadow-lg">
                  <span>FOUR!</span> <span className="text-xs font-bold">+4 RUNS</span>
                </div>
              )}
              {eventFeedback.type === 'NORMAL' && (
                <div className="bg-slate-800/95 border border-amber-400/40 text-amber-300 font-black text-sm sm:text-base py-1.5 px-3 rounded-xl shadow-md">
                  {eventFeedback.runs === 0 ? 'DOT BALL (0 Runs)' : `+${eventFeedback.runs} ${eventFeedback.runs === 1 ? 'RUN' : 'RUNS'}`}
                </div>
              )}
              {eventFeedback.userTimedOut && (
                <div className="text-[10px] text-amber-400 font-semibold mt-1">
                  ⏱️ Auto-picked on timeout
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 2. DYNAMIC DUAL-TONE HEADING WITH YELLOW BRUSH UNDERLINE */}
      <div className="w-full flex flex-col items-center justify-center mb-3 sm:mb-4 z-10">
        {isWaiting ? (
          <div className="flex flex-col items-center text-center">
            <h2 className="text-3xl sm:text-5xl font-black uppercase italic tracking-wide text-amber-400 drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)] font-sans">
              WAITING FOR OPPONENT
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
              <span>Resolving delivery...</span>
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

      {/* 3. CIRCULAR WHITE KEYPAD (1 - 6) MATCHING REFERENCE SPEC */}
      <div className="w-full max-w-sm sm:max-w-lg flex items-center justify-center z-10 mb-2 sm:mb-4">
        <div className="flex items-center justify-center gap-2.5 sm:gap-4 w-full px-2">
          {[1, 2, 3, 4, 5, 6].map((num) => {
            const isSelected = selectedNumber === num;
            return (
              <button
                key={num}
                onClick={() => onSelectNumber(num)}
                disabled={!isTurnInteractive}
                className={`
                  relative w-13 h-13 sm:w-18 sm:h-18 rounded-full aspect-square
                  flex items-center justify-center font-black text-2xl sm:text-4xl
                  transition-all duration-150 select-none
                  ${
                    isSelected
                      ? 'bg-gradient-to-b from-amber-300 to-amber-400 text-slate-950 scale-110 ring-4 ring-amber-400/90 shadow-[0_0_25px_rgba(251,191,36,0.6)] border-2 border-white'
                      : isTurnInteractive
                      ? 'bg-gradient-to-b from-white via-slate-50 to-slate-100 text-blue-700 hover:text-blue-800 hover:scale-105 active:scale-95 border-2 border-white/95 shadow-[0_4px_18px_rgba(0,0,0,0.35)] hover:shadow-[0_6px_24px_rgba(59,130,246,0.45)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 cursor-pointer'
                      : 'bg-white/40 text-slate-400 border border-white/20 cursor-not-allowed opacity-50 scale-95'
                  }
                `}
                aria-label={`Select ${num}`}
              >
                <span>{num}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
