import { useState } from 'react';
import { BowlerPickerModal } from './components/BowlerPickerModal';
import { Header } from './components/Header';
import { InningsBreakModal } from './components/InningsBreakModal';
import { LandingScreen } from './components/LandingScreen';
import { MatchResultModal } from './components/MatchResultModal';
import { PitchArena } from './components/PitchArena';
import { Scoreboard } from './components/Scoreboard';
import { SettingsModal } from './components/SettingsModal';
import { TeamSelectionScreen } from './components/TeamSelectionScreen';
import { TossScreen } from './components/TossScreen';
import { useCricketGame } from './hooks/useCricketGame';

export default function App() {
  const {
    appStage,
    preMatchState,
    bowlerSelectionPrompt,
    matchState,
    connectionStatus,
    selectedNumber,
    isWaiting,
    eventFeedback,
    milestoneFeedback,
    errorMessage,
    startVsComputer,
    goToLanding,
    selectTeam,
    chooseToss,
    selectBowler,
    resetPreMatch,
    submitNumber,
    startNextInnings,
    resetGame,
    reconnect,
  } = useCricketGame();

  const [showSettings, setShowSettings] = useState<boolean>(false);

  // 1. Connection Error Screen
  if (connectionStatus === 'error' && !matchState && !preMatchState) {
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

  // 2. Landing Screen
  if (appStage === 'LANDING') {
    return <LandingScreen onPlayVsComputer={startVsComputer} />;
  }

  // 3. Pre-Match Stage Flows
  if (appStage === 'PRE_MATCH') {
    const stage = preMatchState?.stage || 'TEAM_SELECTION';

    if (stage === 'TOSS_DECISION' || stage === 'TOSS_RESULT') {
      return (
        <TossScreen
          userTeam={preMatchState?.user_team ?? null}
          opponentTeam={preMatchState?.opponent_team ?? null}
          tossWinner={preMatchState?.toss_winner ?? null}
          tossDecision={preMatchState?.toss_decision ?? null}
          onChooseToss={chooseToss}
          isLoading={isWaiting}
        />
      );
    }

    if (stage === 'BOWLER_SELECTION') {
      return (
        <BowlerPickerModal
          currentOver={1}
          maxOvers={5}
          teamName={preMatchState?.user_team?.name || 'Your Team'}
          eligibleBowlers={preMatchState?.eligible_bowlers || []}
          usedBowlers={preMatchState?.used_bowlers || []}
          onSelectBowler={selectBowler}
          isLoading={isWaiting}
        />
      );
    }

    // Default to Team Selection
    return (
      <TeamSelectionScreen
        availableTeams={preMatchState?.available_teams || []}
        onSelectTeam={selectTeam}
        onBack={() => {
          resetPreMatch();
          goToLanding();
        }}
        isLoading={isWaiting}
      />
    );
  }

  // 4. In-Match Playable Arena (Slice 12 Approved Interface)
  return (
    <div className="relative w-full h-[100dvh] max-h-[100dvh] flex flex-col items-center justify-between overflow-hidden bg-[url('/stadium_bg.jpg')] bg-cover bg-center bg-no-repeat text-white select-none">
      {/* Soft atmospheric overlay for readability */}
      <div className="absolute inset-0 bg-gradient-to-b from-slate-950/30 via-transparent to-slate-950/50 pointer-events-none z-0" />

      {/* Top Header */}
      <Header matchState={matchState} onOpenSettings={() => setShowSettings(true)} />

      {/* Main Pitch Arena (Prompts, pitch, 1-6 buttons, event celebrations, milestones) */}
      <PitchArena
        matchState={matchState}
        selectedNumber={selectedNumber}
        isWaiting={isWaiting}
        eventFeedback={eventFeedback}
        milestoneFeedback={milestoneFeedback}
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

      {/* Over-by-Over Bowler Selection Modal Overlay */}
      {bowlerSelectionPrompt && (
        <BowlerPickerModal
          currentOver={bowlerSelectionPrompt.current_over}
          maxOvers={matchState?.max_overs || 5}
          teamName={matchState?.user_team?.name || 'Your Team'}
          eligibleBowlers={bowlerSelectionPrompt.eligible_bowlers}
          usedBowlers={bowlerSelectionPrompt.used_bowlers}
          onSelectBowler={selectBowler}
          isLoading={isWaiting}
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

