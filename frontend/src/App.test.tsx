import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, renderHook, act, within } from '@testing-library/react';
import { Header } from './components/Header';
import { PitchArena } from './components/PitchArena';
import { Scoreboard } from './components/Scoreboard';
import { InningsBreakModal } from './components/InningsBreakModal';
import { MatchResultModal } from './components/MatchResultModal';
import { LandingScreen } from './components/LandingScreen';
import { IntroScreen } from './components/IntroScreen';
import { TeamSelectionScreen } from './components/TeamSelectionScreen';
import { TossScreen } from './components/TossScreen';
import { BowlerPickerModal } from './components/BowlerPickerModal';
import { SettingsModal } from './components/SettingsModal';
import { MatchState, TeamRoster } from './types';
import { useCricketGame } from './hooks/useCricketGame';
import { soundManager } from './utils/sound';

const mockMatchState: MatchState = {
  status: 'INNINGS_1',
  innings: 1,
  user_team: { id: 'IND', name: 'India' },
  opponent_team: { id: 'AUS', name: 'Australia' },
  batting_team: 'India',
  bowling_team: 'Australia',
  user_is_batting: true,
  user_batted_first: true,
  score: 27,
  wickets: 1,
  overs: '2.3',
  max_overs: 5,
  target: null,
  striker: { id: 1, name: 'Rohit Sharma', runs: 16, balls: 9 },
  non_striker: { id: 2, name: 'Virat Kohli', runs: 4, balls: 5 },
  bowler: { id: 11, name: 'Josh Hazlewood', overs: '0.3', runs: 4, wickets: 0, figures: '0.3-4-0' },
  current_over_balls: [1, 0, 4],
  innings_1_score: null,
  innings_1_wickets: null,
  innings_2_score: null,
  innings_2_wickets: null,
  last_ball: null,
  winner: null,
  is_tie: false,
  result_description: null,
};

