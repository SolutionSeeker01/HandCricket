import React, { useState } from 'react';

interface LandingScreenProps {
  onPlayVsComputer: () => void;
  onPlayWithFriend?: () => void;
}

export const LandingScreen: React.FC<LandingScreenProps> = ({
  onPlayVsComputer,
  onPlayWithFriend,
}) => {
  const [showRules, setShowRules] = useState(false);

  return (
    <div className="relative min-h-screen w-full flex flex-col items-center justify-between p-4 sm:p-6 overflow-x-hidden select-none bg-[url('/stadium_bg.jpg')] bg-cover bg-center text-white">
      {/* Stadium Background Atmosphere Overlay */}
      <div className="absolute inset-0 z-0 pointer-events-none bg-gradient-to-b from-slate-950/55 via-black/35 to-slate-950/75" />
      <div className="absolute inset-0 z-0 pointer-events-none bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-amber-500/10 via-transparent to-black/50" />

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
          The nostalgic classroom finger cricket game, brought to life with authentic cricket rules.
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

        {/* Play with Friend (Active when callback provided, otherwise Coming Soon) */}
        <div
          onClick={onPlayWithFriend}
          role={onPlayWithFriend ? 'button' : undefined}
          tabIndex={onPlayWithFriend ? 0 : -1}
          aria-disabled={!onPlayWithFriend}
          onKeyDown={(e) => {
            if (onPlayWithFriend && (e.key === 'Enter' || e.key === ' ')) onPlayWithFriend();
          }}
          className={`group relative flex flex-col justify-between p-6 sm:p-7 rounded-2xl bg-gradient-to-b from-purple-950/60 to-slate-900/80 border-2 ${
            onPlayWithFriend
              ? 'border-purple-400/50 hover:border-purple-400 shadow-[0_0_25px_rgba(168,85,247,0.2)] hover:shadow-[0_0_35px_rgba(168,85,247,0.4)] cursor-pointer transform hover:-translate-y-1 active:scale-[0.98]'
              : 'border-white/10 opacity-70 cursor-not-allowed'
          } transition-all duration-200 backdrop-blur-md`}
        >
          <div
            className={`absolute top-4 right-4 px-2.5 py-0.5 rounded-full ${
              onPlayWithFriend
                ? 'bg-purple-500/20 border border-purple-400/50 text-purple-300'
                : 'bg-white/10 border border-white/20 text-slate-400'
            } text-[10px] font-black tracking-wider uppercase`}
          >
            {onPlayWithFriend ? 'LIVE MULTIPLAYER' : 'COMING SOON'}
          </div>

          <div>
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-3xl shadow-lg shadow-purple-500/30 mb-4 group-hover:scale-105 transition-transform">
              👥
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white group-hover:text-purple-300 transition-colors">
              Play with Friend
            </h2>
            <p className="text-slate-300 text-sm mt-2 leading-relaxed">
              Create a custom match room, share your 6-letter room code, and battle your friends live across devices.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">
            <span className="text-xs font-bold text-purple-300 tracking-wide uppercase">
              Head-to-Head • Live Online
            </span>
            {onPlayWithFriend ? (
              <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-500 text-white font-black text-sm tracking-wide shadow-md group-hover:brightness-110">
                PLAY NOW <span className="text-base font-black">→</span>
              </span>
            ) : (
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Coming Soon
              </span>
            )}
          </div>
        </div>
      </main>

      {/* Footer & How to Play modal toggle */}
      <footer className="relative z-10 w-full max-w-4xl pb-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400 border-t border-white/10 pt-4">
        <div>Hand Cricket Official • Live Match Edition</div>
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
