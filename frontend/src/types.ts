/**
 * Hand Cricket Frontend Types (Slice 12)
 */

export interface TeamInfo {
  id: string;
  name: string;
}

export interface PlayerStat {
  id?: number;
  name: string;
  runs: number;
  balls: number;
}

export interface BowlerStat {
  id?: number;
  name: string;
  overs: string;
  runs: number;
  wickets: number;
  figures: string;
}

export interface LastBallInfo {
  batsman_choice: number;
  bowler_choice: number;
  runs: number;
  is_wicket: boolean;
  user_choice: number;
  computer_choice: number;
  user_timed_out: boolean;
  event: 'NORMAL' | 'FOUR' | 'SIX' | 'WICKET';
  out_player: string | null;
}

export interface MatchState {
  status: 'INNINGS_1' | 'INNINGS_BREAK' | 'INNINGS_2' | 'COMPLETED';
  innings: 1 | 2;
  user_team: TeamInfo;
  opponent_team: TeamInfo;
  batting_team: string;
  bowling_team: string;
  user_is_batting: boolean;
  score: number;
  wickets: number;
  overs: string;
  max_overs: number;
  target: number | null;
  striker: PlayerStat;
  non_striker: PlayerStat;
  bowler: BowlerStat;
  current_over_balls: (number | string)[];
  innings_1_score: number | null;
  innings_1_wickets: number | null;
  innings_2_score: number | null;
  innings_2_wickets: number | null;
  last_ball: LastBallInfo | null;
  winner: string | null;
  is_tie: boolean;
  result_description: string | null;
  turn_id?: number;
}

export interface EventFeedback {
  type: 'FOUR' | 'SIX' | 'WICKET' | 'NORMAL';
  runs: number;
  title: string;
  subtitle?: string;
  number?: number;
  batsmanChoice?: number;
  userChoice?: number;
  computerChoice?: number;
  userTimedOut?: boolean;
}

export interface MilestoneFeedback {
  batsmanName: string;
  milestone: 50 | 100;
  label: 'FIFTY!' | 'CENTURY!';
}

export type AppStage = 'LANDING' | 'PRE_MATCH' | 'IN_MATCH';

export type PreMatchStage =
  | 'TEAM_SELECTION'
  | 'TOSS_DECISION'
  | 'TOSS_RESULT'
  | 'BOWLER_SELECTION'
  | 'MATCH_READY';

export interface TeamRosterPlayer {
  id: number;
  name: string;
}

export interface TeamRoster {
  id: string;
  name: string;
  players: TeamRosterPlayer[];
}

export interface PreMatchState {
  stage: PreMatchStage;
  available_teams: TeamRoster[];
  user_team: TeamInfo | null;
  opponent_team: TeamInfo | null;
  toss_winner: 'user' | 'computer' | null;
  toss_decision: 'BAT' | 'BOWL' | null;
  batting_first: 'user' | 'computer' | null;
  bowling_first: 'user' | 'computer' | null;
  first_bowler_selector: 'user' | 'computer' | null;
  eligible_bowlers?: TeamRosterPlayer[];
  used_bowlers?: TeamRosterPlayer[];
  current_over?: number;
}

export interface BowlerSelectionPrompt {
  current_over: number;
  eligible_bowlers: TeamRosterPlayer[];
  used_bowlers: TeamRosterPlayer[];
  match_state?: MatchState;
}