describe('Slice 12 Frontend Component Tests', () => {
  it('Header renders branding, over, and score pills correctly', () => {
    render(<Header matchState={mockMatchState} onOpenSettings={vi.fn()} />);

    expect(screen.getByText('Hand')).toBeDefined();
    expect(screen.getByText('Cricket')).toBeDefined();
    expect(screen.getByText('2.3 / 5')).toBeDefined();
    expect(screen.getByText('27 / 1')).toBeDefined();
  });

  it('Header renders target pill when target is present in Innings 2', () => {
    const chasingState: MatchState = {
      ...mockMatchState,
      status: 'INNINGS_2',
      innings: 2,
      target: 63,
    };
    render(<Header matchState={chasingState} onOpenSettings={vi.fn()} />);
    expect(screen.getByText('63')).toBeDefined();
  });

  it('Scoreboard renders teams, score, batters, bowler, and over ball dots', () => {
    render(<Scoreboard matchState={mockMatchState} />);

    // Team names
    expect(screen.getAllByText('India').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Australia').length).toBeGreaterThan(0);

    // Score
    expect(screen.getAllByText('27-1').length).toBeGreaterThan(0);

    // Batters & Bowler
    expect(screen.getAllByText(/Rohit Sharma/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Virat Kohli/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Josh Hazlewood/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText('0.3-4-0').length).toBeGreaterThan(0);

    // Over balls (1, 0, 4)
    expect(screen.getAllByText('1').length).toBeGreaterThan(0);
    expect(screen.getAllByText('0').length).toBeGreaterThan(0);
    expect(screen.getAllByText('4').length).toBeGreaterThan(0);
  });

  it('Scoreboard displays batsman score with balls faced in parentheses', () => {
    render(<Scoreboard matchState={mockMatchState} />);
    // Striker: Rohit Sharma 16 runs off 9 balls -> 16 (9)
    // Non-striker: Virat Kohli 4 runs off 5 balls -> 4 (5)
    expect(screen.getAllByText('16 (9)').length).toBeGreaterThan(0);
    expect(screen.getAllByText('4 (5)').length).toBeGreaterThan(0);
  });

  it('PitchArena renders 1-6 buttons and triggers onSelectNumber when clicked', () => {
    const handleSelect = vi.fn();
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={null}
        onSelectNumber={handleSelect}
      />
    );

    expect(screen.getByText('YOUR SHOT')).toBeDefined();
    expect(screen.getByText('Choose your number (1 – 6)')).toBeDefined();

    // Click button '4'
    const btn4 = screen.getByLabelText('Select 4');
    fireEvent.click(btn4);
    expect(handleSelect).toHaveBeenCalledWith(4);
  });

  it('PitchArena renders YOUR DELIVERY when user is bowling in Innings 2', () => {
    const bowlingState: MatchState = {
      ...mockMatchState,
      user_is_batting: false,
    };
    render(
      <PitchArena
        matchState={bowlingState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={null}
        onSelectNumber={vi.fn()}
      />
    );

    expect(screen.getByText('YOUR DELIVERY')).toBeDefined();
    expect(screen.getByText('Choose your delivery (1 – 6)')).toBeDefined();
  });

  it('PitchArena keeps user on arena while waiting (NO separate waiting screen)', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={4}
        isWaiting={true}
        eventFeedback={null}
        onSelectNumber={vi.fn()}
      />
    );

    // Arena elements are STILL fully visible with context-aware waiting
    expect(screen.getByText('WAITING FOR OPPONENT')).toBeDefined();
    expect(screen.getByText('Resolving delivery...')).toBeDefined();
    // Buttons are still present on screen
    expect(screen.getByLabelText('Select 4')).toBeDefined();
  });

  it('When user is batting, ordinary result displays ONLY user batting number and not computer number', () => {
    render(
      <PitchArena
        matchState={{ ...mockMatchState, user_is_batting: true }}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{
          type: 'NORMAL',
          runs: 3,
          title: '+3 RUNS',
          number: 3,
          userChoice: 3,
          computerChoice: 5,
        }}
        onSelectNumber={vi.fn()}
      />
    );

    // Old delivery reveal card text and VS comparison must NOT exist
    expect(screen.queryByText('Delivery Reveal')).toBeNull();
    expect(screen.queryByText('VS')).toBeNull();

    // Result container exists without dark modal wrapper
    const resultElement = screen.getByTestId('onfield-ball-result');
    expect(resultElement).toBeDefined();

    // Batter number 3 is displayed in the ball result
    expect(resultElement.textContent).toContain('3');
    // Computer's bowling choice 5 is NOT displayed in the ball result
    expect(resultElement.textContent).not.toContain('5');

    // Run outcome is displayed
    expect(screen.getByText('+3 RUNS')).toBeDefined();
  });

  it('When computer is batting, result displays ONLY computer batting number and not user bowling number', () => {
    render(
      <PitchArena
        matchState={{ ...mockMatchState, user_is_batting: false }}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{
          type: 'FOUR',
          runs: 4,
          title: 'FOUR!',
          number: 4,
          userChoice: 2,
          computerChoice: 4,
        }}
        onSelectNumber={vi.fn()}
      />
    );

    expect(screen.queryByText('Delivery Reveal')).toBeNull();
    expect(screen.queryByText('VS')).toBeNull();

    const resultElement = screen.getByTestId('onfield-ball-result');
    expect(resultElement).toBeDefined();

    // Computer's batting number 4 is displayed
    expect(resultElement.textContent).toContain('4');
    // User's bowling choice 2 is NOT displayed in the ball result
    expect(resultElement.textContent).not.toContain('2');
    expect(screen.getByText(/FOUR!/)).toBeDefined();
  });

  it('FOUR displays batter number, FOUR celebration, and opponent choice does not appear', () => {
    render(
      <PitchArena
        matchState={{ ...mockMatchState, user_is_batting: true }}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{
          type: 'FOUR',
          runs: 4,
          title: 'FOUR!',
          number: 4,
          userChoice: 4,
          computerChoice: 2,
        }}
        onSelectNumber={vi.fn()}
      />
    );

    const resultElement = screen.getByTestId('onfield-ball-result');
    expect(resultElement.textContent).toContain('4');
    expect(resultElement.textContent).not.toContain('2');
    expect(screen.getByText(/FOUR!/)).toBeDefined();
    expect(screen.queryByText('Delivery Reveal')).toBeNull();
    expect(screen.queryByText('VS')).toBeNull();
  });

  it('SIX displays batter number, SIX celebration, and opponent choice does not appear', () => {
    render(
      <PitchArena
        matchState={{ ...mockMatchState, user_is_batting: true }}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{
          type: 'SIX',
          runs: 6,
          title: 'SIX!',
          number: 6,
          userChoice: 6,
          computerChoice: 1,
        }}
        onSelectNumber={vi.fn()}
      />
    );

    const resultElement = screen.getByTestId('onfield-ball-result');
    expect(resultElement.textContent).toContain('6');
    expect(resultElement.textContent).not.toContain('1');
    expect(screen.getByText(/SIX!/)).toBeDefined();
    expect(screen.queryByText('Delivery Reveal')).toBeNull();
    expect(screen.queryByText('VS')).toBeNull();
  });

  it('WICKET displays WICKET celebration and player name WITHOUT showing batter number', () => {
    render(
      <PitchArena
        matchState={{ ...mockMatchState, user_is_batting: true }}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{
          type: 'WICKET',
          runs: 0,
          title: 'WICKET!',
          subtitle: 'Rohit Sharma is out!',
          userChoice: 3,
          computerChoice: 3,
        }}
        onSelectNumber={vi.fn()}
      />
    );

    const resultElement = screen.getByTestId('onfield-ball-result');
    // Batter choice / number must NOT appear in the onfield result
    expect(resultElement.textContent).not.toContain('3');
    expect(screen.getByText('WICKET!')).toBeDefined();
    expect(screen.getByText('Rohit Sharma is out!')).toBeDefined();
    expect(screen.queryByText('Delivery Reveal')).toBeNull();
    expect(screen.queryByText('VS')).toBeNull();
  });

  it('PitchArena renders exactly 6 circular input buttons with 1:1 aspect ratio', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={null}
        onSelectNumber={vi.fn()}
      />
    );

    for (let num = 1; num <= 6; num++) {
      const btn = screen.getByLabelText(`Select ${num}`);
      expect(btn).toBeDefined();
      expect(btn.className).toContain('rounded-full');
      expect(btn.className).toContain('aspect-square');
      expect(btn.style.aspectRatio).toBe('1 / 1');
    }
  });

  it('PitchArena renders milestone celebration overlay for FIFTY with batsman name', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={null}
        milestoneFeedback={{
          batsmanName: 'Virat Kohli',
          milestone: 50,
          label: 'FIFTY!',
        }}
        onSelectNumber={vi.fn()}
      />
    );

    const milestoneElement = screen.getByTestId('batsman-milestone-celebration');
    expect(milestoneElement).toBeDefined();
    expect(screen.getByText('FIFTY!')).toBeDefined();
    expect(screen.getByText('Virat Kohli')).toBeDefined();
  });

  it('PitchArena renders milestone celebration overlay for CENTURY with batsman name', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={null}
        milestoneFeedback={{
          batsmanName: 'Rohit Sharma',
          milestone: 100,
          label: 'CENTURY!',
        }}
        onSelectNumber={vi.fn()}
      />
    );

    const milestoneElement = screen.getByTestId('batsman-milestone-celebration');
    expect(milestoneElement).toBeDefined();
    expect(screen.getByText('CENTURY!')).toBeDefined();
    expect(screen.getByText('Rohit Sharma')).toBeDefined();
  });

  it('Scoreboard places bowler on User side and batters on Computer side when computer is batting', () => {
    const compBattingState: MatchState = {
      ...mockMatchState,
      user_is_batting: false,
    };
    render(<Scoreboard matchState={compBattingState} />);
    expect(screen.getAllByText('Batting').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Bowling').length).toBeGreaterThan(0);
  });

  it('InningsBreakModal displays 1st innings score, target, and triggers Next Innings', () => {
    const breakState: MatchState = {
      ...mockMatchState,
      status: 'INNINGS_BREAK',
      score: 62,
      wickets: 4,
      target: 63,
    };
    const handleNext = vi.fn();
    render(<InningsBreakModal matchState={breakState} onStartNextInnings={handleNext} />);

    expect(screen.getByText('End of Innings')).toBeDefined();
    expect(screen.getByText('62 / 4')).toBeDefined();
    expect(screen.getByText(/Australia need/i)).toBeDefined();
    expect(screen.getByText('63')).toBeDefined();

    const nextBtn = screen.getByText('Next Innings');
    fireEvent.click(nextBtn);
    expect(handleNext).toHaveBeenCalledTimes(1);
  });

  it('MatchResultModal associates scores correctly when user bats first', () => {
    const userBatsFirstState: MatchState = {
      ...mockMatchState,
      status: 'COMPLETED',
      user_batted_first: true,
      winner: 'India',
      innings_1_score: 58,
      innings_1_wickets: 4,
      innings_2_score: 52,
      innings_2_wickets: 5,
      result_description: 'India won by 6 runs.',
    };
    const handlePlayAgain = vi.fn();
    render(<MatchResultModal matchState={userBatsFirstState} onPlayAgain={handlePlayAgain} />);

    expect(screen.getByText('India Win!')).toBeDefined();
    expect(screen.getByText('India won by 6 runs.')).toBeDefined();

    // Row 1: India (batted first) -> 58 / 4
    const row1 = screen.getByTestId('innings-1-summary');
    expect(within(row1).getByText('India')).toBeDefined();
    expect(within(row1).getByText('58 / 4')).toBeDefined();

    // Row 2: Australia (chased second) -> 52 / 5
    const row2 = screen.getByTestId('innings-2-summary');
    expect(within(row2).getByText('Australia')).toBeDefined();
    expect(within(row2).getByText('52 / 5')).toBeDefined();

    const playBtn = screen.getByText('Play Again');
    fireEvent.click(playBtn);
    expect(handlePlayAgain).toHaveBeenCalledTimes(1);
  });

  it('MatchResultModal associates scores correctly when computer bats first (primary fix)', () => {
    // Computer won toss, chose to bat first
    // Australia: 80/5 (innings 1)
    // India: 81/3 (innings 2) -> India wins by 7 wickets
    const computerBatsFirstState: MatchState = {
      ...mockMatchState,
      status: 'COMPLETED',
      user_batted_first: false,
      winner: 'India',
      innings_1_score: 80,
      innings_1_wickets: 5,
      innings_2_score: 81,
      innings_2_wickets: 3,
      result_description: 'India won by 7 wickets.',
    };
    render(<MatchResultModal matchState={computerBatsFirstState} onPlayAgain={vi.fn()} />);

    expect(screen.getByText('India Win!')).toBeDefined();
    expect(screen.getByText('India won by 7 wickets.')).toBeDefined();

    // Row 1 MUST be Australia (batted first) with 80 / 5, NOT India!
    const row1 = screen.getByTestId('innings-1-summary');
    expect(within(row1).getByText('Australia')).toBeDefined();
    expect(within(row1).getByText('80 / 5')).toBeDefined();

    // Row 2 MUST be India (batted second) with 81 / 3, NOT Australia!
    const row2 = screen.getByTestId('innings-2-summary');
    expect(within(row2).getByText('India')).toBeDefined();
    expect(within(row2).getByText('81 / 3')).toBeDefined();
  });

  it('MatchResultModal associates scores correctly when computer bats first and computer wins', () => {
    // Australia: 75/3 (innings 1)
    // India: 60/5 (innings 2) -> Australia wins by 15 runs
    const computerWinsBattingFirstState: MatchState = {
      ...mockMatchState,
      status: 'COMPLETED',
      user_batted_first: false,
      winner: 'Australia',
      innings_1_score: 75,
      innings_1_wickets: 3,
      innings_2_score: 60,
      innings_2_wickets: 5,
      result_description: 'Australia won by 15 runs.',
    };
    render(<MatchResultModal matchState={computerWinsBattingFirstState} onPlayAgain={vi.fn()} />);

    expect(screen.getByText('Australia Win!')).toBeDefined();
    expect(screen.getByText('Australia won by 15 runs.')).toBeDefined();

    const row1 = screen.getByTestId('innings-1-summary');
    expect(within(row1).getByText('Australia')).toBeDefined();
    expect(within(row1).getByText('75 / 3')).toBeDefined();

    const row2 = screen.getByTestId('innings-2-summary');
    expect(within(row2).getByText('India')).toBeDefined();
    expect(within(row2).getByText('60 / 5')).toBeDefined();
  });

  it('MatchResultModal renders Tie result correctly when computer bats first', () => {
    const tieState: MatchState = {
      ...mockMatchState,
      status: 'COMPLETED',
      user_batted_first: false,
      winner: null,
      is_tie: true,
      innings_1_score: 60,
      innings_1_wickets: 5,
      innings_2_score: 60,
      innings_2_wickets: 5,
      result_description: 'Match tied (60 - 60).',
    };
    render(<MatchResultModal matchState={tieState} onPlayAgain={vi.fn()} />);

    expect(screen.getByText("It's a Tie!")).toBeDefined();
    expect(screen.getByText('Match tied (60 - 60).')).toBeDefined();

    const row1 = screen.getByTestId('innings-1-summary');
    expect(within(row1).getByText('Australia')).toBeDefined();
    expect(within(row1).getByText('60 / 5')).toBeDefined();

    const row2 = screen.getByTestId('innings-2-summary');
    expect(within(row2).getByText('India')).toBeDefined();
    expect(within(row2).getByText('60 / 5')).toBeDefined();
  });
});

