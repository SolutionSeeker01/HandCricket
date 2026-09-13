import React, { useState } from 'react';

interface LandingScreenProps {
  onPlayVsComputer: () => void;
}

export const LandingScreen: React.FC<LandingScreenProps> = ({ onPlayVsComputer }) => {
  const [showRules, setShowRules] = useState(false);

  return (
    <div className="relative min-h-screen w-full flex flex-col items-center justify-between p-4 sm:p-6 overflow-x-hidden select-none bg-[#0a192f] text-white">
      {/* Stadium Background Atmosphere */}
      <div
        className="absolute inset-0 z-0 pointer-events-none bg-cover bg-center opacity-40 scale-105 filter blur-[1px]"
        style={{ backgroundImage: "url('/stadium-bg.png')" }}
      />
      <div className="absolute inset-0 z-0 pointer-events-none bg-gradient-to-b from-[#071322]/80 via-[#0a1c36]/60 to-[#050e1a]/95" />

      {/* Top Bar / Logo */}
      <header className="relative z-10 w-full max-w-4xl pt-6 sm:pt-10 flex flex-col items-center text-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-amber-500/15 border border-amber-400/40 text-amber-300 font-extrabold text-xs sm:text-sm tracking-widest uppercase shadow-lg shadow-amber-500/10 mb-3 animate-pulse">
          <span className="w-2 h-2 rounded-full bg-amber-400"></span>
          5-OVER INTERNATIONAL SHOWDOWN
        </div>
        <h1 className="text-4xl sm:text-6xl md:text-7xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-yellow-200 via-amber-300 to-amber-500 drop-shadow-[0_4px_12px_rgba(0,0,0,0.8)]">
          HAND CRICKET
        </h1>
        <p className="text-slate-300 text-sm sm:text-base font-medium max-w-md mt-2 drop-shadow-md">
          The nostalgic classroom finger cricket game, brought to life with pure authoritative cricket logic.
        </p>
      </header>

      {/* Main Game Mode Choices */}
      <main className="relative z-10 w-full max-w-3xl my-auto py-8 grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
        {/* Play vs Computer (ACTIVE) */}
        <div
          onClick={onPlayVsComputer}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onPlayVsComputer(); }}
          className="group relative flex flex-col justify-between p-6 sm:p-7 rounded-2xl bg-gradient-to-b from-blue-900/60 to-slate-900/80 border-2 border-amber-400/60 hover:border-amber-400 shadow-[0_0_25px_rgba(245,158,11,0.2)] hover:shadow-[0_0_35px_rgba(245,158,11,0.4)] transition-all duration-200 cursor-pointer transform hover:-translate-y-1 active:scale-[0.98] backdrop-blur-md"
        >
          <div className="absolute top-4 right-4 px-2.5 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/50 text-[10px] font-black tracking-wider text-emerald-300 uppercase">
            ACTIVE MODE
          </div>

          <div>
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-3xl shadow-lg shadow-amber-500/30 mb-4 group-hover:scale-105 transition-transform">
              🏏
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white group-hover:text-amber-300 transition-colors">
              Play vs Computer
            </h2>
            <p className="text-slate-300 text-sm mt-2 leading-relaxed">
              Select your nation (IND, AUS, ENG, SA), flip the coin, set your field, and outthink the smart AI bowler!
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">
            <span className="text-xs font-bold text-amber-300 tracking-wide uppercase">Solo Mode • 5 Overs</span>
            <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 font-black text-sm tracking-wide shadow-md group-hover:brightness-110">
              PLAY NOW <span className="text-base font-black">→</span>
            </span>
          </div>
        </div>

        {/* Play with Friend (COMING SOON) */}
        <div className="relative flex flex-col justify-between p-6 sm:p-7 rounded-2xl bg-gradient-to-b from-slate-900/50 to-slate-950/70 border border-white/15 opacity-80 backdrop-blur-sm select-none cursor-not-allowed">
          <div className="absolute top-4 right-4 px-2.5 py-0.5 rounded-full bg-amber-500/25 border border-amber-400/40 text-[10px] font-black tracking-wider text-amber-300 uppercase">
            COMING SOON
          </div>

          <div>
            <div className="w-14 h-14 rounded-xl bg-slate-800/80 border border-white/10 flex items-center justify-center text-3xl text-slate-400 mb-4">
              👥
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-slate-300">
              Play with Friend
            </h2>
            <p className="text-slate-400 text-sm mt-2 leading-relaxed">
              Create a custom match room, share your 6-letter room code, and battle your friends live across devices.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 tracking-wide uppercase">Multiplayer • Room Codes</span>
            <span className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-400 font-bold text-xs tracking-wider uppercase border border-white/10">
              LOCKED
            </span>
          </div>
        </div>
      </main>

      {/* Footer & How to Play modal toggle */}
      <footer className="relative z-10 w-full max-w-4xl pb-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400 border-t border-white/10 pt-4">
        <div>Hand Cricket Official • Slice 13 Pre-Match</div>
        <button
          onClick={() => setShowRules(true)}
          className="text-amber-400 hover:text-amber-300 font-bold underline underline-offset-4 cursor-pointer transition-colors"
        >
          📖 How to Play & Rules Guide
        </button>
      </footer>

      {/* How to Play Dialog */}
      {showRules && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-lg bg-gradient-to-b from-[#0e223d] to-[#081526] border-2 border-amber-400/50 rounded-2xl p-6 shadow-2xl text-white">
            <div className="flex items-center justify-between pb-3 border-b border-white/15">
              <h3 className="text-xl font-black text-amber-300 flex items-center gap-2">
                <span>🏏</span> Hand Cricket Rules
              </h3>
              <button
                onClick={() => setShowRules(false)}
                className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-slate-300 font-bold"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-3.5 text-sm text-slate-200">
              <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                <span className="font-black text-amber-400">1. Numbers (1 to 6):</span> In each delivery, both batter and bowler secretly choose a number from 1 to 6.
              </div>
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30">
                <span className="font-black text-rose-300">2. Wickets:</span> If both players choose the <span className="underline font-bold">exact same number</span>, the batter is OUT!
              </div>
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
                <span className="font-black text-emerald-300">3. Scoring Runs:</span> If the numbers differ, the batter scores their chosen number of runs (1, 2, 3, 4, 5, or 6).
              </div>
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30">
                <span className="font-black text-amber-300">4. Match Structure:</span> 5 overs per side (6 balls per over). Each bowler can bowl at most 1 over (5 unique bowlers required).
              </div>
            </div>

            <button
              onClick={() => setShowRules(false)}
              className="mt-6 w-full py-3 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 text-slate-950 font-black text-sm uppercase tracking-wider shadow-lg hover:brightness-110"
            >
              GOT IT, LET'S PLAY!
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
