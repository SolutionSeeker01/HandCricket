import React from 'react';
import { MatchState } from '../types';

interface InningsBreakModalProps {
  matchState: MatchState;
  onStartNextInnings: () => void;
  isWaitingOpponent?: boolean;
}

export const InningsBreakModal: React.FC<InningsBreakModalProps> = ({
  matchState,
  onStartNextInnings,
  isWaitingOpponent = false,
}) => {
  if (matchState.status !== 'INNINGS_BREAK') {
    return null;
  }

  // Authoritative user_batted_first from match state, fallback to user_is_batting
  const userBattedFirst = matchState.user_batted_first ?? matchState.user_is_batting;
  const battingTeam = userBattedFirst ? matchState.user_team : matchState.opponent_team;
  const chasingTeam = userBattedFirst ? matchState.opponent_team : matchState.user_team;
  const target = matchState.target;
  const score = matchState.innings_1_score ?? matchState.score;
  const wickets = matchState.innings_1_wickets ?? matchState.wickets;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-sm bg-gradient-to-b from-slate-800 via-slate-900 to-slate-950 border border-slate-700 rounded-3xl p-6 shadow-2xl text-center flex flex-col items-center">
        {/* Subtle decorative glow */}
        <div className="absolute -top-12 w-48 h-48 bg-sky-500/10 rounded-full blur-2xl pointer-events-none" />

        {/* Heading */}
        <span className="text-xs font-bold uppercase tracking-widest text-sky-400 mb-2">
          First Innings Complete
        </span>
        <h2 className="text-3xl font-black italic tracking-wide text-white drop-shadow mb-4">
          End of Innings
        </h2>

        {/* Team Badge and Score Banner */}
        <div className="flex items-center justify-center space-x-3 my-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-700 flex items-center justify-center font-black text-lg text-white shadow-lg border border-blue-400/40">
            {battingTeam.id}
          </div>
          <div className="text-left">
            <div className="text-4xl font-black text-amber-400 tracking-tight">
              {score} / {wickets}
            </div>
            <div className="text-xs font-semibold text-slate-400">
              in {matchState.max_overs} overs
            </div>
          </div>
        </div>

        {/* Target Callout Box */}
        <div className="w-full bg-slate-900/90 border border-slate-700/80 rounded-2xl p-3 my-5 shadow-inner">
          <div className="text-xs text-slate-400 font-medium mb-0.5">
            Target to Chase
          </div>
          <div className="text-base font-extrabold text-emerald-400">
            {chasingTeam.name} need{' '}
            <span className="text-xl text-amber-300 font-black">{target}</span>{' '}
            runs to win
          </div>
        </div>

        {/* Next Innings Primary Button */}
        <button
          onClick={onStartNextInnings}
          disabled={isWaitingOpponent}
          className={`w-full py-3.5 px-6 rounded-2xl font-black text-base tracking-wider uppercase transition-all flex items-center justify-center space-x-2 ${
            isWaitingOpponent
              ? 'bg-slate-700 text-slate-400 cursor-not-allowed border border-slate-600 animate-pulse'
              : 'text-slate-950 bg-gradient-to-r from-amber-400 via-amber-300 to-amber-400 hover:brightness-110 active:scale-98 shadow-lg shadow-amber-500/25'
          }`}
        >
          {isWaitingOpponent ? (
            <>
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping inline-block mr-1" />
              <span>Waiting for Opponent...</span>
            </>
          ) : (
            <>
              <span>Next Innings</span>
              <svg
                className="w-5 h-5 text-slate-950"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={3}
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