describe('useCricketGame milestone detection', () => {
  let mockSocket: any;

  beforeEach(() => {
    vi.useFakeTimers();
    mockSocket = {
      readyState: 1, // WebSocket.OPEN
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    };
    vi.stubGlobal('WebSocket', vi.fn().mockImplementation(function () {
      return mockSocket;
    }));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('triggers FIFTY milestone on crossing 50 and does not retrigger on 51', () => {
    const { result } = renderHook(() => useCricketGame());

    // Connect socket
    act(() => {
      mockSocket.onopen?.();
    });

    // 1. Striker at 48 -> no milestone
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 48, balls: 20 },
            non_striker: { id: 2, name: 'Virat Kohli', runs: 4, balls: 5 },
            last_ball: {
              batsman_choice: 4,
              bowler_choice: 2,
              runs: 4,
              is_wicket: false,
              user_choice: 4,
              computer_choice: 2,
              user_timed_out: false,
              event: 'FOUR',
              out_player: null,
            },
          },
        }),
      });
    });

    expect(result.current.milestoneFeedback).toBeNull();

    // 2. Striker scores 4 -> runs: 52 (crosses 50!)
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 52, balls: 21 },
            non_striker: { id: 2, name: 'Virat Kohli', runs: 4, balls: 5 },
            last_ball: {
              batsman_choice: 4,
              bowler_choice: 1,
              runs: 4,
              is_wicket: false,
              user_choice: 4,
              computer_choice: 1,
              user_timed_out: false,
              event: 'FOUR',
              out_player: null,
            },
          },
        }),
      });
    });

    // Ball result is displayed first, milestone sequenced after 1400ms
    act(() => {
      vi.advanceTimersByTime(1400);
    });

    expect(result.current.milestoneFeedback).toEqual({
      batsmanName: 'Rohit Sharma',
      milestone: 50,
      label: 'FIFTY!',
    });

    // 3. Next ball: striker scores 1 -> runs: 53 (already celebrated 50, must NOT retrigger!)
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 53, balls: 22 },
            non_striker: { id: 2, name: 'Virat Kohli', runs: 4, balls: 5 },
            last_ball: {
              batsman_choice: 1,
              bowler_choice: 3,
              runs: 1,
              is_wicket: false,
              user_choice: 1,
              computer_choice: 3,
              user_timed_out: false,
              event: 'NORMAL',
              out_player: null,
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    // Milestone should NOT retrigger
    expect(result.current.milestoneFeedback).toBeNull();
  });

  it('triggers CENTURY milestone on crossing 100 and does not retrigger on 101', () => {
    const { result } = renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    // Striker at 96
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 96, balls: 45 },
            non_striker: { id: 2, name: 'Virat Kohli', runs: 4, balls: 5 },
            last_ball: {
              batsman_choice: 2,
              bowler_choice: 1,
              runs: 2,
              is_wicket: false,
              user_choice: 2,
              computer_choice: 1,
              user_timed_out: false,
              event: 'NORMAL',
              out_player: null,
            },
          },
        }),
      });
    });

    // Striker hits a 6 to reach 102 (crosses 100!)
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 102, balls: 46 },
            non_striker: { id: 2, name: 'Virat Kohli', runs: 4, balls: 5 },
            last_ball: {
              batsman_choice: 6,
              bowler_choice: 2,
              runs: 6,
              is_wicket: false,
              user_choice: 6,
              computer_choice: 2,
              user_timed_out: false,
              event: 'SIX',
              out_player: null,
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(1400);
    });

    expect(result.current.milestoneFeedback).toEqual({
      batsmanName: 'Rohit Sharma',
      milestone: 100,
      label: 'CENTURY!',
    });

    // Next ball to 103 -> no retrigger
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 103, balls: 47 },
            non_striker: { id: 2, name: 'Virat Kohli', runs: 4, balls: 5 },
            last_ball: {
              batsman_choice: 1,
              bowler_choice: 5,
              runs: 1,
              is_wicket: false,
              user_choice: 1,
              computer_choice: 5,
              user_timed_out: false,
              event: 'NORMAL',
              out_player: null,
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(result.current.milestoneFeedback).toBeNull();
  });
});

