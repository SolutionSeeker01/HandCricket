import { useState } from 'react';
import { Header } from './components/Header';
import { InningsBreakModal } from './components/InningsBreakModal';
import { MatchResultModal } from './components/MatchResultModal';
import { PitchArena } from './components/PitchArena';
import { Scoreboard } from './components/Scoreboard';
import { SettingsModal } from './components/SettingsModal';
import { useCricketGame } from './hooks/useCricketGame';

export default function App() {
  const {
    matchState,
    connectionStatus,
    selectedNumber,
    isWaiting,
    eventFeedback,
    errorMessage,
    submitNumber,
    startNextInnings,
    resetGame,
    reconnect,
  } = useCricketGame();

  const [showSettings, setShowSettings] = useState<boolean>(false);

  // 1. Loading / Connecting Screen
  if (connectionStatus === 'connecting' && !matchState) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-950 text-white p-4">
        <div className="flex items-center space-x-2 mb-4">
          <span className="text-3xl sm:text-4xl font-black italic tracking-wider text-white">
            Hand
          </span>
          <span className="text-3xl sm:text-4xl font-black italic tracking-wider text-amber-400">
            Cricket
          </span>
        </div>
        <div className="flex items-center space-x-2 text-sky-400 text-sm font-semibold animate-pulse">
          <div className="w-3 h-3 rounded-full bg-sky-400 animate-ping" />
          <span>Entering stadium...</span>
        </div>
      </div>
    );
  }

  // 2. Connection Error Screen
  if (connectionStatus === 'error' && !matchState) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-950 text-white p-4 text-center">
        <div className="text-5xl mb-3">📡</div>
        <h2 className="text-2xl font-bold text-white mb-2">Connection Issue</h2>
        <p className="text-slate-400 text-sm max-w-xs mb-6">
          {errorMessage || 'Unable to connect to the Hand Cricket server. Please ensure the backend server is running.'}
        </p>
        <button
          onClick={reconnect}
          className="py-3 px-6 rounded-2xl font-bold text-slate-950 bg-amber-400 hover:bg-amber-300 active:scale-95 shadow-lg shadow-amber-500/20 transition-all"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="relative w-full h-[100dvh] max-h-[100dvh] flex flex-col items-center justify-between overflow-hidden bg-slate-950 text-white select-none">
      {/* Top Header */}
      <Header matchState={matchState} onOpenSettings={() => setShowSettings(true)} />

      {/* Main Pitch Arena (Prompts, pitch, 1-6 buttons, event celebrations) */}
      <PitchArena
        matchState={matchState}
        selectedNumber={selectedNumber}
        isWaiting={isWaiting}
        eventFeedback={eventFeedback}
        onSelectNumber={submitNumber}
      />

      {/* Bottom Compact Scoreboard */}
      <Scoreboard matchState={matchState} />

      {/* Innings Break Modal */}
      {matchState && (
        <InningsBreakModal
          matchState={matchState}
          onStartNextInnings={startNextInnings}
        />
      )}

      {/* Match Result Modal (Win, Loss, Tie) */}
      {matchState && (
        <MatchResultModal
          matchState={matchState}
          onPlayAgain={resetGame}
        />
      )}

      {/* Settings & Rules Modal */}
      <SettingsModal
        isOpen={showSettings}
        matchState={matchState}
        onClose={() => setShowSettings(false)}
        onResetMatch={resetGame}
      />
    </div>
  );
}
