import React, { useEffect, useState } from 'react';
import { TeamInfo } from '../types';
import { TeamFlagBadge } from './TeamFlags';

interface TossScreenProps {
  userTeam: TeamInfo | null;
  opponentTeam: TeamInfo | null;
  tossWinner: 'user' | 'computer' | null;
  tossDecision: 'BAT' | 'BOWL' | null;
  onChooseToss: (decision: 'BAT' | 'BOWL') => void;
  onProceed?: () => void;
  isLoading?: boolean;
  isFriendMode?: boolean;
}

export const TossScreen: React.FC<TossScreenProps> = ({
  userTeam,
  opponentTeam,
  tossWinner,
  tossDecision,
  onChooseToss,
  onProceed,
  isLoading = false,
  isFriendMode = false,
}) => {
  // Coin animation state: flips for at least 2.2 seconds before showing result
  const [isFlipping, setIsFlipping] = useState<boolean>(true);
  const [animationCompleted, setAnimationCompleted] = useState<boolean>(false);
  const [hasLanded, setHasLanded] = useState<boolean>(false);

  useEffect(() => {
    // 2.2 seconds flip duration
    const flipTimer = window.setTimeout(() => {
      setIsFlipping(false);
      setHasLanded(true);
      // Brief impact settle
      const settleTimer = window.setTimeout(() => {
        setAnimationCompleted(true);
      }, 300);
      return () => window.clearTimeout(settleTimer);
    }, 2200);

    return () => window.clearTimeout(flipTimer);
  }, []);

  // If computer won (in Computer Mode), automatically proceed after showing their decision for 2.5 seconds
  useEffect(() => {
    if (!isFriendMode && animationCompleted && tossWinner === 'computer' && onProceed) {
      const autoProceedTimer = window.setTimeout(() => {
        onProceed();
      }, 2500);
      return () => window.clearTimeout(autoProceedTimer);
    }
  }, [animationCompleted, tossWinner, onProceed, isFriendMode]);

  const userTeamName = userTeam?.name?.toUpperCase() || 'INDIA';
  const userTeamId = userTeam?.id || 'IND';
  const oppTeamName = opponentTeam?.name?.toUpperCase() || 'AUSTRALIA';
  const oppTeamId = opponentTeam?.id || 'AUS';

  const showResult = animationCompleted && tossWinner !== null;

  return (
    <div className="relative w-full min-h-[100dvh] flex flex-col items-center justify-between p-3 sm:p-6 overflow-y-auto overflow-x-hidden select-none bg-[url('/stadium_bg.jpg')] bg-cover bg-center text-white">
      {/* Stadium Light & Vignette Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-slate-950/50 via-black/25 to-slate-950/75 pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-amber-500/10 via-transparent to-black/50 pointer-events-none" />

      {/* Top Bar / Broadcast Header */}
      <header className="relative z-10 w-full max-w-4xl pt-2 sm:pt-4 flex flex-col items-center text-center">
        <div className="inline-flex items-center gap-2 px-3 sm:px-4 py-1 rounded-full bg-black/50 border border-amber-400/40 text-amber-300 font-extrabold text-[11px] sm:text-xs tracking-widest uppercase shadow-lg shadow-black/40 backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span>
          OFFICIAL MATCH TOSS • 5 OVERS
        </div>
      </header>

      {/* Main Center Stage: Both Teams on Sides + Large Cricket Coin in Center */}
      <main className="relative z-10 w-full max-w-5xl my-auto flex flex-col items-center justify-center py-2">
        {/* Teams Matchup Header (Mobile compact & Desktop side-by-side) */}
        <div className="w-full flex items-center justify-between px-1 sm:px-8 mb-4 sm:mb-8">
          {/* YOU (User Side) */}
          <div
            className={`flex flex-col sm:flex-row items-center gap-1.5 sm:gap-4 p-2 sm:p-5 rounded-2xl bg-slate-950/60 border-2 backdrop-blur-md transition-all duration-500 max-w-[46%] sm:max-w-none ${
              showResult && tossWinner === 'user'
                ? 'border-amber-400 shadow-[0_0_35px_rgba(245,158,11,0.5)] scale-105'
                : 'border-white/15'
            }`}
          >
            <TeamFlagBadge id={userTeamId} className="w-10 h-10 sm:w-16 sm:h-16" />
            <div className="text-center sm:text-left">
              <span className="inline-block px-2 py-0.5 rounded-full bg-amber-400 text-slate-950 text-[9px] sm:text-xs font-black tracking-widest uppercase">
                YOU
              </span>
              <h3 className="text-xs sm:text-2xl font-black tracking-wide text-white drop-shadow-md mt-0.5 truncate max-w-[110px] sm:max-w-none">
                {userTeamName}
              </h3>
              <span className="text-[9px] sm:text-xs font-bold text-amber-300 font-mono">
                [{userTeamId}]
              </span>
            </div>
          </div>

          {/* VS Divider in between */}
          <div className="flex flex-col items-center justify-center px-1">
            <span className="text-lg sm:text-3xl font-black italic text-amber-400 drop-shadow-[0_2px_10px_rgba(0,0,0,0.8)]">
              VS
            </span>
          </div>

          {/* COMPUTER (Opponent Side) */}
          <div
            className={`flex flex-col-reverse sm:flex-row items-center gap-1.5 sm:gap-4 p-2 sm:p-5 rounded-2xl bg-slate-950/60 border-2 backdrop-blur-md transition-all duration-500 max-w-[46%] sm:max-w-none ${
              showResult && tossWinner === 'computer'
                ? 'border-amber-400 shadow-[0_0_35px_rgba(245,158,11,0.5)] scale-105'
                : 'border-white/15'
            }`}
          >
            <div className="text-center sm:text-right">
              <span className="inline-block px-2 py-0.5 rounded-full bg-sky-400 text-slate-950 text-[9px] sm:text-xs font-black tracking-widest uppercase">
                {isFriendMode ? 'OPPONENT' : 'COMPUTER'}
              </span>
              <h3 className="text-xs sm:text-2xl font-black tracking-wide text-white drop-shadow-md mt-0.5 truncate max-w-[110px] sm:max-w-none">
                {oppTeamName}
              </h3>
              <span className="text-[9px] sm:text-xs font-bold text-sky-300 font-mono">
                [{oppTeamId}]
              </span>
            </div>
            <TeamFlagBadge id={oppTeamId} className="w-10 h-10 sm:w-16 sm:h-16" />
          </div>
        </div>

        {/* Center: The Cricket Coin */}
        <div className="relative flex flex-col items-center justify-center my-2 sm:my-4">
          {/* 3D Animated Coin */}
          <div className="relative flex items-center justify-center">
            <div
              className={`w-24 h-24 sm:w-36 sm:h-36 rounded-full bg-gradient-to-tr from-amber-600 via-yellow-300 to-amber-500 border-4 border-yellow-100 shadow-[0_0_45px_rgba(245,158,11,0.6)] flex items-center justify-center transition-all ${
                isFlipping ? 'animate-coin-flip' : hasLanded ? 'scale-100' : ''
              }`}
            >
              {/* Inner embossed cricket emblem */}
              <div className="w-18 h-18 sm:w-28 sm:h-28 rounded-full border-2 border-amber-600/40 bg-gradient-to-br from-amber-400 to-yellow-500 flex flex-col items-center justify-center shadow-inner text-slate-950 font-black">
                <span className="text-3xl sm:text-4xl drop-shadow-sm">🏏</span>
                <span className="text-[9px] sm:text-[11px] font-black tracking-wider uppercase text-amber-950">
                  HAND CRICKET
                </span>
              </div>
            </div>

            {/* Coin Drop Shadow on Stadium Turf */}
            <div
              className={`absolute -bottom-6 w-20 sm:w-28 h-4 rounded-full bg-black/60 blur-sm pointer-events-none transition-all ${
                isFlipping ? 'animate-coin-shadow' : 'scale-100 opacity-60'
              }`}
            />
          </div>

          {/* Animation status text during flip */}
          {isFlipping && (
            <div className="mt-7 inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-black/60 border border-amber-400/40 text-amber-300 text-xs sm:text-sm font-extrabold tracking-wider uppercase animate-pulse backdrop-blur-md">
              <span>🪙</span> COIN IN THE AIR...
            </div>
          )}
        </div>

        {/* Revealed Outcome & Interactive Decision UI */}
        {showResult && (
          <div className="mt-4 sm:mt-6 w-full max-w-xl animate-intro-title">
            {tossWinner === 'user' ? (
              /* User Won the Toss */
              <div className="p-5 sm:p-7 rounded-3xl bg-slate-950/80 border-2 border-amber-400 shadow-[0_0_40px_rgba(245,158,11,0.35)] backdrop-blur-md text-center">
                <div className="inline-block px-3.5 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/50 text-emerald-300 font-black text-xs sm:text-sm uppercase tracking-widest mb-2">
                  🎉 TOSS RESULT
                </div>
                <h2 className="text-2xl sm:text-4xl font-black text-white tracking-tight drop-shadow-md">
                  YOU WON THE TOSS!
                </h2>
                <p className="text-slate-300 text-xs sm:text-sm font-medium mt-1">
                  Choose your strategy for this 5-over match:
                </p>

                {/* BAT FIRST / BOWL FIRST Action Buttons */}
                <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3.5 sm:gap-4">
                  <button
                    onClick={() => onChooseToss('BAT')}
                    disabled={isLoading}
                    className="group relative p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 border-2 border-amber-200 shadow-xl shadow-amber-500/20 transition-all cursor-pointer transform hover:scale-[1.02] active:scale-95 text-left"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-3xl">🏏</span>
                      <span className="text-xs font-black tracking-wider uppercase px-2 py-0.5 rounded bg-slate-950/20 text-slate-950">
                        RECOMMENDED
                      </span>
                    </div>
                    <div className="text-xl sm:text-2xl font-black mt-2">
                      BAT FIRST
                    </div>
                    <div className="text-xs text-slate-900 font-semibold mt-0.5">
                      Set a formidable target for Computer to chase.
                    </div>
                  </button>

                  <button
                    onClick={() => onChooseToss('BOWL')}
                    disabled={isLoading}
                    className="group relative p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 border-2 border-emerald-200 shadow-xl shadow-emerald-500/20 transition-all cursor-pointer transform hover:scale-[1.02] active:scale-95 text-left"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-3xl">🎯</span>
                      <span className="text-xs font-black tracking-wider uppercase px-2 py-0.5 rounded bg-slate-950/20 text-slate-950">
                        FIELD FIRST
                      </span>
                    </div>
                    <div className="text-xl sm:text-2xl font-black mt-2">
                      BOWL FIRST
                    </div>
                    <div className="text-xs text-slate-900 font-semibold mt-0.5">
                      Restrict Computer's score, then chase it down.
                    </div>
                  </button>
                </div>
              </div>
            ) : (
              /* Opponent / Computer Won the Toss */
              <div className="p-5 sm:p-7 rounded-3xl bg-slate-950/80 border-2 border-sky-400 shadow-[0_0_40px_rgba(56,189,248,0.3)] backdrop-blur-md text-center">
                <div className="inline-block px-3.5 py-1 rounded-full bg-sky-500/20 border border-sky-400/50 text-sky-300 font-black text-xs sm:text-sm uppercase tracking-widest mb-2">
                  OPPONENT DECISION
                </div>
                <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight drop-shadow-md">
                  {isFriendMode ? 'OPPONENT WON THE TOSS' : 'COMPUTER WON THE TOSS'}
                </h2>

                {isFriendMode && !tossDecision ? (
                  <div className="mt-4 py-4 px-6 rounded-2xl bg-black/40 border border-white/10 inline-block">
                    <span className="text-xs text-slate-300 uppercase tracking-wider block font-bold">
                      Waiting for opponent's decision...
                    </span>
                    <div className="flex items-center justify-center gap-2 mt-3 text-xs text-amber-300 font-bold animate-pulse">
                      <span className="w-2 h-2 rounded-full bg-amber-400" />
                      <span>Opponent is choosing to bat or bowl</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="mt-3 py-3 px-5 rounded-2xl bg-black/40 border border-white/10 inline-block">
                      <span className="text-xs text-slate-300 uppercase tracking-wider block font-bold">
                        {isFriendMode ? 'Opponent elected to:' : 'Computer elected to:'}
                      </span>
                      <span className="text-2xl sm:text-3xl font-black text-amber-400 tracking-wide mt-0.5 block">
                        {tossDecision === 'BAT' ? 'BAT FIRST 🏏' : 'BOWL FIRST 🎯'}
                      </span>
                    </div>

                    <p className="text-xs sm:text-sm font-semibold text-slate-200 mt-3">
                      {tossDecision === 'BAT'
                        ? 'You will bowl first. Prepare to select your opening bowler!'
                        : 'You will bat first. Entering the pitch now!'}
                    </p>

                    {!isFriendMode && (
                      <div className="mt-4 flex items-center justify-center gap-3">
                        <button
                          onClick={() => onProceed && onProceed()}
                          className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 font-black text-xs sm:text-sm tracking-wider uppercase shadow-lg transition-all transform hover:scale-105 active:scale-95"
                        >
                          CONTINUE TO MATCH →
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full max-w-4xl pb-3 text-center text-xs text-slate-300/80 font-medium">
        Hand Cricket Official • Match Toss
      </footer>
    </div>
  );
};