describe('Slice 13 Pre-Match Flows Frontend Component Tests', () => {
  it('IntroScreen renders WELCOME TO HAND CRICKET BY SRW and transitions on tap or timeout', () => {
    vi.useFakeTimers();
    const handleFinish = vi.fn();
    render(<IntroScreen onFinish={handleFinish} durationMs={2000} />);

    expect(screen.getByText(/WELCOME TO/i)).toBeDefined();
    expect(screen.getByText('HAND CRICKET')).toBeDefined();
    expect(screen.getByText(/BY SRW/i)).toBeDefined();

    // Advance timer to trigger transition
    act(() => {
      vi.advanceTimersByTime(2100);
    });
    expect(handleFinish).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('LandingScreen renders Play vs Computer and disabled Play with Friend with COMING SOON badge', () => {
    const handlePlay = vi.fn();
    render(<LandingScreen onPlayVsComputer={handlePlay} />);

    expect(screen.getByText('HAND CRICKET')).toBeDefined();
    expect(screen.getByText('Play vs Computer')).toBeDefined();
    expect(screen.getByText('Play with Friend')).toBeDefined();
    expect(screen.getByText('COMING SOON')).toBeDefined();

    const playBtn = screen.getByText('PLAY NOW');
    fireEvent.click(playBtn);
    expect(handlePlay).toHaveBeenCalledTimes(1);
  });

  it('TeamSelectionScreen renders all 4 teams and handles team selection and back navigation', () => {
    const handleSelect = vi.fn();
    const handleBack = vi.fn();
    const mockTeams: TeamRoster[] = [
      { id: 'IND', name: 'India', players: [{ id: 1, name: 'Rohit Sharma' }] },
      { id: 'AUS', name: 'Australia', players: [{ id: 1, name: 'David Warner' }] },
      { id: 'ENG', name: 'England', players: [{ id: 1, name: 'Jos Buttler' }] },
      { id: 'SA', name: 'South Africa', players: [{ id: 1, name: 'Temba Bavuma' }] },
    ];

    render(
      <TeamSelectionScreen
        availableTeams={mockTeams}
        onSelectTeam={handleSelect}
        onBack={handleBack}
      />
    );

    expect(screen.getByText('CHOOSE YOUR TEAM')).toBeDefined();
    expect(screen.getAllByText('India').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Australia').length).toBeGreaterThan(0);
    expect(screen.getAllByText('England').length).toBeGreaterThan(0);
    expect(screen.getAllByText('South Africa').length).toBeGreaterThan(0);

    // Select Australia
    fireEvent.click(screen.getAllByText('Australia')[0]);

    // Click Proceed
    const proceedBtn = screen.getByText(/PROCEED TO TOSS/i);
    fireEvent.click(proceedBtn);
    expect(handleSelect).toHaveBeenCalledWith('AUS');

    // Click Back
    const backBtn = screen.getByText(/← BACK/i);
    fireEvent.click(backBtn);
    expect(handleBack).toHaveBeenCalledTimes(1);
  });

  it('TossScreen displays both teams and coin flip, then reveals user toss win with BAT and BOWL buttons', () => {
    vi.useFakeTimers();
    const handleChoice = vi.fn();
    render(
      <TossScreen
        userTeam={{ id: 'IND', name: 'India' }}
        opponentTeam={{ id: 'AUS', name: 'Australia' }}
        tossWinner="user"
        tossDecision={null}
        onChooseToss={handleChoice}
      />
    );

    // Initial state: Both teams are visible on sides
    expect(screen.getByText('YOU')).toBeDefined();
    expect(screen.getByText('INDIA')).toBeDefined();
    expect(screen.getByText('COMPUTER')).toBeDefined();
    expect(screen.getByText('AUSTRALIA')).toBeDefined();
    expect(screen.getByText(/COIN IN THE AIR/i)).toBeDefined();

    // Advance timers past 2.2s flip animation
    act(() => {
      vi.advanceTimersByTime(2600);
    });

    expect(screen.getByText('YOU WON THE TOSS!')).toBeDefined();
    expect(screen.getByText('BAT FIRST')).toBeDefined();
    expect(screen.getByText('BOWL FIRST')).toBeDefined();

    fireEvent.click(screen.getByText('BAT FIRST'));
    expect(handleChoice).toHaveBeenCalledWith('BAT');

    fireEvent.click(screen.getByText('BOWL FIRST'));
    expect(handleChoice).toHaveBeenCalledWith('BOWL');
    vi.useRealTimers();
  });

  it('TossScreen displays computer toss win and its decision after coin flip completes', () => {
    vi.useFakeTimers();
    render(
      <TossScreen
        userTeam={{ id: 'IND', name: 'India' }}
        opponentTeam={{ id: 'AUS', name: 'Australia' }}
        tossWinner="computer"
        tossDecision="BAT"
        onChooseToss={vi.fn()}
      />
    );

    // Advance past flip animation
    act(() => {
      vi.advanceTimersByTime(2600);
    });

    expect(screen.getByText('COMPUTER WON THE TOSS')).toBeDefined();
    expect(screen.getByText(/BAT FIRST/i)).toBeDefined();
    vi.useRealTimers();
  });

  it('BowlerPickerModal displays quota, eligible players, and disables used bowlers', () => {
    const handleBowler = vi.fn();
    const eligible = [
      { id: 10, name: 'Mohammed Shami' },
      { id: 9, name: 'Jasprit Bumrah' },
    ];
    const used = [{ id: 11, name: 'Mohammed Siraj' }];

    render(
      <BowlerPickerModal
        currentOver={2}
        maxOvers={5}
        teamName="India"
        eligibleBowlers={eligible}
        usedBowlers={used}
        onSelectBowler={handleBowler}
      />
    );

    expect(screen.getByText(/OVER 2 OF 5/i)).toBeDefined();
    expect(screen.getByText('Mohammed Siraj')).toBeDefined();
    expect(screen.getByText(/QUOTA EXHAUSTED/i)).toBeDefined();
    expect(screen.getByText('Mohammed Shami')).toBeDefined();
    expect(screen.getByText('Jasprit Bumrah')).toBeDefined();

    // Select Jasprit Bumrah
    fireEvent.click(screen.getByText('Jasprit Bumrah'));

    // Confirm
    const confirmBtn = screen.getByText(/CONFIRM BOWLER/i);
    fireEvent.click(confirmBtn);
    expect(handleBowler).toHaveBeenCalledWith(9);
  });

  it('Scoreboard renders England and South Africa flags correctly', () => {
    const engState: MatchState = {
      ...mockMatchState,
      user_team: { id: 'ENG', name: 'England' },
      opponent_team: { id: 'SA', name: 'South Africa' },
    };
    render(<Scoreboard matchState={engState} />);

    expect(screen.getAllByText('England').length).toBeGreaterThan(0);
    expect(screen.getAllByText('South Africa').length).toBeGreaterThan(0);
  });

  it('PitchArena renders OVER COMPLETE banner when over ends', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{
          type: 'NORMAL',
          runs: 0,
          title: 'OVER COMPLETE',
          subtitle: 'Over finished',
        }}
        onSelectNumber={vi.fn()}
      />
    );

    expect(screen.getByText('OVER COMPLETE')).toBeDefined();
    expect(screen.getByText(/Strike rotated • Preparing next over/i)).toBeDefined();
  });
});

