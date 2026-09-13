import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from './components/Header';
import { PitchArena } from './components/PitchArena';
import { Scoreboard } from './components/Scoreboard';
import { InningsBreakModal } from './components/InningsBreakModal';
import { MatchResultModal } from './components/MatchResultModal';
import { MatchState } from './types';

const mockMatchState: MatchState = {
  status: 'INNINGS_1',
  innings: 1,
  user_team: { id: 'IND', name: 'India' },
  opponent_team: { id: 'AUS', name: 'Australia' },
  batting_team: 'India',
  bowling_team: 'Australia',
  user_is_batting: true,
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
    expect(screen.getByText('1')).toBeDefined();
    expect(screen.getByText('0')).toBeDefined();
    expect(screen.getByText('4')).toBeDefined();
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

    expect(screen.getByText('Your Call!')).toBeDefined();
    expect(screen.getByText('Choose a number (1 – 6)')).toBeDefined();

    // Click button '4'
    const btn4 = screen.getByLabelText('Select 4');
    fireEvent.click(btn4);
    expect(handleSelect).toHaveBeenCalledWith(4);
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

    // Arena elements are STILL fully visible
    expect(screen.getByText('Your Call!')).toBeDefined();
    // Non-disruptive indicator is present
    expect(screen.getByText('Opponent is choosing…')).toBeDefined();
    // Buttons are still present on screen
    expect(screen.getByLabelText('Select 4')).toBeDefined();
  });

  it('PitchArena displays FOUR celebration overlay', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{ type: 'FOUR', runs: 4, title: 'FOUR!', number: 4 }}
        onSelectNumber={vi.fn()}
      />
    );

    expect(screen.getByText('FOUR!')).toBeDefined();
  });

  it('PitchArena displays SIX celebration overlay', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{ type: 'SIX', runs: 6, title: 'SIX!', number: 6 }}
        onSelectNumber={vi.fn()}
      />
    );

    expect(screen.getByText('SIX!')).toBeDefined();
  });

  it('PitchArena displays WICKET celebration overlay with out batsman', () => {
    render(
      <PitchArena
        matchState={mockMatchState}
        selectedNumber={null}
        isWaiting={false}
        eventFeedback={{
          type: 'WICKET',
          runs: 0,
          title: 'WICKET!',
          subtitle: 'Rohit Sharma is out!',
        }}
        onSelectNumber={vi.fn()}
      />
    );

    expect(screen.getByText('WICKET!')).toBeDefined();
    expect(screen.getByText('Rohit Sharma is out!')).toBeDefined();
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

  it('MatchResultModal renders Win result and Play Again action', () => {
    const winState: MatchState = {
      ...mockMatchState,
      status: 'COMPLETED',
      winner: 'India',
      innings_1_score: 58,
      innings_1_wickets: 4,
      innings_2_score: 52,
      innings_2_wickets: 5,
      result_description: 'India won by 6 runs.',
    };
    const handlePlayAgain = vi.fn();
    render(<MatchResultModal matchState={winState} onPlayAgain={handlePlayAgain} />);

    expect(screen.getByText('India Win!')).toBeDefined();
    expect(screen.getByText('India won by 6 runs.')).toBeDefined();

    const playBtn = screen.getByText('Play Again');
    fireEvent.click(playBtn);
    expect(handlePlayAgain).toHaveBeenCalledTimes(1);
  });

  it('MatchResultModal renders Tie result', () => {
    const tieState: MatchState = {
      ...mockMatchState,
      status: 'COMPLETED',
      winner: null,
      is_tie: true,
      innings_1_score: 60,
      innings_1_wickets: 5,
      innings_2_score: 60,
      innings_2_wickets: 5,
      result_description: 'Match tied.',
    };
    render(<MatchResultModal matchState={tieState} onPlayAgain={vi.fn()} />);

    expect(screen.getByText("It's a Tie!")).toBeDefined();
    expect(screen.getByText('Match tied.')).toBeDefined();
  });
});
