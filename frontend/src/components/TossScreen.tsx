import React from 'react';
import { TeamInfo } from '../types';

interface TossScreenProps {
  userTeam: TeamInfo | null;
  opponentTeam: TeamInfo | null;
  tossWinner: 'user' | 'computer' | null;
  tossDecision: 'BAT' | 'BOWL' | null;
  onChooseToss: (decision: 'BAT' | 'BOWL') => void;
  isLoading?: boolean;
}

export const TossScreen: React.FC<TossScreenProps> = ({
  userTeam,
  opponentTeam,
  tossWinner,
  tossDecision,
  onChooseToss,
  isLoading = false,
}) => {
  const isUserWinner = tossWinner === 'user';

  return (
    <div className="relative min-h-screen w-full flex flex-col items-center justify-between p-4 sm:p-6 overflow-x-hidden select-none bg-[#0a192f] text-white">
      {/* Stadium Background Atmosphere */}
      <div
        className="absolute inset-0 z-0 pointer-events-none bg-cover bg-center opacity-35 scale-105 filter blur-[1px]"
        style={{ backgroundImage: "url('/stadium-bg.png')" }}
      />
      <div className="absolute inset-0 z-0 pointer-events-none bg-gradient-to-b from-[#071322]/85 via-[#0a1c36]/65 to-[#050e1a]/95" />

      {/* Header */}
      <header className="relative z-10 w-full max-w-3xl pt-6 sm:pt-8 flex flex-col items-center text-center">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-400/30 text-amber-300 font-extrabold text-xs tracking-widest uppercase mb-3">
          STEP 2 OF 3 • THE TOSS
        </div>
        <div className="flex items-center gap-3 text-sm sm:text-base font-black text-slate-300">
          <span className="text-amber-400 font-black">{userTeam?.name || 'User'} ({userTeam?.id || 'IND'})</span>
          <span className="text-xs text-slate-500">VS</span>
          <span className="text-slate-300 font-black">{opponentTeam?.name || 'Computer'} ({opponentTeam?.id || 'AUS'})</span>
        </div>
      </header>

      {/* Center Toss Visual & Decision Card */}
      <main className="relative z-10 w-full max-w-lg my-auto py-6 flex flex-col items-center text-center">
        {/* Animated Coin */}
        <div className="relative mb-6">
          <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-tr from-amber-600 via-yellow-400 to-amber-300 border-4 border-amber-200 shadow-[0_0_40px_rgba(245,158,11,0.5)] flex items-center justify-center text-4xl sm:text-5xl animate-bounce">
            🪙
          </div>
          <div className="absolute -bottom-2 inset-x-0 h-4 bg-amber-500/20 blur-md rounded-full"></div>
        </div>

        {isUserWinner ? (
          /* User Won Toss */
          <div className="w-full bg-gradient-to-b from-blue-950/90 to-slate-900/90 border-2 border-amber-400/70 rounded-3xl p-6 sm:p-8 shadow-[0_0_35px_rgba(245,158,11,0.25)] backdrop-blur-md">
            <div className="inline-block px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/50 text-emerald-300 font-black text-xs uppercase tracking-widest mb-3">
              🎉 TOSS WON!
            </div>
            <h2 className="text-2xl sm:text-4xl font-black text-white tracking-tight">
              YOU WON THE TOSS!
            </h2>
            <p className="text-slate-300 text-sm mt-2 font-medium">
              What would you like to do first?
            </p>

            <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* BAT FIRST */}
              <button
                onClick={() => onChooseToss('BAT')}
                disabled={isLoading}
                className="group relative p-5 rounded-2xl bg-gradient-to-b from-amber-500/20 to-amber-600/10 hover:from-amber-500/30 hover:to-amber-600/20 border-2 border-amber-400 hover:border-amber-300 shadow-lg hover:shadow-amber-500/20 transition-all cursor-pointer transform hover:-translate-y-1 active:scale-95 text-left"
              >
                <div className="text-3xl mb-2">🏏</div>
                <div className="text-xl font-black text-amber-300 group-hover:text-yellow-200">
                  BAT FIRST
                </div>
                <div className="text-xs text-slate-300 mt-1">
                  Set a commanding 5-over total for Computer to chase.
                </div>
              </button>

              {/* BOWL FIRST */}
              <button
                onClick={() => onChooseToss('BOWL')}
                disabled={isLoading}
                className="group relative p-5 rounded-2xl bg-gradient-to-b from-emerald-500/20 to-emerald-600/10 hover:from-emerald-500/30 hover:to-emerald-600/20 border-2 border-emerald-400 hover:border-emerald-300 shadow-lg hover:shadow-emerald-500/20 transition-all cursor-pointer transform hover:-translate-y-1 active:scale-95 text-left"
              >
                <div className="text-3xl mb-2">🎯</div>
                <div className="text-xl font-black text-emerald-300 group-hover:text-emerald-200">
                  BOWL FIRST
                </div>
                <div className="text-xs text-slate-300 mt-1">
                  Restrict Computer's score, then chase it down.
                </div>
              </button>
            </div>
          </div>
        ) : (
          /* Computer Won Toss */
          <div className="w-full bg-gradient-to-b from-slate-900/90 to-blue-950/90 border-2 border-white/20 rounded-3xl p-6 sm:p-8 shadow-xl backdrop-blur-md">
            <div className="inline-block px-3 py-1 rounded-full bg-amber-500/20 border border-amber-400/40 text-amber-300 font-black text-xs uppercase tracking-widest mb-3">
              OPPONENT DECISION
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              COMPUTER WON THE TOSS
            </h2>
            <div className="mt-4 p-4 rounded-xl bg-white/5 border border-white/10 text-slate-200">
              <span className="text-sm font-medium">Computer has chosen to:</span>
              <div className="text-2xl sm:text-3xl font-black text-amber-400 mt-1 tracking-wide">
                {tossDecision === 'BAT' ? 'BAT FIRST 🏏' : 'BOWL FIRST 🎯'}
              </div>
            </div>
            <p className="text-xs text-slate-300 mt-4">
              {tossDecision === 'BAT'
                ? 'You will bowl first. Select your opening bowler to begin!'
                : 'You will bat first. Prepare to face the first over!'}
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full max-w-3xl pb-6 text-center text-xs text-slate-500">
        Hand Cricket • Official Server Authoritative Toss
      </footer>
    </div>
  );
};
