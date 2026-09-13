import React, { useState } from 'react';
import { TeamRoster } from '../types';

interface TeamSelectionScreenProps {
  availableTeams: TeamRoster[];
  onSelectTeam: (teamId: string) => void;
  onBack: () => void;
  isLoading?: boolean;
}

// Reusable SVG Flags for Team Selection
const IndiaFlagSVG = () => (
  <svg viewBox="0 0 36 36" className="w-12 h-12 rounded-full shadow-lg border-2 border-white/30 shrink-0">
    <clipPath id="ts-clip-ind">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#ts-clip-ind)">
      <rect x="0" y="0" width="36" height="12" fill="#FF9933" />
      <rect x="0" y="12" width="36" height="12" fill="#FFFFFF" />
      <rect x="0" y="24" width="36" height="12" fill="#138808" />
      <circle cx="18" cy="18" r="4.2" fill="none" stroke="#000080" strokeWidth="0.9" />
      <circle cx="18" cy="18" r="0.9" fill="#000080" />
      {Array.from({ length: 8 }).map((_, i) => (
        <line
          key={i}
          x1="18"
          y1="18"
          x2={18 + 4.2 * Math.cos((i * Math.PI) / 4)}
          y2={18 + 4.2 * Math.sin((i * Math.PI) / 4)}
          stroke="#000080"
          strokeWidth="0.6"
        />
      ))}
    </g>
  </svg>
);

const AustraliaFlagSVG = () => (
  <svg viewBox="0 0 36 36" className="w-12 h-12 rounded-full shadow-lg border-2 border-white/30 shrink-0">
    <clipPath id="ts-clip-aus">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#ts-clip-aus)">
      <rect x="0" y="0" width="36" height="36" fill="#00008B" />
      <rect x="0" y="0" width="18" height="18" fill="#00247D" />
      <line x1="0" y1="0" x2="18" y2="18" stroke="#FFFFFF" strokeWidth="2.5" />
      <line x1="18" y1="0" x2="0" y2="18" stroke="#FFFFFF" strokeWidth="2.5" />
      <line x1="0" y1="0" x2="18" y2="18" stroke="#CF142B" strokeWidth="1.2" />
      <line x1="18" y1="0" x2="0" y2="18" stroke="#CF142B" strokeWidth="1.2" />
      <line x1="9" y1="0" x2="9" y2="18" stroke="#FFFFFF" strokeWidth="3.5" />
      <line x1="0" y1="9" x2="18" y2="9" stroke="#FFFFFF" strokeWidth="3.5" />
      <line x1="9" y1="0" x2="9" y2="18" stroke="#CF142B" strokeWidth="1.8" />
      <line x1="0" y1="9" x2="18" y2="9" stroke="#CF142B" strokeWidth="1.8" />
      <circle cx="28" cy="8" r="1.2" fill="#FFFFFF" />
      <circle cx="23" cy="13" r="1.2" fill="#FFFFFF" />
      <circle cx="31" cy="15" r="1.2" fill="#FFFFFF" />
      <circle cx="28" cy="22" r="1.5" fill="#FFFFFF" />
      <circle cx="25" cy="29" r="1.7" fill="#FFFFFF" />
    </g>
  </svg>
);

const EnglandFlagSVG = () => (
  <svg viewBox="0 0 36 36" className="w-12 h-12 rounded-full shadow-lg border-2 border-white/30 shrink-0">
    <clipPath id="ts-clip-eng">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#ts-clip-eng)">
      <rect x="0" y="0" width="36" height="36" fill="#FFFFFF" />
      <rect x="15" y="0" width="6" height="36" fill="#CF142B" />
      <rect x="0" y="15" width="36" height="6" fill="#CF142B" />
    </g>
  </svg>
);

const SouthAfricaFlagSVG = () => (
  <svg viewBox="0 0 36 36" className="w-12 h-12 rounded-full shadow-lg border-2 border-white/30 shrink-0">
    <clipPath id="ts-clip-sa">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#ts-clip-sa)">
      <rect x="0" y="0" width="36" height="18" fill="#E03C31" />
      <rect x="0" y="18" width="36" height="18" fill="#001489" />
      <polygon points="0,0 16,18 0,36 6,36 22,18 6,0" fill="#FFFFFF" />
      <rect x="16" y="14" width="20" height="8" fill="#FFFFFF" />
      <polygon points="0,2 14,18 0,34 4,34 18,18 4,2" fill="#007749" />
      <rect x="16" y="15.5" width="20" height="5" fill="#007749" />
      <polygon points="0,5 11,18 0,31" fill="#FFB81C" />
      <polygon points="0,8 8,18 0,28" fill="#000000" />
    </g>
  </svg>
);

