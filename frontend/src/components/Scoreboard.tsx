import React from 'react';
import { MatchState } from '../types';

interface ScoreboardProps {
  matchState: MatchState | null;
}

export const Scoreboard: React.FC<ScoreboardProps> = ({ matchState }) => {
  if (!matchState) {
    return null;
  }

  const {
    user_team,
    opponent_team,
    score,
    wickets,
    overs,
    striker,
    non_striker,
    bowler,
    current_over_balls,
  } = matchState;

  // Render over ball dots (up to 6 balls)
  const renderBallIndicators = () => {
    const dots = [];
    const maxBalls = 6;
    for (let i = 0; i < maxBalls; i++) {
      const ball = current_over_balls[i];
      if (ball !== undefined) {
        const isWicket = ball === 'W';
        const isFour = ball === 4;
        const isSix = ball === 6;

        let bgClass = 'bg-sky-500 text-white';
        if (isWicket) bgClass = 'bg-red-500 text-white font-black';
        else if (isSix) bgClass = 'bg-amber-400 text-slate-950 font-black';
        else if (isFour) bgClass = 'bg-blue-600 text-white font-black';

        dots.push(
          <span
            key={i}
            className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shadow-sm ${bgClass}`}
          >
            {ball}
          </span>
        );
      } else {
        dots.push(
          <span
            key={i}
            className="w-2.5 h-2.5 rounded-full bg-slate-700/80 border border-slate-600/50"
          />
        );
      }
    }
    return dots;
  };

  return (
    <div className="w-full max-w-4xl px-2 pb-2 sm:pb-3 z-20">
      <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 rounded-2xl shadow-2xl p-2 sm:p-3 text-white">
        {/* DESKTOP & TABLET SINGLE-ROW SCOREBOARD (sm and up) */}
        <div className="hidden sm:flex items-center justify-between gap-2 md:gap-4">
          {/* User Team Badge */}
          <div className="flex items-center space-x-2 min-w-[110px]">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-800 flex items-center justify-center font-black text-sm text-white shadow-md border border-blue-400/40">
              {user_team.id}
            </div>
            <div className="text-left">
              <div className="text-xs font-black tracking-wide text-white uppercase truncate max-w-[80px]">
                {user_team.name}
              </div>
              <div className="text-[10px] text-sky-300 font-semibold">User</div>
            </div>
          </div>

          {/* Yellow Score Box */}
          <div className="flex flex-col items-center justify-center bg-gradient-to-b from-amber-300 to-amber-400 text-slate-950 font-black px-3 py-1 rounded-xl shadow-md min-w-[75px]">
            <span className="text-base tracking-tight leading-none">
              {score}-{wickets}
            </span>
            <span className="text-[10px] font-bold text-slate-800 mt-0.5">
              ({overs})
            </span>
          </div>

          {/* Batters Details */}
          <div className="flex items-center space-x-4 text-xs font-semibold">
            {/* Striker */}
            <div className="flex flex-col text-left">
              <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider">
                Striker
              </span>
              <span className="font-extrabold text-amber-300 flex items-center">
                <span className="truncate max-w-[95px]">{striker.name || 'Batter 1'}</span>
                <span className="text-amber-400 ml-0.5">*</span>
              </span>
              <span className="text-slate-200 text-[11px] font-bold">
                {striker.runs} ({striker.balls})
              </span>
            </div>

            {/* Non-Striker */}
            <div className="flex flex-col text-left">
              <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider">
                Non-Striker
              </span>
              <span className="font-bold text-slate-300 truncate max-w-[95px]">
                {non_striker.name || 'Batter 2'}
              </span>
              <span className="text-slate-300 text-[11px]">
                {non_striker.runs} ({non_striker.balls})
              </span>
            </div>
          </div>

          {/* Bowler Details */}
          <div className="flex flex-col text-left text-xs min-w-[100px]">
            <span className="text-slate-400 text-[10px] uppercase font-bold tracking-wider">
              Bowler
            </span>
            <span className="font-bold text-sky-300 truncate max-w-[110px]">
              {bowler.name || 'Bowler'}
            </span>
            <span className="text-slate-300 text-[11px] font-medium">
              {bowler.figures}
            </span>
          </div>

          {/* Opponent Team Badge */}
          <div className="flex items-center space-x-2 min-w-[110px] justify-end">
            <div className="text-right">
              <div className="text-xs font-black tracking-wide text-white uppercase truncate max-w-[80px]">
                {opponent_team.name}
              </div>
              <div className="text-[10px] text-amber-300 font-semibold">Computer</div>
            </div>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-500 to-orange-700 flex items-center justify-center font-black text-sm text-slate-950 shadow-md border border-amber-300/40">
              {opponent_team.id}
            </div>
          </div>
        </div>

        {/* MOBILE STACKED COMPACT SCOREBOARD (screens < 640px) */}
        <div className="flex flex-col space-y-1.5 sm:hidden text-xs">
          {/* Top Row: Teams and Big Score Box */}
          <div className="flex items-center justify-between">
            {/* User Team */}
            <div className="flex items-center space-x-1.5">
              <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center font-black text-xs text-white">
                {user_team.id}
              </div>
              <span className="font-bold text-white text-xs">{user_team.name}</span>
            </div>

            {/* Score Pill */}
            <div className="flex items-center space-x-1.5 bg-amber-400 text-slate-950 font-black px-2.5 py-0.5 rounded-lg shadow-sm">
              <span className="text-sm">{score}-{wickets}</span>
              <span className="text-[10px] text-slate-800">({overs})</span>
            </div>

            {/* Opponent Team */}
            <div className="flex items-center space-x-1.5">
              <span className="font-bold text-white text-xs">{opponent_team.name}</span>
              <div className="w-7 h-7 rounded-lg bg-amber-500 flex items-center justify-center font-black text-xs text-slate-950">
                {opponent_team.id}
              </div>
            </div>
          </div>

          {/* Middle Row: Batters and Bowler */}
          <div className="grid grid-cols-3 gap-1 pt-1 border-t border-slate-800 text-[11px]">
            {/* Striker */}
            <div className="flex flex-col text-left">
              <span className="text-amber-300 font-bold truncate">
                {striker.name}*
              </span>
              <span className="text-slate-300 font-medium">
                {striker.runs} ({striker.balls})
              </span>
            </div>

            {/* Non-Striker */}
            <div className="flex flex-col text-left">
              <span className="text-slate-300 truncate">
                {non_striker.name}
              </span>
              <span className="text-slate-400 font-medium">
                {non_striker.runs} ({non_striker.balls})
              </span>
            </div>

            {/* Bowler */}
            <div className="flex flex-col text-right">
              <span className="text-sky-300 font-bold truncate">
                {bowler.name}
              </span>
              <span className="text-slate-300 font-medium text-[10px]">
                {bowler.figures}
              </span>
            </div>
          </div>
        </div>

        {/* BOTTOM ROW: Current Over Ball Indicators */}
        <div className="flex items-center justify-center space-x-2 pt-1.5 mt-1 sm:mt-1.5 border-t border-slate-800/80">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mr-1">
            This Over:
          </span>
          <div className="flex items-center space-x-1.5">
            {renderBallIndicators()}
          </div>
        </div>
      </div>
    </div>
  );
};
