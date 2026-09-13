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
    <header className="w-full flex items-center justify-between px-3 py-2 sm:px-6 sm:py-3 z-20">
      {/* Branding */}
      <div className="flex flex-col text-left select-none">
        <div className="flex items-center space-x-1">
          <span className="text-xl sm:text-2xl font-black italic tracking-wider text-white drop-shadow-md">
            Hand
          </span>
          <span className="text-xl sm:text-2xl font-black italic tracking-wider text-amber-400 drop-shadow-md">
            Cricket
          </span>
        </div>
        <span className="text-[10px] sm:text-xs text-sky-200/70 font-medium tracking-wide">
          Small numbers. Big fun.
        </span>
      </div>

      {/* Central Over & Score Pills */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Over Pill */}
        <div className="flex flex-col items-center justify-center bg-slate-900/80 backdrop-blur-md border border-slate-700/60 rounded-xl px-2.5 py-1 sm:px-4 sm:py-1.5 shadow-lg">
          <span className="text-[9px] sm:text-[11px] uppercase font-bold tracking-wider text-slate-400">
            Over
          </span>
          <span className="text-xs sm:text-sm font-extrabold text-white tracking-wide">
            {overs}
          </span>
        </div>

        {/* Score Pill */}
        <div className="flex flex-col items-center justify-center bg-slate-900/80 backdrop-blur-md border border-slate-700/60 rounded-xl px-3 py-1 sm:px-4 sm:py-1.5 shadow-lg">
          <span className="text-[9px] sm:text-[11px] uppercase font-bold tracking-wider text-slate-400">
            Score
          </span>
          <span className="text-xs sm:text-sm font-extrabold text-amber-400 tracking-wide">
            {score}
          </span>
        </div>

        {/* Target Pill (when applicable in Innings 2) */}
        {target !== null && target !== undefined && (
          <div className="hidden sm:flex flex-col items-center justify-center bg-emerald-950/70 backdrop-blur-md border border-emerald-500/40 rounded-xl px-3 py-1 sm:px-4 sm:py-1.5 shadow-lg">
            <span className="text-[9px] sm:text-[11px] uppercase font-bold tracking-wider text-emerald-400">
              Target
            </span>
            <span className="text-xs sm:text-sm font-extrabold text-emerald-300 tracking-wide">
              {target}
            </span>
          </div>
        )}
      </div>

      {/* Settings / Menu Affordance */}
      <button
        onClick={onOpenSettings}
        className="p-2 sm:p-2.5 bg-slate-800/80 hover:bg-slate-700/90 text-slate-300 hover:text-white rounded-xl border border-slate-700/50 shadow-md transition-all active:scale-95 focus:outline-none"
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
    </header>
  );
};
