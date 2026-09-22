import React from 'react';
import { MatchState } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  matchState: MatchState | null;
  onClose: () => void;
  onResetMatch: () => void;
  isMuted?: boolean;
  onToggleMute?: () => void;
}

const formatMatchStatus = (status: string): string => {
  switch (status) {
    case 'INNINGS_1':
      return '1st Innings';
    case 'INNINGS_2':
      return '2nd Innings';
    case 'IN_PROGRESS':
      return 'In Progress';
    case 'INNINGS_BREAK':
      return 'Innings Break';
    case 'COMPLETED':
      return 'Match Completed';
    default:
      return status.replace(/_/g, ' ');
  }
};

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  matchState,
  onClose,
  onResetMatch,
  isMuted = false,
  onToggleMute,
}) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-700/80 rounded-3xl p-6 shadow-2xl text-white max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <h3 className="text-xl font-bold text-white flex items-center space-x-2">
            <span>⚙️</span>
            <span>Match Details & Rules</span>
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Current Match Summary (if active) */}
        {matchState && (
          <div className="bg-slate-800/60 rounded-2xl p-4 border border-slate-700/60 mb-4 text-xs sm:text-sm space-y-2">
            <div className="font-extrabold text-amber-400 uppercase tracking-wider text-[11px]">
              Active Match
            </div>
            <div className="flex justify-between items-center text-slate-300">
              <span>Teams:</span>
              <span className="font-bold text-white">
                {matchState.user_team.name} vs {matchState.opponent_team.name}
              </span>
            </div>
            <div className="flex justify-between items-center text-slate-300">
              <span>Current Status:</span>
              <span className="font-bold text-sky-400">
                {formatMatchStatus(matchState.status)}
              </span>
            </div>
            <div className="flex justify-between items-center text-slate-300">
              <span>Overs per Innings:</span>
              <span className="font-bold text-white">
                {matchState.max_overs} overs ({matchState.max_overs * 6} balls)
              </span>
            </div>
            {matchState.target && (
              <div className="flex justify-between items-center text-emerald-400 font-bold">
                <span>Target:</span>
                <span>{matchState.target} runs</span>
              </div>
            )}
          </div>
        )}

        {/* Sound & Audio Control Card */}
        {onToggleMute && (
          <div className="bg-slate-800/60 rounded-2xl p-4 border border-slate-700/60 mb-4 flex items-center justify-between">
            <div>
              <div className="font-bold text-white text-xs sm:text-sm flex items-center space-x-1.5">
                <span>{isMuted ? '🔇' : '🔊'}</span>
                <span>Game Audio & SFX</span>
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">
                Bat hits, crowd cheers, boundary & wicket sounds
              </div>
            </div>
            <button
              type="button"
              onClick={onToggleMute}
              data-testid="settings-audio-toggle"
              className={`px-3 py-1.5 rounded-xl font-bold text-xs transition-all active:scale-95 ${
                isMuted
                  ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  : 'bg-amber-400 text-slate-950 hover:bg-amber-300 font-extrabold shadow-md shadow-amber-500/20'
              }`}
            >
              {isMuted ? 'Sound: OFF' : 'Sound: ON'}
            </button>
          </div>
        )}

        {/* Hand Cricket Rules Card */}
        <div className="bg-slate-800/40 rounded-2xl p-4 border border-slate-700/40 mb-5 text-xs text-slate-300 space-y-2.5 leading-relaxed">
          <div className="font-bold text-white text-sm flex items-center space-x-1.5">
            <span>🏏</span>
            <span>How Hand Cricket Works</span>
          </div>
          <ul className="space-y-1.5 list-disc pl-4 text-slate-300">
            <li>
              <strong>Simultaneous Numbers</strong>: Both batsman and bowler choose an integer (<strong className="text-amber-400">1, 2, 3, 4, or 6</strong>).
            </li>
            <li>
              <strong>Scoring</strong>: If choices differ, the batsman scores the runs of their choice!
            </li>
            <li>
              <strong>Wicket</strong>: If both choices match, the batsman is <strong className="text-red-400">OUT!</strong>
            </li>
            <li>
              <strong>Turn Timer</strong>: You have <strong className="text-amber-400">10 seconds</strong> to pick your number before a random ball is chosen.
            </li>
            <li>
              <strong>Target Chase</strong>: In Innings 2, chasing team tries to exceed Innings 1 score to win.
            </li>
          </ul>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-2 pt-2 border-t border-slate-800">
          <button
            onClick={() => {
              onResetMatch();
              onClose();
            }}
            className="w-full py-2.5 px-4 rounded-xl font-bold text-sm text-red-300 bg-red-950/40 hover:bg-red-900/50 border border-red-800/50 active:scale-98 transition-all"
          >
            Exit Match
          </button>
          <button
            onClick={onClose}
            className="w-full py-2.5 px-4 rounded-xl font-bold text-sm text-slate-300 bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            Resume Game
          </button>
        </div>
      </div>
    </div>
  );
};