const TEAM_DETAILS: Record<string, { flag: React.ReactNode; color: string; stars: string; highlight: string }> = {
  IND: {
    flag: <IndiaFlagSVG />,
    color: 'from-blue-900/80 via-indigo-950/80 to-blue-950/90',
    stars: '⭐⭐',
    highlight: 'Rohit, Kohli, Bumrah',
  },
  AUS: {
    flag: <AustraliaFlagSVG />,
    color: 'from-amber-950/80 via-yellow-950/70 to-slate-950/90',
    stars: '⭐⭐⭐⭐⭐',
    highlight: 'Warner, Maxwell, Starc',
  },
  ENG: {
    flag: <EnglandFlagSVG />,
    color: 'from-sky-950/80 via-blue-950/70 to-slate-950/90',
    stars: '⭐⭐',
    highlight: 'Root, Stokes, Buttler',
  },
  SA: {
    flag: <SouthAfricaFlagSVG />,
    color: 'from-emerald-950/80 via-green-950/70 to-slate-950/90',
    stars: '⭐',
    highlight: 'Klassen, Rabada, Jansen',
  },
};

export const TeamSelectionScreen: React.FC<TeamSelectionScreenProps> = ({
  availableTeams,
  onSelectTeam,
  onBack,
  isLoading = false,
}) => {
  const [selectedTeamId, setSelectedTeamId] = useState<string>('IND');
  const [viewingSquadId, setViewingSquadId] = useState<string | null>(null);

  // Fallback teams if list empty yet
  const teamsToDisplay = availableTeams.length > 0
    ? availableTeams
    : [
        { id: 'IND', name: 'India', players: [] },
        { id: 'AUS', name: 'Australia', players: [] },
        { id: 'ENG', name: 'England', players: [] },
        { id: 'SA', name: 'South Africa', players: [] },
      ];

  const handleContinue = () => {
    if (selectedTeamId && !isLoading) {
      onSelectTeam(selectedTeamId);
    }
  };

  const selectedTeamObj = teamsToDisplay.find((t) => t.id === selectedTeamId);
  const viewingTeamObj = teamsToDisplay.find((t) => t.id === viewingSquadId);

  return (
    <div className="relative min-h-screen w-full flex flex-col items-center justify-between p-4 sm:p-6 overflow-x-hidden select-none bg-[#0a192f] text-white">
      {/* Stadium Background Atmosphere */}
      <div
        className="absolute inset-0 z-0 pointer-events-none bg-cover bg-center opacity-35 scale-105 filter blur-[1px]"
        style={{ backgroundImage: "url('/stadium-bg.png')" }}
      />
      <div className="absolute inset-0 z-0 pointer-events-none bg-gradient-to-b from-[#071322]/85 via-[#0a1c36]/65 to-[#050e1a]/95" />

      {/* Header */}
      <header className="relative z-10 w-full max-w-4xl pt-4 sm:pt-6 flex flex-col items-center text-center">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-400/30 text-amber-300 font-extrabold text-xs tracking-widest uppercase mb-2">
          STEP 1 OF 3 • TEAM SELECTION
        </div>
        <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-yellow-200 via-amber-300 to-amber-500 drop-shadow-[0_4px_12px_rgba(0,0,0,0.8)]">
          CHOOSE YOUR TEAM
        </h1>
        <p className="text-slate-300 text-xs sm:text-sm font-medium mt-1">
          Pick your national side. Computer AI will automatically select an opponent team.
        </p>
      </header>

      {/* Team Grid */}
      <main className="relative z-10 w-full max-w-4xl my-auto py-6 grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-5">
        {teamsToDisplay.map((team) => {
          const isSelected = team.id === selectedTeamId;
          const meta = TEAM_DETAILS[team.id] || {
            flag: <div className="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center font-bold">{team.id}</div>,
            color: 'from-slate-900 to-slate-950',
            stars: '⭐',
            highlight: 'International Roster',
          };

          return (
            <div
              key={team.id}
              onClick={() => setSelectedTeamId(team.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedTeamId(team.id); }}
              className={`relative flex items-center justify-between p-4 sm:p-5 rounded-2xl bg-gradient-to-br ${meta.color} border-2 transition-all duration-200 cursor-pointer backdrop-blur-md ${
                isSelected
                  ? 'border-amber-400 shadow-[0_0_30px_rgba(245,158,11,0.4)] scale-[1.02]'
                  : 'border-white/15 hover:border-white/40 hover:bg-white/5 opacity-80 hover:opacity-100'
              }`}
            >
              <div className="flex items-center gap-4">
                {meta.flag}
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl sm:text-2xl font-black text-white tracking-wide">
                      {team.name}
                    </h3>
                    <span className="px-2 py-0.5 rounded bg-white/10 text-[11px] font-black text-amber-300">
                      {team.id}
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 mt-1 font-medium">
                    Key: {meta.highlight}
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setViewingSquadId(team.id);
                    }}
                    className="mt-2 inline-flex items-center text-[11px] font-bold text-amber-400 hover:text-amber-300 underline underline-offset-2"
                  >
                    View 11 Squad Players
                  </button>
                </div>
              </div>

              {/* Selection Indicator */}
              <div className="flex flex-col items-center justify-center">
                <div
                  className={`w-7 h-7 rounded-full border-2 flex items-center justify-center transition-all ${
                    isSelected
                      ? 'border-amber-400 bg-amber-400 text-slate-950 font-black text-sm shadow-md shadow-amber-400/50'
                      : 'border-white/30 bg-black/20'
                  }`}
                >
                  {isSelected ? '✓' : ''}
                </div>
              </div>
            </div>
          );
        })}
      </main>

      {/* Bottom Action Controls */}
      <footer className="relative z-10 w-full max-w-4xl pb-4 pt-2 flex items-center justify-between gap-4 border-t border-white/10">
        <button
          onClick={onBack}
          className="px-5 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white font-black text-xs sm:text-sm tracking-wider uppercase transition-all"
        >
          ← BACK
        </button>

        <div className="flex items-center gap-3">
          <div className="hidden sm:block text-right text-xs">
            <span className="text-slate-400">Selected: </span>
            <span className="font-extrabold text-amber-300">{selectedTeamObj?.name || 'None'}</span>
          </div>

          <button
            onClick={handleContinue}
            disabled={!selectedTeamId || isLoading}
            className={`px-6 sm:px-8 py-3 rounded-xl font-black text-xs sm:text-sm tracking-wider uppercase transition-all shadow-lg flex items-center gap-2 ${
              selectedTeamId && !isLoading
                ? 'bg-gradient-to-r from-amber-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 shadow-amber-500/30 hover:shadow-amber-500/50 cursor-pointer transform hover:scale-[1.02]'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/10'
            }`}
          >
            {isLoading ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></span>
                STARTING TOSS...
              </>
            ) : (
              <>
                PROCEED TO TOSS 🪙 →
              </>
            )}
          </button>
        </div>
      </footer>

      {/* Squad Players Preview Modal */}
      {viewingTeamObj && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-md bg-[#0d223f] border-2 border-amber-400/50 rounded-2xl p-5 shadow-2xl text-white">
            <div className="flex items-center justify-between pb-3 border-b border-white/15">
              <h3 className="text-lg font-black text-amber-300 flex items-center gap-2">
                {viewingTeamObj.name} ({viewingTeamObj.id}) Squad (11)
              </h3>
              <button
                onClick={() => setViewingSquadId(null)}
                className="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-slate-300 font-bold"
              >
                ✕
              </button>
            </div>

            <div className="mt-3 max-h-72 overflow-y-auto pr-1 space-y-1.5 custom-scrollbar">
              {viewingTeamObj.players && viewingTeamObj.players.length > 0 ? (
                viewingTeamObj.players.map((p, idx) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between p-2 rounded-lg bg-white/5 border border-white/5 text-xs text-slate-200"
                  >
                    <span className="font-bold text-amber-300 w-6">#{idx + 1}</span>
                    <span className="flex-1 font-semibold">{p.name}</span>
                    <span className="text-[10px] text-slate-400 uppercase font-mono">
                      {idx < 2 ? 'Opening' : idx < 7 ? 'Middle' : 'Bowler'}
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-400 py-4 text-center">11 Official International Players</div>
              )}
            </div>

            <button
              onClick={() => {
                setSelectedTeamId(viewingTeamObj.id);
                setViewingSquadId(null);
              }}
              className="mt-4 w-full py-2.5 rounded-xl bg-amber-400 text-slate-950 font-black text-xs uppercase tracking-wider hover:bg-amber-300"
            >
              SELECT THIS TEAM
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
