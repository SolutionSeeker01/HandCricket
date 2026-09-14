import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { LandingScreen } from './components/LandingScreen';
import { FriendLobbyModal } from './components/FriendLobbyModal';
import { FriendArena } from './components/FriendArena';
import { TossScreen } from './components/TossScreen';
import { Scoreboard } from './components/Scoreboard';
import { MatchResultModal } from './components/MatchResultModal';
import { InningsBreakModal } from './components/InningsBreakModal';
import { PitchArena } from './components/PitchArena';
import { Header } from './components/Header';
import { MatchState } from './types';

// Mock MockWebSocket for useFriendCricketGame tests
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  readyState: number = WebSocket.OPEN;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 0);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) this.onclose();
  }

  triggerMessage(data: any) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }
}

describe('Friend Mode Frontend Tests (Sub-slice 15E)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  const dummyMatchState: MatchState = {
    innings: 1,
    batting_team: 'India',
    bowling_team: 'Australia',
    last_ball: null,
    user_team: { id: 'IND', name: 'India' },
    opponent_team: { id: 'AUS', name: 'Australia' },
    user_is_batting: true,
    user_batted_first: true,
    score: 42,
    wickets: 1,
    overs: '3.2',
    max_overs: 5,
    target: null,
    striker: { name: 'V. Kohli', runs: 28, balls: 14 },
    non_striker: { name: 'R. Sharma', runs: 12, balls: 6 },
    bowler: { name: 'P. Cummins', figures: '1/15', overs: '1.2', runs: 15, wickets: 1 },
    current_over_balls: [1, 4, 0, 1],
    innings_1_score: 42,
    innings_1_wickets: 1,
    innings_2_score: null,
    innings_2_wickets: null,
    status: 'INNINGS_1',
    winner: null,
    is_tie: false,
    result_description: null,
  };

  // 1. LANDING SCREEN ENTRY
  describe('1. Landing Screen Entry', () => {
    it('LandingScreen renders active LIVE MULTIPLAYER card and triggers onPlayWithFriend', () => {
      const handleComputer = vi.fn();
      const handleFriend = vi.fn();

      render(
        <LandingScreen
          onPlayVsComputer={handleComputer}
          onPlayWithFriend={handleFriend}
        />
      );

      expect(screen.getByText('LIVE MULTIPLAYER')).toBeDefined();
      expect(screen.getByText('Play with Friend')).toBeDefined();

      const friendCard = screen.getByText('Play with Friend').closest('[role="button"]');
      expect(friendCard).toBeDefined();

      if (friendCard) {
        fireEvent.click(friendCard);
        expect(handleFriend).toHaveBeenCalledTimes(1);
      }
    });
  });

  // 2. FRIEND LOBBY MODAL
  describe('2. Friend Lobby Modal', () => {
    it('creates a room and calls onEnterRoom with code, token, and seat A', async () => {
      const handleClose = vi.fn();
      const handleEnterRoom = vi.fn();

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          room_code: 'XYZ123',
          player_token: 'token-player-a',
          role: 'host',
        }),
      });
      vi.stubGlobal('fetch', fetchMock);

      render(
        <FriendLobbyModal
          isOpen={true}
          onClose={handleClose}
          onEnterRoom={handleEnterRoom}
        />
      );

      const createBtn = screen.getByRole('button', { name: /create match room/i });
      fireEvent.click(createBtn);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith('/api/rooms', { method: 'POST' });
        expect(handleEnterRoom).toHaveBeenCalledWith('XYZ123', 'token-player-a', 'A');
      });
    });

    it('shows error message if room creation fails', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Failed' }),
      });
      vi.stubGlobal('fetch', fetchMock);

      render(
        <FriendLobbyModal
          isOpen={true}
          onClose={vi.fn()}
          onEnterRoom={vi.fn()}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /create match room/i }));

      await waitFor(() => {
        expect(screen.getByText(/Failed to create room/i)).toBeDefined();
      });
    });

    it('joins a room, handles lowercase input conversion, and returns seat B', async () => {
      const handleEnterRoom = vi.fn();
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          room_code: 'CRIC99',
          player_token: 'token-player-b',
          role: 'guest',
        }),
      });
      vi.stubGlobal('fetch', fetchMock);

      render(
        <FriendLobbyModal
          isOpen={true}
          onClose={vi.fn()}
          onEnterRoom={handleEnterRoom}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /join room/i }));

      const input = screen.getByPlaceholderText('e.g. CRIC88');
      fireEvent.change(input, { target: { value: 'cric99' } });

      fireEvent.click(screen.getByRole('button', { name: /join match/i }));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith('/api/rooms/CRIC99/join', { method: 'POST' });
        expect(handleEnterRoom).toHaveBeenCalledWith('CRIC99', 'token-player-b', 'B');
      });
    });

    it('displays error message when room is full or not found', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({
          detail: { code: 'room_full', message: 'Room is full' },
        }),
      });
      vi.stubGlobal('fetch', fetchMock);

      render(
        <FriendLobbyModal
          isOpen={true}
          onClose={vi.fn()}
          onEnterRoom={vi.fn()}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /join room/i }));
      const input = screen.getByPlaceholderText('e.g. CRIC88');
      fireEvent.change(input, { target: { value: 'FULL99' } });
      fireEvent.click(screen.getByRole('button', { name: /join match/i }));

      await waitFor(() => {
        expect(screen.getByText('This room is already full.')).toBeDefined();
      });
    });
  });

  // 3. WAITING LOBBY (HOST WAITING ROOM)
  describe('3. Waiting Lobby UX', () => {
    it('renders room code, copy button, and waiting status for Player 2', () => {
      const handleExit = vi.fn();

      render(
        <FriendArena
          roomCode="CRIC88"
          playerToken="tokA"
          participantSeat="A"
          onExit={handleExit}
        />
      );

      // Verify room code is prominently shown
      expect(screen.getByText('CRIC88')).toBeDefined();
      expect(screen.getByText(/Waiting for Player 2 to connect/i)).toBeDefined();

      // Test copy room code button
      const copyBtn = screen.getByRole('button', { name: /copy room code/i });
      expect(copyBtn).toBeDefined();
      fireEvent.click(copyBtn);
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('CRIC88');

      // Test cancel button
      const exitBtn = screen.getByRole('button', { name: /cancel & exit room/i });
      fireEvent.click(exitBtn);
      expect(handleExit).toHaveBeenCalledTimes(1);
    });
  });

  // 4. TEAM SELECTION SYNCHRONIZATION
  describe('4. Team Selection UX', () => {
    it('shows Team Locked and opponent status when user has chosen a team', async () => {
      render(
        <FriendArena
          roomCode="TEAM99"
          playerToken="tokA"
          participantSeat="A"
          onExit={vi.fn()}
        />
      );

      const currentWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      await act(async () => {
        currentWs.triggerMessage({
          type: 'sync_state',
          participant: 'A',
          stage: 'TEAM_SELECTION',
          match_state: {
            user_team: { id: 'IND', name: 'India' },
          },
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Team Locked!')).toBeDefined();
        expect(screen.getByText('India')).toBeDefined();
        expect(screen.getByText(/Waiting for opponent to select team/i)).toBeDefined();
      });
    });

    it('shows opponent locked notification when opponent chooses first', async () => {
      render(
        <FriendArena
          roomCode="TEAM99"
          playerToken="tokA"
          participantSeat="A"
          onExit={vi.fn()}
        />
      );

      const currentWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      await act(async () => {
        currentWs.triggerMessage({
          type: 'sync_state',
          participant: 'A',
          stage: 'TEAM_SELECTION',
          match_state: {
            opponent_team: { id: 'AUS', name: 'Australia' },
          },
        });
      });

      await waitFor(() => {
        expect(screen.getByText(/Opponent has selected Australia/i)).toBeDefined();
      });
    });
  });

  // 5. TOSS EXPERIENCE (PLAYER RELATIVE)
  describe('5. Toss Experience', () => {
    it('renders player-relative labels "YOU" and "OPPONENT" in Friend Mode', () => {
      render(
        <TossScreen
          userTeam={{ id: 'IND', name: 'India' }}
          opponentTeam={{ id: 'AUS', name: 'Australia' }}
          tossWinner={null}
          tossDecision={null}
          onChooseToss={vi.fn()}
          isFriendMode={true}
        />
      );

      expect(screen.getByText('YOU')).toBeDefined();
      expect(screen.getByText('OPPONENT')).toBeDefined();
      expect(screen.queryByText('COMPUTER')).toBeNull();
    });

    it('renders "YOU WON THE TOSS!" with BAT FIRST / BOWL FIRST options for winner', async () => {
      const chooseToss = vi.fn();
      render(
        <TossScreen
          userTeam={{ id: 'IND', name: 'India' }}
          opponentTeam={{ id: 'AUS', name: 'Australia' }}
          tossWinner="user"
          tossDecision={null}
          onChooseToss={chooseToss}
          isFriendMode={true}
        />
      );

      // Wait for coin animation settle
      await waitFor(() => {
        expect(screen.getByText('YOU WON THE TOSS!')).toBeDefined();
      }, { timeout: 3000 });

      const batBtn = screen.getByRole('button', { name: /bat first/i });
      const bowlBtn = screen.getByRole('button', { name: /bowl first/i });

      expect(batBtn).toBeDefined();
      expect(bowlBtn).toBeDefined();

      fireEvent.click(batBtn);
      expect(chooseToss).toHaveBeenCalledWith('BAT');
    });

    it('renders "Waiting for opponent\'s decision..." when opponent won and tossDecision is null', async () => {
      render(
        <TossScreen
          userTeam={{ id: 'IND', name: 'India' }}
          opponentTeam={{ id: 'AUS', name: 'Australia' }}
          tossWinner="computer"
          tossDecision={null}
          onChooseToss={vi.fn()}
          isFriendMode={true}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('OPPONENT WON THE TOSS')).toBeDefined();
        expect(screen.getByText("Waiting for opponent's decision...")).toBeDefined();
        expect(screen.getByText('Opponent is choosing to bat or bowl')).toBeDefined();
      }, { timeout: 3000 });
    });
  });

  // 6. BOWLER SELECTION & WAITING SCREEN
  describe('6. Bowler Selection UX', () => {
    it('shows waiting toast for batting player during bowler selection', async () => {
      render(
        <FriendArena
          roomCode="BOWL01"
          playerToken="tokA"
          participantSeat="A"
          onExit={vi.fn()}
        />
      );

      const currentWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      await act(async () => {
        currentWs.triggerMessage({
          type: 'sync_state',
          participant: 'A',
          stage: 'BOWLER_SELECTION',
          bowler_selection_prompt: {
            bowler_selector: 'B', // Opponent is choosing
            current_over: 1,
            eligible_bowlers: [1, 2, 3],
            used_bowlers: [],
          },
        });
      });

      await waitFor(() => {
        expect(screen.getByText(/Waiting for opponent to select the next bowler/i)).toBeDefined();
      });
    });
  });

  // 7. FRIEND ARENA PRESENTATION & KEYPAD LOCK
  describe('7. Friend Arena Presentation', () => {
    it('displays room code, batting role, and Scoreboard with "Opponent"', async () => {
      render(
        <FriendArena
          roomCode="GAME77"
          playerToken="tokA"
          participantSeat="A"
          onExit={vi.fn()}
        />
      );

      const currentWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      await act(async () => {
        currentWs.triggerMessage({
          type: 'sync_state',
          participant: 'A',
          stage: 'IN_MATCH',
          match_state: dummyMatchState,
        });
      });

      await waitFor(() => {
        expect(screen.getByText(/ROOM: GAME77/i)).toBeDefined();
        expect(screen.getByText(/YOU ARE BATTING/i)).toBeDefined();
        expect(screen.getByText('Opponent')).toBeDefined();
      });
    });

    it('Scoreboard renders "Opponent" label when opponentLabel="Opponent"', () => {
      render(
        <Scoreboard
          matchState={dummyMatchState}
          opponentLabel="Opponent"
        />
      );

      expect(screen.getByText('Opponent')).toBeDefined();
      expect(screen.queryByText('Comp')).toBeNull();
    });

    it('Keypad locks choice and shows "YOUR CHOICE IS LOCKED" after submitting', () => {
      const selectNum = vi.fn();
      render(
        <PitchArena
          matchState={dummyMatchState}
          selectedNumber={4}
          isWaiting={true}
          waitingTitle="YOUR CHOICE IS LOCKED"
          waitingSubtitle="Waiting for opponent to submit..."
          eventFeedback={null}
          onSelectNumber={selectNum}
        />
      );

      expect(screen.getByText('YOUR CHOICE IS LOCKED')).toBeDefined();
      expect(screen.getByText('Waiting for opponent to submit...')).toBeDefined();

      // Keypad buttons should be disabled while waiting
      const btn4 = screen.getByLabelText('Select 4');
      expect(btn4.getAttribute('disabled')).not.toBeNull();
    });
  });

  // 8. BALL RESULT & TIMEOUT FEEDBACK
  describe('8. Ball Result & Timeout Feedback', () => {
    it('PitchArena displays ball result and auto-picked timeout badge', () => {
      render(
        <PitchArena
          matchState={dummyMatchState}
          selectedNumber={null}
          isWaiting={false}
          eventFeedback={{
            type: 'FOUR',
            runs: 4,
            title: 'FOUR!',
            batsmanChoice: 4,
            userChoice: 4,
            computerChoice: 2,
            userTimedOut: true,
          }}
          onSelectNumber={vi.fn()}
        />
      );

      expect(screen.getByTestId('onfield-ball-result')).toBeDefined();
      expect(screen.getByText('FOUR!')).toBeDefined();
      expect(screen.getByTestId('timeout-auto-picked-badge')).toBeDefined();
      expect(screen.getByText('TIMEOUT — AUTO-PICKED')).toBeDefined();
    });
  });

  // 9. MATCH RESULT MODAL (PLAYER RELATIVE)
  describe('9. Match Result Modal', () => {
    it('renders "YOU WON!" with "Return to Main Menu" when user won in Friend Mode', () => {
      const onPlayAgain = vi.fn();
      const winState: MatchState = {
        ...dummyMatchState,
        status: 'COMPLETED',
        winner: 'India',
        is_tie: false,
        result_description: 'India won by 15 runs',
      };

      render(
        <MatchResultModal
          matchState={winState}
          onPlayAgain={onPlayAgain}
          isFriendMode={true}
        />
      );

      expect(screen.getByText('YOU WON!')).toBeDefined();
      expect(screen.getByText('India won by 15 runs')).toBeDefined();

      const returnBtn = screen.getByRole('button', { name: /return to main menu/i });
      expect(returnBtn).toBeDefined();
      fireEvent.click(returnBtn);
      expect(onPlayAgain).toHaveBeenCalledTimes(1);
    });

    it('renders "YOU LOST!" when opponent won in Friend Mode', () => {
      const lossState: MatchState = {
        ...dummyMatchState,
        status: 'COMPLETED',
        winner: 'Australia',
        is_tie: false,
        result_description: 'Australia won by 4 wickets',
      };

      render(
        <MatchResultModal
          matchState={lossState}
          onPlayAgain={vi.fn()}
          isFriendMode={true}
        />
      );

      expect(screen.getByText('YOU LOST!')).toBeDefined();
    });

    it('renders "MATCH TIED!" when match is a tie in Friend Mode', () => {
      const tieState: MatchState = {
        ...dummyMatchState,
        status: 'COMPLETED',
        winner: null,
        is_tie: true,
        result_description: 'Scores level! Match tied.',
      };

      render(
        <MatchResultModal
          matchState={tieState}
          onPlayAgain={vi.fn()}
          isFriendMode={true}
        />
      );

      expect(screen.getByText('MATCH TIED!')).toBeDefined();
    });
  });

  // 10. RECONNECTION & DISCONNECT BANNERS
  describe('10. Reconnection & Disconnect Banners', () => {
    it('renders opponent disconnected grace banner with countdown timer', async () => {
      render(
        <FriendArena
          roomCode="CONN99"
          playerToken="tokA"
          participantSeat="A"
          onExit={vi.fn()}
        />
      );

      const currentWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      await act(async () => {
        currentWs.triggerMessage({
          type: 'sync_state',
          participant: 'A',
          stage: 'IN_MATCH',
          match_state: dummyMatchState,
        });
        currentWs.triggerMessage({
          type: 'player_disconnected',
          participant: 'B',
          grace_seconds: 45,
        });
      });

      await waitFor(() => {
        expect(screen.getByText(/Opponent disconnected. Waiting for reconnect.../i)).toBeDefined();
        expect(screen.getByText('45s')).toBeDefined();
      });
    });
  });

  // 11. MILESTONE CELEBRATIONS & WICKET SUBTITLE
  describe('11. Milestones & Wicket Subtitle Parity', () => {
    it('renders dismissed batsman name on wicket delivery', () => {
      const wicketFeedback = {
        type: 'WICKET' as const,
        runs: 0,
        title: 'WICKET!',
        subtitle: 'Rohit Sharma is out!',
      };

      render(
        <PitchArena
          matchState={dummyMatchState}
          selectedNumber={null}
          isWaiting={false}
          eventFeedback={wicketFeedback}
          onSelectNumber={vi.fn()}
        />
      );

      expect(screen.getByText('WICKET!')).toBeDefined();
      expect(screen.getByText('Rohit Sharma is out!')).toBeDefined();
    });

    it('renders 50 milestone celebration banner with batsman name', () => {
      const fiftyMilestone = {
        batsmanName: 'Virat Kohli',
        milestone: 50 as const,
        label: 'FIFTY!' as const,
      };

      render(
        <PitchArena
          matchState={dummyMatchState}
          selectedNumber={null}
          isWaiting={false}
          eventFeedback={null}
          milestoneFeedback={fiftyMilestone}
          onSelectNumber={vi.fn()}
        />
      );

      expect(screen.getByTestId('batsman-milestone-celebration')).toBeDefined();
      expect(screen.getByText('Virat Kohli')).toBeDefined();
      expect(screen.getByText('50')).toBeDefined();
      expect(screen.getByText('FIFTY!')).toBeDefined();
    });
  });

  // 12. TWO-PLAYER INNINGS BREAK WAITING
  describe('12. Two-Player Innings Break Waiting', () => {
    it('renders disabled "Waiting for Opponent..." when user acknowledged break', () => {
      const breakState: MatchState = {
        ...dummyMatchState,
        status: 'INNINGS_BREAK',
        innings_1_score: 45,
        innings_1_wickets: 3,
        target: 46,
      };

      render(
        <InningsBreakModal
          matchState={breakState}
          onStartNextInnings={vi.fn()}
          isWaitingOpponent={true}
        />
      );

      const btn = screen.getByRole('button', { name: /waiting for opponent/i });
      expect(btn).toBeDefined();
      expect((btn as HTMLButtonElement).disabled).toBe(true);
    });
  });

  // 13. REMATCH LIFECYCLE & PROMPTS
  describe('13. Rematch Lifecycle UI', () => {
    it('renders Play Again and handles mutual rematch states', () => {
      const onPlayAgain = vi.fn();
      const onExit = vi.fn();
      const winState: MatchState = {
        ...dummyMatchState,
        status: 'COMPLETED',
        winner: 'India',
        is_tie: false,
        result_description: 'India won by 10 runs',
      };

      const { rerender } = render(
        <MatchResultModal
          matchState={winState}
          onPlayAgain={onPlayAgain}
          onExit={onExit}
          isFriendMode={true}
          isRematchRequested={false}
          opponentWantsRematch={true}
        />
      );

      expect(screen.getByTestId('opponent-rematch-badge')).toBeDefined();
      expect(screen.getByText(/opponent wants a rematch!/i)).toBeDefined();

      const playAgainBtn = screen.getByRole('button', { name: /play again/i });
      fireEvent.click(playAgainBtn);
      expect(onPlayAgain).toHaveBeenCalledTimes(1);

      // Re-render in waiting state
      rerender(
        <MatchResultModal
          matchState={winState}
          onPlayAgain={onPlayAgain}
          onExit={onExit}
          isFriendMode={true}
          isRematchRequested={true}
          opponentWantsRematch={true}
        />
      );

      const waitingBtn = screen.getByRole('button', { name: /waiting for opponent/i });
      expect((waitingBtn as HTMLButtonElement).disabled).toBe(true);
    });
  });

  // 14. HEADER CLEANUP PARITY IN FRIEND MODE
  describe('14. Header Cleanup Parity in Friend Mode', () => {
    it('renders no Over, no Score, and no Target in Friend Mode Innings 1', () => {
      const inn1State: MatchState = {
        ...dummyMatchState,
        status: 'INNINGS_1',
        innings: 1,
        target: null,
      };

      render(
        <Header
          matchState={inn1State}
          onOpenSettings={vi.fn()}
          modeLabel="vs Friend"
        />
      );

      expect(screen.getByText('Hand')).toBeDefined();
      expect(screen.getByText('Cricket')).toBeDefined();
      expect(screen.getByText('vs Friend')).toBeDefined();
      expect(screen.queryByText('Over')).toBeNull();
      expect(screen.queryByText('Score')).toBeNull();
      expect(screen.queryByText('Target')).toBeNull();
    });

    it('renders no Over, no Score, but preserves Target in Friend Mode Innings 2', () => {
      const inn2State: MatchState = {
        ...dummyMatchState,
        status: 'INNINGS_2',
        innings: 2,
        target: 78,
      };

      render(
        <Header
          matchState={inn2State}
          onOpenSettings={vi.fn()}
          modeLabel="vs Friend"
        />
      );

      expect(screen.getByText('vs Friend')).toBeDefined();
      expect(screen.queryByText('Over')).toBeNull();
      expect(screen.queryByText('Score')).toBeNull();
      expect(screen.getByText('Target')).toBeDefined();
      expect(screen.getByText('78')).toBeDefined();
    });
  });

  describe('Hardening Regression Tests (Sub-slice 15F Parity & Fixes)', () => {
    it('displays OVER 5: in Scoreboard when overs is 4.1 (during over 5)', () => {
      const stateOver5: MatchState = {
        ...dummyMatchState,
        overs: '4.1',
        max_overs: 5,
        current_over_balls: [4],
      };

      render(<Scoreboard matchState={stateOver5} />);
      expect(screen.getByText('OVER 5:')).toBeDefined();
      expect(screen.queryByText('OVER 4:')).toBeNull();
      expect(screen.queryByText('This Over:')).toBeNull();
    });

    it('displays OVER 1: in Scoreboard when overs is 0.0 (first over)', () => {
      const stateOver1: MatchState = {
        ...dummyMatchState,
        overs: '0.0',
        max_overs: 5,
        current_over_balls: [],
      };

      render(<Scoreboard matchState={stateOver1} />);
      expect(screen.getByText('OVER 1:')).toBeDefined();
    });

    it('renders Return to Main Menu button in Computer Mode MatchResultModal and calls onExit', () => {
      const handleExit = vi.fn();
      const completedState: MatchState = {
        ...dummyMatchState,
        status: 'COMPLETED',
        winner: 'India',
        result_description: 'India won by 10 runs',
      };

      render(
        <MatchResultModal
          matchState={completedState}
          onPlayAgain={vi.fn()}
          onExit={handleExit}
          isFriendMode={false}
        />
      );

      const exitBtn = screen.getByText('Return to Main Menu');
      expect(exitBtn).toBeDefined();
      fireEvent.click(exitBtn);
      expect(handleExit).toHaveBeenCalledTimes(1);
    });

    it('renders YOU WON! in Friend Mode MatchResultModal when winner matches user_team', () => {
      const winState: MatchState = {
        ...dummyMatchState,
        status: 'COMPLETED',
        winner: 'India',
        user_team: { id: 'IND', name: 'India' },
        opponent_team: { id: 'AUS', name: 'Australia' },
        result_description: 'India won by 10 runs',
      };

      render(
        <MatchResultModal
          matchState={winState}
          onPlayAgain={vi.fn()}
          isFriendMode={true}
        />
      );

      expect(screen.getByText('YOU WON!')).toBeDefined();
    });

    it('renders YOU LOST! in Friend Mode MatchResultModal when winner matches opponent_team', () => {
      const lossState: MatchState = {
        ...dummyMatchState,
        status: 'COMPLETED',
        winner: 'Australia',
        user_team: { id: 'IND', name: 'India' },
        opponent_team: { id: 'AUS', name: 'Australia' },
        result_description: 'Australia won by 4 wickets',
      };

      render(
        <MatchResultModal
          matchState={lossState}
          onPlayAgain={vi.fn()}
          isFriendMode={true}
        />
      );

      expect(screen.getByText('YOU LOST!')).toBeDefined();
    });

    it('disambiguates same-team matchup in MatchResultModal using user_won', () => {
      const sameTeamWinState: MatchState = {
        ...dummyMatchState,
        status: 'COMPLETED',
        winner: 'India',
        user_won: true,
        user_team: { id: 'IND', name: 'India' },
        opponent_team: { id: 'IND', name: 'India' },
        result_description: 'India won by 15 runs',
      };

      const { rerender } = render(
        <MatchResultModal
          matchState={sameTeamWinState}
          onPlayAgain={vi.fn()}
          isFriendMode={true}
        />
      );

      expect(screen.getByText('YOU WON!')).toBeDefined();

      const sameTeamLossState: MatchState = {
        ...sameTeamWinState,
        user_won: false,
      };

      rerender(
        <MatchResultModal
          matchState={sameTeamLossState}
          onPlayAgain={vi.fn()}
          isFriendMode={true}
        />
      );

      expect(screen.getByText('YOU LOST!')).toBeDefined();
    });

    it('renders Match Abandoned screen when room is abandoned', async () => {
      const handleExit = vi.fn();
      render(
        <FriendArena
          roomCode="ABAN99"
          playerToken="tokA"
          participantSeat="A"
          onExit={handleExit}
        />
      );

      const currentWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      await act(async () => {
        currentWs.triggerMessage({
          type: 'room_abandoned',
          room_code: 'ABAN99',
          stage: 'ABANDONED',
          reason: 'Player B disconnected and did not return.',
        });
      });

      expect(screen.getByText('Match Abandoned')).toBeDefined();
      expect(screen.getByText('Player B disconnected and did not return.')).toBeDefined();

      const exitBtn = screen.getByText('Return to Main Menu');
      fireEvent.click(exitBtn);
      expect(handleExit).toHaveBeenCalledTimes(1);
    });

    it('reconstructs userTeam and opponentTeam on sync_state during TOSS_DECISION', async () => {
      render(
        <FriendArena
          roomCode="TOSS99"
          playerToken="tokA"
          participantSeat="A"
          onExit={vi.fn()}
        />
      );

      const currentWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      await act(async () => {
        currentWs.triggerMessage({
          type: 'sync_state',
          participant: 'A',
          stage: 'TOSS_DECISION',
          team_a: 'IND',
          team_b: 'AUS',
          team_a_name: 'India',
          team_b_name: 'Australia',
          toss_winner: 'A',
          match_state: {},
        });
      });

      // TossScreen should be visible with reconstructed India vs Australia
      expect(screen.getAllByText(/TOSS/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('INDIA')).toBeDefined();
      expect(screen.getByText('AUSTRALIA')).toBeDefined();
    });
  });
});