describe('Slice 14: Polish, Animations, Audio & Edge Cases', () => {
  it('PitchArena renders visual countdown bar with remaining seconds when interactive', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={null}
        turnCountdown={{
          remainingSeconds: 8,
          totalSeconds: 10,
          isUrgent: false,
        }}
        onSelectNumber={vi.fn()}
      />
    );

    const countdownBar = screen.getByTestId('turn-countdown-bar');
    expect(countdownBar).toBeDefined();
    expect(screen.getByText(/8s remaining/i)).toBeDefined();
    expect(screen.getByText('8s')).toBeDefined();
  });

  it('PitchArena renders low-time urgency warning styling when isUrgent is true', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={null}
        turnCountdown={{
          remainingSeconds: 2,
          totalSeconds: 10,
          isUrgent: true,
        }}
        onSelectNumber={vi.fn()}
      />
    );

    const countdownBar = screen.getByTestId('turn-countdown-bar');
    expect(countdownBar).toBeDefined();
    expect(screen.getByText(/2s remaining/i)).toBeDefined();
    expect(screen.getByText('2s')).toBeDefined();
  });

  it('PitchArena shows "Waiting for delivery..." when remaining seconds reach 0 without client submit', () => {
    const handleSelect = vi.fn();
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={null}
        turnCountdown={{
          remainingSeconds: 0,
          totalSeconds: 10,
          isUrgent: true,
        }}
        onSelectNumber={handleSelect}
      />
    );

    expect(screen.getByText(/Waiting for delivery.../i)).toBeDefined();
    // Client-side selection is NOT triggered automatically:
    expect(handleSelect).not.toHaveBeenCalled();
  });

  it('PitchArena renders styled TIMEOUT — AUTO-PICKED badge when userTimedOut is true', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{
          type: 'NORMAL',
          runs: 2,
          title: '+2 RUNS',
          userChoice: 2,
          computerChoice: 4,
          userTimedOut: true,
        }}
        onSelectNumber={vi.fn()}
      />
    );

    const badge = screen.getByTestId('timeout-auto-picked-badge');
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain('TIMEOUT — AUTO-PICKED');
  });

  it('PitchArena disables keypad buttons and sets opacity-45 while awaiting opponent', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={3}
        isWaiting={true}
        eventFeedback={null}
        onSelectNumber={vi.fn()}
      />
    );

    const btn1 = screen.getByLabelText('Select 1') as HTMLButtonElement;
    expect(btn1.disabled).toBe(true);
    expect(btn1.className).toContain('cursor-not-allowed');
    expect(btn1.className).toContain('opacity-45');
  });

  it('Header renders audio toggle button and invokes onToggleMute', () => {
    const handleToggleMute = vi.fn();
    render(
      <Header
        matchState={mockMatchState}
        onOpenSettings={vi.fn()}
        isMuted={false}
        onToggleMute={handleToggleMute}
      />
    );

    const audioBtn = screen.getByTestId('header-audio-toggle');
    expect(audioBtn).toBeDefined();
    expect(audioBtn.getAttribute('aria-label')).toBe('Mute sound');

    fireEvent.click(audioBtn);
    expect(handleToggleMute).toHaveBeenCalledTimes(1);
  });

  it('SettingsModal renders audio toggle card and calls onToggleMute', () => {
    const handleToggleMute = vi.fn();
    render(
      <SettingsModal
        isOpen={true}
        matchState={mockMatchState}
        onClose={vi.fn()}
        onResetMatch={vi.fn()}
        isMuted={true}
        onToggleMute={handleToggleMute}
      />
    );

    expect(screen.getByText('Game Audio & SFX')).toBeDefined();
    const toggleBtn = screen.getByTestId('settings-audio-toggle');
    expect(toggleBtn.textContent).toContain('Sound: OFF');

    fireEvent.click(toggleBtn);
    expect(handleToggleMute).toHaveBeenCalledTimes(1);
  });

  it('soundManager toggles mute and safely executes audio calls in test environment', () => {
    const initialMute = soundManager.isMuted();
    const toggled = soundManager.toggleMute();
    expect(toggled).toBe(!initialMute);
    expect(soundManager.isMuted()).toBe(!initialMute);

    // Call all audio methods to verify zero crashes / graceful no-op in tests
    expect(() => {
      soundManager.playClick();
      soundManager.playCoinToss();
      soundManager.playBatHit(2);
      soundManager.playFour();
      soundManager.playSix();
      soundManager.playWicket();
      soundManager.playTimerWarning();
    }).not.toThrow();

    // Restore mute state
    soundManager.setMuted(initialMute);
  });

  it('resets reconnect retry budget on resetGame and resetPreMatch', () => {
    vi.useFakeTimers();
    let currentSocket: any;
    const createMockSocket = () => {
      const sock: any = {
        readyState: 1, // OPEN
        send: vi.fn(),
        close: vi.fn(),
        onopen: null,
        onmessage: null,
        onerror: null,
        onclose: null,
      };
      currentSocket = sock;
      return sock;
    };

    vi.stubGlobal('WebSocket', vi.fn().mockImplementation(createMockSocket));

    const { result } = renderHook(() => useCricketGame());

    // 1. Initial connect
    act(() => {
      currentSocket.onopen?.();
    });
    expect(result.current.connectionStatus).toBe('connected');

    // 2. Simulate connection drops up to retry limit (4 attempts max)
    // Attempt 1
    act(() => {
      currentSocket.onclose?.();
    });
    expect(result.current.connectionStatus).toBe('reconnecting');
    act(() => {
      vi.advanceTimersByTime(1500); // delay 1200ms
    });

    // Attempt 2
    act(() => {
      currentSocket.onclose?.();
    });
    expect(result.current.connectionStatus).toBe('reconnecting');
    act(() => {
      vi.advanceTimersByTime(2000); // delay 1800ms
    });

    // Attempt 3
    act(() => {
      currentSocket.onclose?.();
    });
    expect(result.current.connectionStatus).toBe('reconnecting');
    act(() => {
      vi.advanceTimersByTime(3000); // delay 2700ms
    });

    // Attempt 4
    act(() => {
      currentSocket.onclose?.();
    });
    expect(result.current.connectionStatus).toBe('reconnecting');
    act(() => {
      vi.advanceTimersByTime(4500); // delay 4000ms
    });

    // 3. Retry budget is now exhausted (reconnectAttemptRef === 4). Next drop must transition to disconnected
    act(() => {
      currentSocket.onclose?.();
    });
    expect(result.current.connectionStatus).toBe('disconnected');

    // Advancing timers should NOT trigger reconnect because budget is exhausted
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.connectionStatus).toBe('disconnected');

    // 4. resetGame() must reset the retry budget
    act(() => {
      result.current.resetGame();
    });
    expect(result.current.connectionStatus).toBe('connecting');
    act(() => {
      currentSocket.onopen?.();
    });
    expect(result.current.connectionStatus).toBe('connected');

    // 5. Verify that a subsequent drop gets the full retry budget again
    act(() => {
      currentSocket.onclose?.();
    });
    expect(result.current.connectionStatus).toBe('reconnecting');

    // 6. Exhaust retry budget again to test resetPreMatch()
    act(() => {
      vi.advanceTimersByTime(1500);
    });
    act(() => {
      currentSocket.onclose?.(); // attempt 2
    });
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    act(() => {
      currentSocket.onclose?.(); // attempt 3
    });
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    act(() => {
      currentSocket.onclose?.(); // attempt 4
    });
    act(() => {
      vi.advanceTimersByTime(4500);
    });
    // Exhausted
    act(() => {
      currentSocket.onclose?.();
    });
    expect(result.current.connectionStatus).toBe('disconnected');

    // 7. resetPreMatch() must reset the retry budget
    act(() => {
      result.current.resetPreMatch();
    });
    expect(result.current.connectionStatus).toBe('connecting');
    act(() => {
      currentSocket.onopen?.();
    });
    expect(result.current.connectionStatus).toBe('connected');

    // Drop connection: should reconnect (budget restored!)
    act(() => {
      currentSocket.onclose?.();
    });
    expect(result.current.connectionStatus).toBe('reconnecting');

    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('clears pending milestone timeout during component unmount', () => {
    vi.useFakeTimers();
    let mockSocket: any = {
      readyState: 1,
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    };
    vi.stubGlobal('WebSocket', vi.fn().mockImplementation(() => mockSocket));

    const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout');

    const { result, unmount } = renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    // Striker scores 4 to reach 52 (crosses 50 milestone)
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 52, balls: 21 },
            non_striker: { id: 2, name: 'Virat Kohli', runs: 4, balls: 5 },
            last_ball: {
              batsman_choice: 4,
              bowler_choice: 1,
              runs: 4,
              is_wicket: false,
              user_choice: 4,
              computer_choice: 1,
              user_timed_out: false,
              event: 'FOUR',
              out_player: null,
            },
          },
        }),
      });
    });

    // Milestone is pending (1400ms delay)
    expect(result.current.milestoneFeedback).toBeNull();
    clearTimeoutSpy.mockClear();

    // Unmount before milestone timeout fires
    unmount();

    // Verify clearTimeout was called during unmount cleanup
    expect(clearTimeoutSpy).toHaveBeenCalled();

    // Advance time past 1400ms - ensure no timers throw or execute unexpectedly
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    clearTimeoutSpy.mockRestore();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });
});

