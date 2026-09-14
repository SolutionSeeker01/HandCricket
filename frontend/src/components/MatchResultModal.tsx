import React from 'react';
import { MatchState } from '../types';

interface MatchResultModalProps {
  matchState: MatchState;
  onPlayAgain: () => void;
  onExit?: () => void;
  isFriendMode?: boolean;
  isRematchRequested?: boolean;
  opponentWantsRematch?: boolean;
}

export const MatchResultModal: React.FC<MatchResultModalProps> = ({
  matchState,
  onPlayAgain,
  onExit,
  isFriendMode = false,
  isRematchRequested = false,
  opponentWantsRematch = false,
}) => {
  if (matchState.status !== 'COMPLETED') {
    return null;
  }

  const {
    winner,
    is_tie,
    result_description,
    user_team,
    opponent_team,
    user_batted_first,
    innings_1_score,
    innings_1_wickets,
    innings_2_score,
    innings_2_wickets,
  } = matchState;

  const isUserWinner = winner === user_team.name;
  const isOpponentWinner = winner === opponent_team.name;

  const userBattedFirst = user_batted_first ?? true;
  const innings1Team = userBattedFirst ? user_team : opponent_team;
  const innings2Team = userBattedFirst ? opponent_team : user_team;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-lg animate-in fade-in duration-300">
      <div className="relative w-full max-w-sm bg-gradient-to-b from-slate-800 via-slate-900 to-slate-950 border border-slate-700/80 rounded-3xl p-6 shadow-2xl text-center flex flex-col items-center overflow-hidden">
        {/* Decorative backdrop glows */}
        {isUserWinner && (
          <div className="absolute -top-10 w-60 h-60 bg-amber-400/20 rounded-full blur-3xl pointer-events-none" />
        )}
        {isOpponentWinner && (
          <div className="absolute -top-10 w-60 h-60 bg-red-500/15 rounded-full blur-3xl pointer-events-none" />
        )}
        {is_tie && (
          <div className="absolute -top-10 w-60 h-60 bg-sky-400/20 rounded-full blur-3xl pointer-events-none" />
        )}

        {/* Dynamic Heading based on outcome */}
        {is_tie ? (
          <div className="flex flex-col items-center">
            <span className="text-4xl mb-1">🤝</span>
            <h2 className="text-3xl sm:text-4xl font-black italic tracking-wide text-sky-300 drop-shadow">
              {isFriendMode ? 'MATCH TIED!' : "It's a Tie!"}
            </h2>
          </div>
        ) : isUserWinner ? (
          <div className="flex flex-col items-center">
            <span className="text-4xl mb-1 animate-bounce">🏆</span>
            <h2 className="text-3xl sm:text-4xl font-black italic tracking-wide text-amber-400 drop-shadow">
              {isFriendMode ? 'YOU WON!' : `${user_team.name} Win!`}
            </h2>
            {isFriendMode && (
              <p className="text-xs font-bold text-amber-200 uppercase tracking-widest mt-1">
                {user_team.name}
              </p>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <span className="text-4xl mb-1">🏏</span>
            <h2 className="text-3xl sm:text-4xl font-black italic tracking-wide text-slate-100 drop-shadow">
              {isFriendMode ? 'YOU LOST!' : `${opponent_team.name} Win!`}
            </h2>
            {isFriendMode && (
              <p className="text-xs font-bold text-slate-300 uppercase tracking-widest mt-1">
                {opponent_team.name}
              </p>
            )}
          </div>
        )}

        {/* Winning Team Badge (if not tie) */}
        {!is_tie && (
          <div className="my-4">
            <div
              className={`w-16 h-16 rounded-2xl flex items-center justify-center font-black text-2xl shadow-xl border-2 ${
                isUserWinner
                  ? 'bg-gradient-to-br from-blue-600 to-indigo-800 text-white border-blue-400/60 shadow-blue-500/25'
                  : 'bg-gradient-to-br from-amber-500 to-orange-700 text-slate-950 border-amber-300/60 shadow-amber-500/25'
              }`}
            >
              {isUserWinner ? user_team.id : opponent_team.id}
            </div>
          </div>
        )}

        {/* Match Summary Box */}
        <div className="w-full bg-slate-900/90 border border-slate-700/70 rounded-2xl p-4 my-4 shadow-inner space-y-2 text-xs sm:text-sm">
          <div data-testid="innings-1-summary" className="flex justify-between items-center text-slate-300 font-semibold border-b border-slate-800 pb-2">
            <span>{innings1Team.name}</span>
            <span className="font-extrabold text-white">
              {innings_1_score} / {innings_1_wickets}
            </span>
          </div>
          <div data-testid="innings-2-summary" className="flex justify-between items-center text-slate-300 font-semibold border-b border-slate-800 pb-2">
            <span>{innings2Team.name}</span>
            <span className="font-extrabold text-white">
              {innings_2_score} / {innings_2_wickets}
            </span>
          </div>
          <div className="pt-1 text-amber-300 font-extrabold text-xs sm:text-sm">
            {result_description || 'Match Concluded'}
          </div>
        </div>

        {/* Opponent Rematch Notification Badge */}
        {isFriendMode && opponentWantsRematch && !isRematchRequested && (
          <div
            data-testid="opponent-rematch-badge"
            className="mb-3 px-4 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-400 text-emerald-300 font-extrabold text-xs sm:text-sm animate-pulse flex items-center gap-1.5"
          >
            <span>🏏</span>
            <span>Opponent wants a rematch!</span>
          </div>
        )}

        {/* Buttons */}
        {isFriendMode ? (
          <div className="w-full flex flex-col gap-2.5">
            <button
              onClick={onPlayAgain}
              disabled={isRematchRequested}
              className={`w-full py-3.5 px-6 rounded-2xl font-black text-base tracking-wider uppercase transition-all flex items-center justify-center space-x-2 ${
                isRematchRequested
                  ? 'bg-slate-700 text-slate-400 cursor-not-allowed border border-slate-600 animate-pulse'
                  : 'text-slate-950 bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-400 hover:brightness-110 active:scale-98 shadow-lg shadow-amber-500/30 cursor-pointer'
              }`}
            >
              {isRematchRequested ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping inline-block mr-1" />
                  <span>Waiting for Opponent...</span>
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5 text-slate-950"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2.5}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  <span>Play Again</span>
                </>
              )}
            </button>

            <button
              onClick={onExit ?? onPlayAgain}
              className="w-full py-3 px-6 rounded-2xl font-bold text-sm tracking-wider uppercase text-slate-300 bg-slate-800/80 hover:bg-slate-700 hover:text-white border border-slate-700 transition-all cursor-pointer"
            >
              Return to Main Menu
            </button>
          </div>
        ) : (
          <button
            onClick={onPlayAgain}
            className="w-full py-3.5 px-6 rounded-2xl font-black text-base tracking-wider uppercase text-slate-950 bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-400 hover:brightness-110 active:scale-98 shadow-lg shadow-amber-500/30 transition-all flex items-center justify-center space-x-2 cursor-pointer"
          >
            <svg
              className="w-5 h-5 text-slate-950"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>Play Again</span>
          </button>
        )}
      </div>
    </div>
  );
};
