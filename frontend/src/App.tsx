import { useState } from 'react';
import { BowlerPickerModal } from './components/BowlerPickerModal';
import { FriendArena } from './components/FriendArena';
import { FriendLobbyModal } from './components/FriendLobbyModal';
import { Header } from './components/Header';
import { InningsBreakModal } from './components/InningsBreakModal';
import { IntroScreen } from './components/IntroScreen';
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
    tossActive,
    tossOutcome,
    bowlerSelectionPrompt,
    matchState,
    connectionStatus,
    turnCountdown,
    isMuted,
    toggleMute,
    selectedNumber,
    isWaiting,
    eventFeedback,
    milestoneFeedback,
    errorMessage,
    finishIntro,
    startVsComputer,
    goToLanding,
    selectTeam,
    chooseToss,
    finishToss,
    selectBowler,
    resetPreMatch,
    submitNumber,
    startNextInnings,
    resetGame,
    reconnect,
  } = useCricketGame();

  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [showFriendLobby, setShowFriendLobby] = useState<boolean>(false);
  const [friendSession, setFriendSession] = useState<{
    roomCode: string;
    token: string;
    participant: 'A' | 'B';
  } | null>(() => {
    try {
      const stored = sessionStorage.getItem('hc_friend_session');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const handleEnterFriendRoom = (roomCode: string, token: string, participant: 'A' | 'B') => {
    const session = { roomCode, token, participant };
    try {
      sessionStorage.setItem('hc_friend_session', JSON.stringify(session));
    } catch {}
    setFriendSession(session);
  };

  const handleExitFriendRoom = () => {
    try {
      sessionStorage.removeItem('hc_friend_session');
    } catch {}
    setFriendSession(null);
  };

  // If in active Friend Mode session, display FriendArena
  if (friendSession) {
    return (
      <FriendArena
        roomCode={friendSession.roomCode}
        playerToken={friendSession.token}
        participantSeat={friendSession.participant}
        onExit={handleExitFriendRoom}
      />
    );
  }

  // 1. Connection Error Screen
  if (connectionStatus === 'error' && !matchState && !preMatchState) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-950 text-white p-4 text-center">
        <div className="text-5xl mb-3">📡</div>
        <h2 className="text-2xl font-bold text-white mb-2">Connection Issue</h2>
        <p className="text-slate-400 text-sm max-w-xs mb-6">
          {errorMessage || 'Unable to connect to the game server. Please check your internet connection and try again.'}
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

  // 2. Intro Title Screen Sequence
  if (appStage === 'INTRO') {
    return <IntroScreen onFinish={finishIntro} />;
  }

  // 3. Landing Screen
  if (appStage === 'LANDING') {
    return (
      <>
        <LandingScreen
          onPlayVsComputer={startVsComputer}
          onPlayWithFriend={() => setShowFriendLobby(true)}
        />
        <FriendLobbyModal
          isOpen={showFriendLobby}
          onClose={() => setShowFriendLobby(false)}
          onEnterRoom={(roomCode, token, participant) => {
            setShowFriendLobby(false);
            handleEnterFriendRoom(roomCode, token, participant);
          }}
        />
      </>
    );
  }

  // 4. Pre-Match Stage Flows
  if (appStage === 'PRE_MATCH') {
    const stage = preMatchState?.stage || 'TEAM_SELECTION';

    if (tossActive || stage === 'TOSS_DECISION' || stage === 'TOSS_RESULT') {
      const uTeam = tossOutcome?.userTeam ?? preMatchState?.user_team ?? null;
      const oTeam = tossOutcome?.opponentTeam ?? preMatchState?.opponent_team ?? null;
      const tWinner = tossOutcome?.winner ?? preMatchState?.toss_winner ?? null;
      const tossKey = `toss_${uTeam?.id || 'u'}_${oTeam?.id || 'o'}_${tWinner || 'pending'}`;

      return (
        <TossScreen
          key={tossKey}
          userTeam={uTeam}
          opponentTeam={oTeam}
          tossWinner={tWinner}
          tossDecision={tossOutcome?.decision ?? preMatchState?.toss_decision ?? null}
          onChooseToss={chooseToss}
          onProceed={finishToss}
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

      {/* Reconnection Status Banner (non-destructive) */}
      {connectionStatus === 'reconnecting' && (
        <div
          data-testid="reconnection-banner"
          className="absolute top-2 z-50 px-4 py-1.5 rounded-full bg-amber-500/95 text-slate-950 font-black text-xs sm:text-sm shadow-xl flex items-center space-x-2 backdrop-blur-md animate-in slide-in-from-top duration-200 border border-amber-300"
        >
          <span className="w-2.5 h-2.5 rounded-full bg-slate-950 animate-ping inline-block" />
          <span>Connection lost — Reconnecting to match...</span>
        </div>
      )}

      {/* Top Header */}
      <Header
        matchState={matchState}
        onOpenSettings={() => setShowSettings(true)}
        isMuted={isMuted}
        onToggleMute={toggleMute}
      />

      {/* Main Pitch Arena (Prompts, pitch, 1-6 buttons, event celebrations, milestones) */}
      <PitchArena
        matchState={matchState}
        selectedNumber={selectedNumber}
        isWaiting={isWaiting}
        eventFeedback={eventFeedback}
        milestoneFeedback={milestoneFeedback}
        turnCountdown={turnCountdown}
        onSelectNumber={submitNumber}
      />

      {/* Bottom Compact Scoreboard */}
      <Scoreboard matchState={matchState} />

      {/* Innings Break Modal — guarded so 6th ball delivery result is visible first */}
      {matchState && !eventFeedback && (
        <InningsBreakModal
          matchState={matchState}
          onStartNextInnings={startNextInnings}
        />
      )}

      {/* Match Result Modal (Win, Loss, Tie) — guarded so winning ball delivery result is visible first */}
      {matchState && !eventFeedback && (
        <MatchResultModal
          matchState={matchState}
          onPlayAgain={resetGame}
        />
      )}

      {/* Over-by-Over Bowler Selection Modal Overlay — guarded so 6th ball delivery result is visible first */}
      {bowlerSelectionPrompt && !eventFeedback && (
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
        isMuted={isMuted}
        onToggleMute={toggleMute}
      />
    </div>
  );
}