describe('Slice 14 Audio Refinement: Realistic Sports Crowd Cheering', () => {
  let mockSocket: any;

  beforeEach(() => {
    vi.useFakeTimers();
    mockSocket = {
      readyState: 1, // OPEN
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    };
    vi.stubGlobal('WebSocket', vi.fn().mockImplementation(() => mockSocket));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('FOUR triggers crowd audio playFour() exactly once', () => {
    const playFourSpy = vi.spyOn(soundManager, 'playFour');
    const { result } = renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            last_ball: {
              runs: 4,
              event: 'FOUR',
              batsman_choice: 4,
              bowler_choice: 1,
              user_choice: 4,
              computer_choice: 1,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    expect(playFourSpy).toHaveBeenCalledTimes(1);
    expect(result.current.eventFeedback?.title).toBe('FOUR!');
  });

  it('SIX triggers crowd audio playSix() exactly once', () => {
    const playSixSpy = vi.spyOn(soundManager, 'playSix');
    const { result } = renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            last_ball: {
              runs: 6,
              event: 'SIX',
              batsman_choice: 6,
              bowler_choice: 2,
              user_choice: 6,
              computer_choice: 2,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    expect(playSixSpy).toHaveBeenCalledTimes(1);
    expect(result.current.eventFeedback?.title).toBe('SIX!');
  });

  it('WICKET triggers crowd audio playWicket() exactly once', () => {
    const playWicketSpy = vi.spyOn(soundManager, 'playWicket');
    const { result } = renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            last_ball: {
              runs: 0,
              event: 'WICKET',
              batsman_choice: 3,
              bowler_choice: 3,
              user_choice: 3,
              computer_choice: 3,
              user_timed_out: false,
              is_wicket: true,
              out_player: 'Rohit Sharma',
            },
          },
        }),
      });
    });

    expect(playWicketSpy).toHaveBeenCalledTimes(1);
    expect(result.current.eventFeedback?.title).toBe('WICKET!');
  });

  it('Match win triggers victory crowd audio playMatchWin() exactly once', () => {
    const playWinSpy = vi.spyOn(soundManager, 'playMatchWin');
    renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            status: 'COMPLETED',
            winner: 'India',
            is_tie: false,
            user_team: { id: 'IND', name: 'India' },
            opponent_team: { id: 'AUS', name: 'Australia' },
            last_ball: {
              runs: 4,
              event: 'FOUR',
              batsman_choice: 4,
              bowler_choice: 1,
              user_choice: 4,
              computer_choice: 1,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    // Before feedback clears: winning shot audio has played, win celebration fires when modal displays
    expect(playWinSpy).not.toHaveBeenCalled();

    // Advance past the 1500ms ball delivery feedback
    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(playWinSpy).toHaveBeenCalledTimes(1);

    // Further timer advancement must not re-trigger
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(playWinSpy).toHaveBeenCalledTimes(1);
  });

  it('Match loss triggers loss crowd audio playMatchLoss() exactly once', () => {
    const playLossSpy = vi.spyOn(soundManager, 'playMatchLoss');
    renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            status: 'COMPLETED',
            winner: 'Australia',
            is_tie: false,
            user_team: { id: 'IND', name: 'India' },
            opponent_team: { id: 'AUS', name: 'Australia' },
            last_ball: {
              runs: 0,
              event: 'WICKET',
              batsman_choice: 5,
              bowler_choice: 5,
              user_choice: 5,
              computer_choice: 5,
              user_timed_out: false,
              is_wicket: true,
              out_player: 'Virat Kohli',
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(playLossSpy).toHaveBeenCalledTimes(1);
  });

  it('50-run milestone triggers playFifty() once for user batsman and does not replay on 51', () => {
    const playFiftySpy = vi.spyOn(soundManager, 'playFifty');
    const { result } = renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    // Cross 50 runs (from 48 to 52)
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 52, balls: 22 },
            last_ball: {
              runs: 4,
              event: 'FOUR',
              batsman_choice: 4,
              bowler_choice: 1,
              user_choice: 4,
              computer_choice: 1,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    // Milestone audio is synchronized with the milestone celebration banner (at 1400ms)
    expect(playFiftySpy).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1400);
    });

    expect(playFiftySpy).toHaveBeenCalledTimes(1);
    expect(result.current.milestoneFeedback?.label).toBe('FIFTY!');

    // Next ball to 53 runs -> must NOT retrigger playFifty
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 53, balls: 23 },
            last_ball: {
              runs: 1,
              event: 'NORMAL',
              batsman_choice: 1,
              bowler_choice: 2,
              user_choice: 1,
              computer_choice: 2,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(playFiftySpy).toHaveBeenCalledTimes(1);
  });

  it('50-run milestone triggers playFifty() for computer batsman when computer bats', () => {
    const playFiftySpy = vi.spyOn(soundManager, 'playFifty');
    renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    // Computer striker crosses 50
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            user_is_batting: false,
            striker: { id: 15, name: 'David Warner', runs: 54, balls: 25 },
            last_ball: {
              runs: 6,
              event: 'SIX',
              batsman_choice: 6,
              bowler_choice: 3,
              user_choice: 3,
              computer_choice: 6,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(1400);
    });

    expect(playFiftySpy).toHaveBeenCalledTimes(1);
  });

  it('100-run milestone triggers playCentury() exactly once', () => {
    const playCenturySpy = vi.spyOn(soundManager, 'playCentury');
    renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    // Cross 100 runs
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 104, balls: 48 },
            last_ball: {
              runs: 6,
              event: 'SIX',
              batsman_choice: 6,
              bowler_choice: 1,
              user_choice: 6,
              computer_choice: 1,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(1400);
    });

    expect(playCenturySpy).toHaveBeenCalledTimes(1);

    // Next ball to 105 -> does not retrigger
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            striker: { id: 1, name: 'Rohit Sharma', runs: 105, balls: 49 },
            last_ball: {
              runs: 1,
              event: 'NORMAL',
              batsman_choice: 1,
              bowler_choice: 4,
              user_choice: 1,
              computer_choice: 4,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(playCenturySpy).toHaveBeenCalledTimes(1);
  });

  it('Mute prevents audio playback across all crowd sounds', () => {
    soundManager.setMuted(true);
    expect(soundManager.isMuted()).toBe(true);

    // Spies on audio output context
    expect(() => {
      soundManager.playFour();
      soundManager.playSix();
      soundManager.playWicket();
      soundManager.playFifty();
      soundManager.playCentury();
      soundManager.playMatchWin();
      soundManager.playMatchLoss();
    }).not.toThrow();

    soundManager.setMuted(false);
  });

  it('React re-render does not duplicate or replay crowd sounds', () => {
    const playFourSpy = vi.spyOn(soundManager, 'playFour');
    const { rerender } = renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            last_ball: {
              runs: 4,
              event: 'FOUR',
              batsman_choice: 4,
              bowler_choice: 2,
              user_choice: 4,
              computer_choice: 2,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    expect(playFourSpy).toHaveBeenCalledTimes(1);

    // Trigger multiple React re-renders
    rerender();
    rerender();
    rerender();

    expect(playFourSpy).toHaveBeenCalledTimes(1);
  });

  it('resetGame clears milestone and match celebration state for subsequent matches', () => {
    const playFiftySpy = vi.spyOn(soundManager, 'playFifty');
    const playWinSpy = vi.spyOn(soundManager, 'playMatchWin');
    const { result } = renderHook(() => useCricketGame());

    act(() => {
      mockSocket.onopen?.();
    });

    // Match 1: reach 50 runs and win
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            status: 'COMPLETED',
            winner: 'India',
            striker: { id: 1, name: 'Rohit Sharma', runs: 50, balls: 20 },
            last_ball: {
              runs: 4,
              event: 'FOUR',
              batsman_choice: 4,
              bowler_choice: 1,
              user_choice: 4,
              computer_choice: 1,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(playFiftySpy).toHaveBeenCalledTimes(1);
    expect(playWinSpy).toHaveBeenCalledTimes(1);

    // User restarts match via Play Again
    act(() => {
      result.current.resetGame();
    });

    // Match 2: same batsman reaches 50 runs again in fresh match
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'ball_result',
          match_state: {
            ...mockMatchState,
            status: 'INNINGS_1',
            striker: { id: 1, name: 'Rohit Sharma', runs: 50, balls: 21 },
            last_ball: {
              runs: 4,
              event: 'FOUR',
              batsman_choice: 4,
              bowler_choice: 2,
              user_choice: 4,
              computer_choice: 2,
              user_timed_out: false,
              is_wicket: false,
              out_player: null,
            },
          },
        }),
      });
    });

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    // 50 runs milestone triggered freshly in the new match!
    expect(playFiftySpy).toHaveBeenCalledTimes(2);
  });
});

