import React, { useState } from 'react';
import { useFriendCricketGame } from '../hooks/useFriendCricketGame';
import { BowlerPickerModal } from './BowlerPickerModal';
import { Header } from './Header';
import { InningsBreakModal } from './InningsBreakModal';
import { MatchResultModal } from './MatchResultModal';
import { PitchArena } from './PitchArena';
import { Scoreboard } from './Scoreboard';
import { SettingsModal } from './SettingsModal';
import { TeamSelectionScreen } from './TeamSelectionScreen';
import { TossScreen } from './TossScreen';

interface FriendArenaProps {
  roomCode: string;
  playerToken: string;
  participantSeat: 'A' | 'B';
  onExit: () => void;
}

export const FriendArena: React.FC<FriendArenaProps> = ({
  roomCode,
  playerToken,
  participantSeat,
  onExit,
}) => {
  const {
    connectionStatus,
    stage,
    participant,
    userTeam,
    opponentTeam,
    tossWinner,
    tossDecision,
    bowlerSelector,
    bowlerSelectionPrompt,
    matchState,
    selectedNumber,
    hasSubmitted,
    opponentSubmitted,
    turnCountdown,
    eventFeedback,
    milestoneFeedback,
    errorMessage,
    opponentDisconnected,
    opponentGraceSeconds,
    inningsBreakReady,
    rematchRequested,
    opponentRematchRequested,
    selectTeam,
    chooseToss,
    selectBowler,
    submitNumber,
    startNextInnings,
    requestRematch,
    leaveRoom,
  } = useFriendCricketGame({
    roomCode,
    playerToken,
    participantSeat,
    onLeave: onExit,
  });

  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [copiedCode, setCopiedCode] = useState<boolean>(false);

  const handleCopyRoomCode = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(roomCode);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  // 1. Connection Error / Disconnected
  if (connectionStatus === 'disconnected' || connectionStatus === 'error') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-950 text-white p-4 text-center">
        <div className="text-5xl mb-3">📡</div>
        <h2 className="text-2xl font-bold text-white mb-2">Connection Lost</h2>
        <p className="text-slate-400 text-sm max-w-xs mb-6">
          {errorMessage || 'Disconnected from Friend match.'}
        </p>
        <button
          onClick={onExit}
          className="py-3 px-6 rounded-2xl font-bold text-slate-950 bg-amber-400 hover:bg-amber-300 active:scale-95 shadow-lg shadow-amber-500/20 transition-all"
        >
          Return to Main Menu
        </button>
      </div>
    );
  }

  // 2. Waiting for Player B (Host waiting room)
  if (stage === 'WAITING_FOR_PLAYER') {
    return (
      <div className="relative min-h-screen w-full flex flex-col items-center justify-center p-6 bg-[url('/stadium_bg.jpg')] bg-cover bg-center text-white select-none">
        <div className="absolute inset-0 bg-gradient-to-b from-slate-950/80 via-black/60 to-slate-950/90" />
        <div className="relative z-10 w-full max-w-md bg-slate-900/90 border-2 border-amber-400/60 rounded-3xl p-6 sm:p-8 text-center shadow-2xl backdrop-blur-md">
          <span className="text-xs font-bold text-amber-400 uppercase tracking-widest">
            ROOM CODE
          </span>
          <div className="flex items-center justify-center gap-3 my-3">
            <div className="px-6 py-4 rounded-2xl bg-black/60 border-2 border-amber-400/80 font-mono text-4xl sm:text-5xl font-black tracking-widest text-amber-300">
              {roomCode}
            </div>
            <button
              onClick={handleCopyRoomCode}
              className="px-4 py-4 rounded-2xl bg-amber-400/20 hover:bg-amber-400/30 border border-amber-400/50 text-amber-300 font-bold text-xs flex flex-col items-center gap-1 transition-all active:scale-95 cursor-pointer"
              aria-label="Copy Room Code"
            >
              <span>{copiedCode ? '✓' : '📋'}</span>
              <span>{copiedCode ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
          <p className="text-slate-300 text-sm mt-2">
            Share this match code with your friend. The game will automatically start as soon as they join!
          </p>
          <div className="flex items-center justify-center gap-2 mt-6 text-xs text-amber-300 font-bold animate-pulse">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span>Waiting for Player 2 to connect...</span>
          </div>
          <button
            onClick={onExit}
            className="mt-6 text-xs font-bold text-slate-400 hover:text-white underline underline-offset-4 cursor-pointer"
          >
            Cancel & Exit Room
          </button>
        </div>
      </div>
    );
  }

  // 3. Team Selection Screen
  if (stage === 'TEAM_SELECTION') {
    if (userTeam) {
      return (
        <div className="relative min-h-screen w-full flex flex-col items-center justify-center p-6 bg-[url('/stadium_bg.jpg')] bg-cover bg-center text-white select-none">
          <div className="absolute inset-0 bg-gradient-to-b from-slate-950/80 via-black/60 to-slate-950/90" />
          <div className="relative z-10 w-full max-w-md bg-slate-900/90 border-2 border-amber-400/60 rounded-3xl p-8 text-center shadow-2xl backdrop-blur-md">
            <div className="text-5xl mb-3">🏏</div>
            <h3 className="text-2xl font-black text-amber-300 uppercase">Team Locked!</h3>
            <p className="text-white text-lg font-extrabold mt-1">{userTeam.name}</p>
            {opponentTeam ? (
              <div className="flex items-center justify-center gap-2 mt-6 text-xs text-emerald-400 font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>Opponent locked in {opponentTeam.name}! Setting up toss...</span>
              </div>
            ) : (
              <div className="flex items-center justify-center gap-2 mt-6 text-xs text-amber-300 font-bold animate-pulse">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                <span>Waiting for opponent to select team...</span>
              </div>
            )}
          </div>
        </div>
      );
    }

    return (
      <div className="relative">
        {opponentTeam && (
          <div className="fixed top-3 left-1/2 -translate-x-1/2 z-50 px-4 py-1.5 rounded-full bg-emerald-950/90 border border-emerald-500/50 text-emerald-300 text-xs font-bold shadow-lg backdrop-blur-md animate-pulse">
            Opponent has selected {opponentTeam.name}! Choose your team.
          </div>
        )}
        <TeamSelectionScreen
          availableTeams={[]}
          onSelectTeam={selectTeam}
          onBack={onExit}
          isLoading={false}
        />
      </div>
    );
  }

  // 4. Toss Screen
  if (stage === 'TOSS_DECISION') {
    const isWinner = tossWinner === participant;
    return (
      <TossScreen
        userTeam={userTeam}
        opponentTeam={opponentTeam}
        tossWinner={isWinner ? 'user' : 'computer'}
        tossDecision={tossDecision}
        onChooseToss={chooseToss}
        onProceed={() => {}}
        isLoading={false}
        isFriendMode={true}
      />
    );
  }

  // 5. Active Match Arena (IN_MATCH, BOWLER_SELECTION, INNINGS_BREAK, MATCH_COMPLETED)
  const isBowlerModalOpen = stage === 'BOWLER_SELECTION' && bowlerSelector === participant;
  const isBowlerWaitScreen = stage === 'BOWLER_SELECTION' && bowlerSelector !== participant;

  return (
    <div className="relative w-full h-[100dvh] max-h-[100dvh] flex flex-col items-center justify-between overflow-hidden bg-[url('/stadium_bg.jpg')] bg-cover bg-center bg-no-repeat text-white select-none">
      {/* Soft atmospheric overlay for readability (matching Computer Mode) */}
      <div className="absolute inset-0 bg-gradient-to-b from-slate-950/30 via-transparent to-slate-950/50 pointer-events-none z-0" />

      {/* Top Header (Direct flex child, identical geometry to Computer Mode) */}
      <Header
        matchState={matchState}
        onOpenSettings={() => setShowSettings(true)}
        isMuted={isMuted}
        onToggleMute={() => setIsMuted(!isMuted)}
        modeLabel="vs Friend"
      />

      {/* Room Badge & Role Floating Pill (Non-destructive overlay; does not shift arena geometry) */}
      <div className="absolute top-[48px] sm:top-[64px] left-1/2 -translate-x-1/2 z-20 pointer-events-none flex items-center justify-center">
        <div className="flex items-center gap-1.5 sm:gap-2 px-3 py-0.5 sm:px-4 sm:py-1 rounded-full bg-slate-950/80 border border-amber-400/30 backdrop-blur-md shadow-lg text-[10px] sm:text-[11px] font-extrabold uppercase tracking-wider">
          <span className="text-amber-400 font-mono">ROOM: {roomCode}</span>
          <span className="text-white/40">•</span>
          <span className="text-slate-200">
            {matchState?.user_is_batting ? '🏏 YOU ARE BATTING' : '⚾ YOU ARE BOWLING'}
          </span>
          {hasSubmitted && !opponentSubmitted && (
            <>
              <span className="text-white/40">•</span>
              <span className="text-amber-300 font-bold">Your Choice Locked</span>
            </>
          )}
          {!hasSubmitted && opponentSubmitted && (
            <>
              <span className="text-white/40">•</span>
              <span className="text-emerald-400 font-bold animate-pulse">Opponent Locked In!</span>
            </>
          )}
          {hasSubmitted && opponentSubmitted && (
            <>
              <span className="text-white/40">•</span>
              <span className="text-sky-300 font-bold">Resolving Delivery...</span>
            </>
          )}
        </div>
      </div>

      {/* Opponent Disconnected Grace Banner (Floating Overlay) */}
      {opponentDisconnected && (
        <div
          data-testid="opponent-disconnect-banner"
          className="absolute top-0 left-0 right-0 z-40 px-4 py-2 bg-rose-950/95 border-b border-rose-500/50 flex items-center justify-between text-xs font-bold text-rose-200 backdrop-blur-md animate-pulse shadow-lg"
        >
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span>Opponent disconnected. Waiting for reconnect...</span>
          </div>
          <span className="font-mono text-rose-300 font-extrabold">
            {Math.max(0, Math.ceil(opponentGraceSeconds))}s
          </span>
        </div>
      )}

      {/* Reconnecting to Server Banner (Floating Overlay) */}
      {connectionStatus === 'reconnecting' && (
        <div
          data-testid="reconnection-banner"
          className="absolute top-0 left-0 right-0 z-40 px-4 py-2 bg-amber-950/95 border-b border-amber-500/50 flex items-center justify-center gap-2 text-xs font-bold text-amber-200 backdrop-blur-md animate-pulse shadow-lg"
        >
          <span className="w-2 h-2 rounded-full bg-amber-400" />
          <span>Connection lost. Reconnecting to match...</span>
        </div>
      )}

      {/* Main Pitch Arena (Prompts, pitch, 1-6 buttons, event celebrations, milestones) */}
      <PitchArena
        matchState={matchState}
        selectedNumber={selectedNumber}
        isWaiting={hasSubmitted}
        waitingTitle={
          hasSubmitted
            ? opponentSubmitted
              ? 'RESOLVING DELIVERY'
              : 'YOUR CHOICE IS LOCKED'
            : 'WAITING FOR OPPONENT'
        }
        waitingSubtitle={
          hasSubmitted
            ? opponentSubmitted
              ? 'Both choices locked in...'
              : 'Waiting for opponent to submit...'
            : 'Resolving delivery...'
        }
        eventFeedback={eventFeedback}
        milestoneFeedback={milestoneFeedback}
        turnCountdown={turnCountdown}
        onSelectNumber={submitNumber}
      />

      {/* Bottom Compact Scoreboard (Matching Computer Mode layout) */}
      <Scoreboard matchState={matchState} opponentLabel="Opponent" />

      {/* Opponent Bowler Selection Waiting Toast */}
      {isBowlerWaitScreen && !eventFeedback && !milestoneFeedback && (
        <div className="absolute inset-0 z-40 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="p-6 rounded-2xl bg-slate-900 border border-amber-400/50 text-center text-white shadow-2xl">
            <div className="text-4xl mb-2">⚾</div>
            <h4 className="text-lg font-black text-amber-300">Bowler Selection</h4>
            <p className="text-xs text-slate-300 mt-1 animate-pulse">
              Waiting for opponent to select the next bowler...
            </p>
          </div>
        </div>
      )}

      {/* Bowler Picker Modal (Fielding Player) */}
      {isBowlerModalOpen && !eventFeedback && !milestoneFeedback && (
        <BowlerPickerModal
          currentOver={bowlerSelectionPrompt?.current_over || 1}
          maxOvers={matchState?.max_overs || 5}
          teamName={userTeam?.name || 'Your Team'}
          eligibleBowlers={bowlerSelectionPrompt?.eligible_bowlers || (userTeam as any)?.players || []}
          usedBowlers={bowlerSelectionPrompt?.used_bowlers || []}
          onSelectBowler={selectBowler}
          isLoading={false}
        />
      )}

      {/* Innings Break Modal */}
      {matchState && stage === 'INNINGS_BREAK' && !eventFeedback && !milestoneFeedback && (
        <InningsBreakModal
          matchState={matchState}
          onStartNextInnings={startNextInnings}
          isWaitingOpponent={inningsBreakReady}
        />
      )}

      {/* Match Completed Modal */}
      {matchState && stage === 'MATCH_COMPLETED' && !eventFeedback && !milestoneFeedback && (
        <MatchResultModal
          matchState={matchState}
          onPlayAgain={requestRematch}
          onExit={leaveRoom}
          isFriendMode={true}
          isRematchRequested={rematchRequested}
          opponentWantsRematch={opponentRematchRequested}
        />
      )}

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        matchState={matchState}
        onClose={() => setShowSettings(false)}
        isMuted={isMuted}
        onToggleMute={() => setIsMuted(!isMuted)}
        onResetMatch={onExit}
      />
    </div>
  );
};
