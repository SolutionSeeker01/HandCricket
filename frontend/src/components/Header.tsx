import React from 'react';
import { MatchState } from '../types';

interface HeaderProps {
  matchState: MatchState | null;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({ matchState, onOpenSettings }) => {
  const overs = matchState ? `${matchState.overs} / ${matchState.max_overs}` : '0.0 / 5';
  const score = matchState ? `${matchState.score} / ${matchState.wickets}` : '0 / 0';
  const target = matchState?.target;

  return (
    <header className="w-full flex items-center justify-between px-3 py-2 sm:px-6 sm:py-3 z-30">
      {/* Branding */}
      <div className="flex flex-col text-left select-none">
        <div className="flex items-center space-x-1">
          <span className="text-2xl sm:text-3xl font-black italic tracking-wider text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)] font-sans">
            Hand
          </span>
          <span className="text-2xl sm:text-3xl font-black italic tracking-wider text-amber-400 drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)] font-sans">
            Cricket
          </span>
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-600 border border-white -mt-3 shadow-sm" />
        </div>
        <span className="text-[11px] sm:text-xs text-white/90 font-medium tracking-wide drop-shadow">
          Small numbers. Big fun.
        </span>
      </div>

      {/* Central Over & Score Status Pills */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Over Pill */}
        <div className="flex flex-col items-center justify-center bg-slate-900/80 backdrop-blur-md border border-slate-700/60 rounded-2xl px-3 py-1 sm:px-4 sm:py-1.5 shadow-lg min-w-[65px] sm:min-w-[75px]">
          <span className="text-[9px] sm:text-[10px] uppercase font-bold tracking-wider text-slate-300">
            Over
          </span>
          <span className="text-xs sm:text-sm font-black text-white tracking-wide">
            {overs}
          </span>
        </div>

        {/* Score Pill */}
        <div className="flex flex-col items-center justify-center bg-slate-900/80 backdrop-blur-md border border-slate-700/60 rounded-2xl px-3 py-1 sm:px-4 sm:py-1.5 shadow-lg min-w-[65px] sm:min-w-[75px]">
          <span className="text-[9px] sm:text-[10px] uppercase font-bold tracking-wider text-slate-300">
            Score
          </span>
          <span className="text-xs sm:text-sm font-black text-amber-400 tracking-wide">
            {score}
          </span>
        </div>

        {/* Target Pill (when applicable in Innings 2) */}
        {target !== null && target !== undefined && (
          <div className="hidden sm:flex flex-col items-center justify-center bg-emerald-950/80 backdrop-blur-md border border-emerald-500/50 rounded-2xl px-3 py-1 sm:px-4 sm:py-1.5 shadow-lg">
            <span className="text-[9px] sm:text-[10px] uppercase font-bold tracking-wider text-emerald-300">
              Target
            </span>
            <span className="text-xs sm:text-sm font-black text-emerald-300 tracking-wide">
              {target}
            </span>
          </div>
        )}
      </div>

      {/* Right: Mode Badge & Settings */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* vs Computer Pill */}
        <div className="hidden sm:flex items-center space-x-2 bg-slate-900/80 backdrop-blur-md border border-slate-700/60 rounded-2xl px-3 py-1.5 shadow-lg text-xs font-bold text-slate-200">
          <svg className="w-4 h-4 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="10" rx="2" />
            <circle cx="12" cy="5" r="2" />
            <path d="M12 7v4" />
            <line x1="8" y1="16" x2="8" y2="16" strokeWidth="3" />
            <line x1="16" y1="16" x2="16" y2="16" strokeWidth="3" />
          </svg>
          <span>vs Computer</span>
        </div>

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          className="p-2 sm:p-2.5 bg-slate-900/80 hover:bg-slate-800 backdrop-blur-md text-slate-200 hover:text-white rounded-2xl border border-slate-700/60 shadow-lg transition-all active:scale-95 focus:outline-none"
          title="Match Details & Settings"
          aria-label="Settings"
        >
          <svg
            className="w-4 h-4 sm:w-5 sm:h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>
      </div>
    </header>
  );
};