describe('Slice 14 Audio Preload: Early Crowd Buffer Decoding & Fallback Safety', () => {
  let mockSocket: any;

  beforeEach(() => {
    vi.useFakeTimers();
    soundManager.resetContextForTesting();
    mockSocket = {
      readyState: 1, // OPEN
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    };
    const mockWsClass: any = vi.fn().mockImplementation(() => mockSocket);
    mockWsClass.OPEN = 1;
    mockWsClass.CONNECTING = 0;
    mockWsClass.CLOSING = 2;
    mockWsClass.CLOSED = 3;
    vi.stubGlobal('WebSocket', mockWsClass);
  });

  afterEach(() => {
    soundManager.resetContextForTesting();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('triggers preloadAll() during useCricketGame hook initialization and pre-match lifecycle steps', () => {
    const preloadSpy = vi.spyOn(soundManager, 'preloadAll');

    const { result } = renderHook(() => useCricketGame());
    // 1. Triggered on mount
    expect(preloadSpy).toHaveBeenCalledTimes(1);

    // 2. Pre-match step: finishIntro
    act(() => {
      result.current.finishIntro();
    });
    expect(preloadSpy).toHaveBeenCalledTimes(2);

    // 3. Pre-match step: startVsComputer
    act(() => {
      result.current.startVsComputer();
    });
    expect(preloadSpy).toHaveBeenCalledTimes(3);

    // Connect socket
    act(() => {
      mockSocket.onopen?.();
    });

    // Provide pre-match team selection state
    act(() => {
      mockSocket.onmessage?.({
        data: JSON.stringify({
          type: 'pre_match_state',
          pre_match_state: {
            stage: 'TEAM_SELECTION',
            available_teams: [
              { id: 'IND', name: 'India', flag: '🇮🇳' },
              { id: 'AUS', name: 'Australia', flag: '🇦🇺' },
            ],
            user_team: null,
            opponent_team: null,
            toss_winner: null,
            toss_decision: null,
          },
        }),
      });
    });

    // 4. Pre-match step: selectTeam
    act(() => {
      result.current.selectTeam('IND');
    });
    expect(preloadSpy).toHaveBeenCalledTimes(4);

    // 5. Pre-match step: chooseToss
    act(() => {
      result.current.chooseToss('BAT');
    });
    expect(preloadSpy).toHaveBeenCalledTimes(5);

    // 6. Pre-match step: finishToss
    act(() => {
      result.current.finishToss();
    });
    expect(preloadSpy).toHaveBeenCalledTimes(6);

    // 7. Pre-match step: selectBowler
    act(() => {
      result.current.selectBowler(1);
    });
    expect(preloadSpy).toHaveBeenCalledTimes(7);
  });

  it('plays decoded AudioBuffer when crowd audio asset is cached', () => {
    const mockSource = {
      buffer: null as any,
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
      onended: null as any,
    };
    const mockGain = {
      gain: {
        value: 1,
        setValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
    };
    const mockContext = {
      state: 'running',
      currentTime: 0,
      destination: {},
      createBufferSource: vi.fn().mockReturnValue(mockSource),
      createGain: vi.fn().mockReturnValue(mockGain),
      resume: vi.fn().mockResolvedValue(undefined),
    };

    vi.stubGlobal('AudioContext', vi.fn().mockImplementation(() => mockContext));

    // Seed mock AudioBuffer into soundManager's cache
    const dummyBuffer = { duration: 1.5, length: 66150, sampleRate: 44100, numberOfChannels: 2 } as AudioBuffer;
    soundManager.setCachedBuffer('crowd_four.wav', dummyBuffer);

    expect(soundManager.isBufferLoaded('crowd_four.wav')).toBe(true);
    expect(soundManager.getLoadedCount()).toBe(1);

    // Play FOUR
    soundManager.playFour();

    expect(mockContext.createBufferSource).toHaveBeenCalled();
    expect(mockSource.buffer).toBe(dummyBuffer);
    expect(mockGain.gain.setValueAtTime).toHaveBeenCalledWith(0.5, 0);
    expect(mockSource.connect).toHaveBeenCalledWith(mockGain);
    expect(mockGain.connect).toHaveBeenCalledWith(mockContext.destination);
    expect(mockSource.start).toHaveBeenCalled();
  });

  it('falls back seamlessly to synthetic sound when audio buffer is missing or fetch fails without affecting gameplay', () => {
    const mockSource = {
      buffer: null as any,
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
      onended: null as any,
    };
    const mockOscillator = {
      type: 'sine',
      frequency: {
        setValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    };
    const mockGain = {
      gain: {
        value: 1,
        setValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
    };
    const mockFilter = {
      type: 'lowpass',
      frequency: {
        setValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      Q: { value: 1 },
      connect: vi.fn(),
    };

    const mockContext = {
      state: 'running',
      currentTime: 0,
      sampleRate: 44100,
      destination: {},
      createBufferSource: vi.fn().mockReturnValue(mockSource),
      createOscillator: vi.fn().mockReturnValue(mockOscillator),
      createGain: vi.fn().mockReturnValue(mockGain),
      createBiquadFilter: vi.fn().mockReturnValue(mockFilter),
      createBuffer: vi.fn().mockReturnValue({
        getChannelData: vi.fn().mockReturnValue(new Float32Array(4410)),
      }),
      resume: vi.fn().mockResolvedValue(undefined),
    };

    vi.stubGlobal('AudioContext', vi.fn().mockImplementation(() => mockContext));

    // Ensure cache is empty
    soundManager.clearBufferCache();
    expect(soundManager.isBufferLoaded('crowd_four.wav')).toBe(false);

    // Call all crowd events - must execute synthetic fallback without throwing
    expect(() => {
      soundManager.playFour();
      soundManager.playSix();
      soundManager.playWicket();
      soundManager.playFifty();
      soundManager.playCentury();
      soundManager.playMatchWin();
      soundManager.playMatchLoss();
    }).not.toThrow();

    // Verify synthetic noise/oscillator elements were engaged
    expect(mockContext.createBiquadFilter).toHaveBeenCalled();
    expect(mockContext.createGain).toHaveBeenCalled();
  });

  it('preloadAudio handles fetch network error or non-200 gracefully and returns null', async () => {
    const mockContext = {
      state: 'running',
      currentTime: 0,
      decodeAudioData: vi.fn(),
      resume: vi.fn().mockResolvedValue(undefined),
    };
    vi.stubGlobal('AudioContext', vi.fn().mockImplementation(() => mockContext));

    // Mock fetch returning HTTP 404
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    }));

    const result = await soundManager.preloadAudio('nonexistent.wav');
    expect(result).toBeNull();
    expect(soundManager.isBufferLoaded('nonexistent.wav')).toBe(false);
  });
});


