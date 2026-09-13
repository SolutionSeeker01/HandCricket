import React, { useState } from 'react';
import { TeamRosterPlayer } from '../types';

interface BowlerPickerModalProps {
  currentOver: number;
  maxOvers?: number;
  teamName?: string;
  eligibleBowlers: TeamRosterPlayer[];
  usedBowlers: TeamRosterPlayer[];
  onSelectBowler: (bowlerId: number) => void;
  isLoading?: boolean;
}

export const BowlerPickerModal: React.FC<BowlerPickerModalProps> = ({
  currentOver,
  maxOvers = 5,
  teamName = 'Your Team',
  eligibleBowlers,
  usedBowlers,
  onSelectBowler,
  isLoading = false,
}) => {
  // Pre-select first eligible bowler by default
  const defaultBowlerId = eligibleBowlers.length > 0 ? eligibleBowlers[0].id : null;
  const [selectedBowlerId, setSelectedBowlerId] = useState<number | null>(defaultBowlerId);

  const usedBowlerIds = new Set(usedBowlers.map((b) => b.id));

  // Combine eligible + used to show full 11-player squad roster sorted by ID
  const combinedMap = new Map<number, TeamRosterPlayer>();
  usedBowlers.forEach((b) => combinedMap.set(b.id, b));
  eligibleBowlers.forEach((b) => combinedMap.set(b.id, b));
  const allSquadPlayers = Array.from(combinedMap.values()).sort((a, b) => a.id - b.id);

  const handleConfirm = () => {
    if (selectedBowlerId !== null && !isLoading && !usedBowlerIds.has(selectedBowlerId)) {
      onSelectBowler(selectedBowlerId);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-fade-in select-none">
      <div className="relative w-full max-w-lg bg-gradient-to-b from-[#0e223d] to-[#071322] border-2 border-amber-400/60 rounded-3xl p-5 sm:p-7 shadow-[0_0_40px_rgba(245,158,11,0.3)] text-white">
        {/* Header */}
        <div className="text-center pb-4 border-b border-white/10">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-400/40 text-amber-300 font-extrabold text-xs uppercase tracking-widest mb-2">
            OVER {currentOver} OF {maxOvers} • BOWLER SELECTION
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            SELECT NEXT BOWLER
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Choose who bowls Over {currentOver} for {teamName}. Each bowler is limited to 1 over per innings.
          </p>
        </div>

        {/* Bowler List */}
        <div className="mt-4 max-h-64 sm:max-h-72 overflow-y-auto pr-1 space-y-2 custom-scrollbar">
          {allSquadPlayers.map((player) => {
            const hasBowled = usedBowlerIds.has(player.id);
            const isSelected = selectedBowlerId === player.id;

            return (
              <div
                key={player.id}
                onClick={() => {
                  if (!hasBowled) {
                    setSelectedBowlerId(player.id);
                  }
                }}
                role="button"
                tabIndex={hasBowled ? -1 : 0}
                onKeyDown={(e) => {
                  if (!hasBowled && (e.key === 'Enter' || e.key === ' ')) {
                    setSelectedBowlerId(player.id);
                  }
                }}
                className={`flex items-center justify-between p-3 rounded-xl border transition-all ${
                  hasBowled
                    ? 'bg-slate-900/40 border-white/5 opacity-50 cursor-not-allowed text-slate-500'
                    : isSelected
                    ? 'bg-amber-500/20 border-amber-400 text-white shadow-md shadow-amber-500/20 cursor-pointer'
                    : 'bg-white/5 border-white/10 hover:border-white/30 text-slate-200 cursor-pointer hover:bg-white/10'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`w-7 h-7 rounded-lg flex items-center justify-center font-black text-xs ${
                      hasBowled
                        ? 'bg-slate-800 text-slate-500'
                        : isSelected
                        ? 'bg-amber-400 text-slate-950'
                        : 'bg-white/10 text-slate-300'
                    }`}
                  >
                    #{player.id}
                  </span>
                  <div>
                    <div className="font-bold text-sm tracking-wide">{player.name}</div>
                    <div className="text-[10px] text-slate-400">
                      {player.id >= 8 ? 'Specialist Bowler' : player.id >= 6 ? 'All-Rounder' : 'Part-Time Bowler'}
                    </div>
                  </div>
                </div>

                <div>
                  {hasBowled ? (
                    <span className="px-2.5 py-1 rounded-md bg-rose-500/20 border border-rose-500/30 text-[10px] font-black text-rose-300 uppercase tracking-wider">
                      QUOTA EXHAUSTED (1.0)
                    </span>
                  ) : isSelected ? (
                    <span className="px-3 py-1 rounded-md bg-amber-400 text-slate-950 font-black text-xs uppercase tracking-wider">
                      SELECTED ✓
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 rounded-md bg-white/10 text-slate-400 font-bold text-xs uppercase tracking-wider">
                      ELIGIBLE
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Action Button */}
        <div className="mt-5 pt-3 border-t border-white/10 flex items-center justify-between gap-3">
          <div className="text-xs text-slate-400">
            Bowler Quota: <span className="font-bold text-amber-300">{usedBowlers.length} / {maxOvers}</span> Used
          </div>

          <button
            onClick={handleConfirm}
            disabled={selectedBowlerId === null || isLoading || usedBowlerIds.has(selectedBowlerId)}
            className={`px-6 py-3 rounded-xl font-black text-xs sm:text-sm tracking-wider uppercase transition-all shadow-lg flex items-center gap-2 ${
              selectedBowlerId !== null && !isLoading && !usedBowlerIds.has(selectedBowlerId)
                ? 'bg-gradient-to-r from-amber-400 to-amber-500 hover:from-yellow-300 hover:to-amber-400 text-slate-950 shadow-amber-500/30 hover:shadow-amber-500/50 cursor-pointer transform hover:scale-[1.02]'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/10'
            }`}
          >
            {isLoading ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></span>
                CONFIRMING...
              </>
            ) : (
              <>CONFIRM BOWLER 🎯</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
