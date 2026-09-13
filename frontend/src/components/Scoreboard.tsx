import React from 'react';
import { MatchState } from '../types';

interface ScoreboardProps {
  matchState: MatchState | null;
}

// 1. CIRCULAR SVG TEAM FLAGS (IND & AUS + Fallback)
const IndiaFlag: React.FC = () => (
  <svg viewBox="0 0 36 36" className="w-9 h-9 sm:w-11 sm:h-11 rounded-full shadow-md border-2 border-white/20 shrink-0">
    <clipPath id="circle-clip-ind">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#circle-clip-ind)">
      {/* Saffron */}
      <rect x="0" y="0" width="36" height="12" fill="#FF9933" />
      {/* White */}
      <rect x="0" y="12" width="36" height="12" fill="#FFFFFF" />
      {/* Green */}
      <rect x="0" y="24" width="36" height="12" fill="#138808" />
      {/* Ashoka Chakra */}
      <circle cx="18" cy="18" r="4.2" fill="none" stroke="#000080" strokeWidth="0.9" />
      <circle cx="18" cy="18" r="0.9" fill="#000080" />
      {Array.from({ length: 8 }).map((_, i) => (
        <line
          key={i}
          x1="18"
          y1="18"
          x2={18 + 4.2 * Math.cos((i * Math.PI) / 4)}
          y2={18 + 4.2 * Math.sin((i * Math.PI) / 4)}
          stroke="#000080"
          strokeWidth="0.6"
        />
      ))}
    </g>
  </svg>
);

const AustraliaFlag: React.FC = () => (
  <svg viewBox="0 0 36 36" className="w-9 h-9 sm:w-11 sm:h-11 rounded-full shadow-md border-2 border-white/20 shrink-0">
    <clipPath id="circle-clip-aus">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#circle-clip-aus)">
      {/* Blue Ensign */}
      <rect x="0" y="0" width="36" height="36" fill="#00008B" />
      {/* Union Jack Canton */}
      <rect x="0" y="0" width="18" height="18" fill="#00247D" />
      {/* White Saltire */}
      <line x1="0" y1="0" x2="18" y2="18" stroke="#FFFFFF" strokeWidth="2.5" />
      <line x1="18" y1="0" x2="0" y2="18" stroke="#FFFFFF" strokeWidth="2.5" />
      {/* Red Saltire */}
      <line x1="0" y1="0" x2="18" y2="18" stroke="#CF142B" strokeWidth="1.2" />
      <line x1="18" y1="0" x2="0" y2="18" stroke="#CF142B" strokeWidth="1.2" />
      {/* White Cross */}
      <line x1="9" y1="0" x2="9" y2="18" stroke="#FFFFFF" strokeWidth="3.5" />
      <line x1="0" y1="9" x2="18" y2="9" stroke="#FFFFFF" strokeWidth="3.5" />
      {/* Red Cross */}
      <line x1="9" y1="0" x2="9" y2="18" stroke="#CF142B" strokeWidth="1.8" />
      <line x1="0" y1="9" x2="18" y2="9" stroke="#CF142B" strokeWidth="1.8" />
      {/* Southern Cross stars */}
      <circle cx="28" cy="8" r="1.2" fill="#FFFFFF" />
      <circle cx="23" cy="13" r="1.2" fill="#FFFFFF" />
      <circle cx="31" cy="15" r="1.2" fill="#FFFFFF" />
      <circle cx="28" cy="22" r="1.5" fill="#FFFFFF" />
      <circle cx="25" cy="29" r="1.7" fill="#FFFFFF" />
    </g>
  </svg>
);

const EnglandFlag: React.FC = () => (
  <svg viewBox="0 0 36 36" className="w-9 h-9 sm:w-11 sm:h-11 rounded-full shadow-md border-2 border-white/20 shrink-0">
    <clipPath id="circle-clip-eng">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#circle-clip-eng)">
      <rect x="0" y="0" width="36" height="36" fill="#FFFFFF" />
      {/* Red St George Cross */}
      <rect x="15" y="0" width="6" height="36" fill="#CF142B" />
      <rect x="0" y="15" width="36" height="6" fill="#CF142B" />
    </g>
  </svg>
);

const SouthAfricaFlag: React.FC = () => (
  <svg viewBox="0 0 36 36" className="w-9 h-9 sm:w-11 sm:h-11 rounded-full shadow-md border-2 border-white/20 shrink-0">
    <clipPath id="circle-clip-sa">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#circle-clip-sa)">
      {/* Top red, bottom blue */}
      <rect x="0" y="0" width="36" height="18" fill="#E03C31" />
      <rect x="0" y="18" width="36" height="18" fill="#001489" />
      {/* White background for Y shape */}
      <polygon points="0,0 16,18 0,36 6,36 22,18 6,0" fill="#FFFFFF" />
      <rect x="16" y="14" width="20" height="8" fill="#FFFFFF" />
      {/* Green Y-shape */}
      <polygon points="0,2 14,18 0,34 4,34 18,18 4,2" fill="#007749" />
      <rect x="16" y="15.5" width="20" height="5" fill="#007749" />
      {/* Yellow/Gold chevron */}
      <polygon points="0,5 11,18 0,31" fill="#FFB81C" />
      {/* Black triangle */}
      <polygon points="0,8 8,18 0,28" fill="#000000" />
    </g>
  </svg>
);

const TeamFlagBadge: React.FC<{ id: string; name: string }> = ({ id }) => {
  if (id === 'IND') return <IndiaFlag />;
  if (id === 'AUS') return <AustraliaFlag />;
  if (id === 'ENG') return <EnglandFlag />;
  if (id === 'SA') return <SouthAfricaFlag />;
  return (
    <div className="w-9 h-9 sm:w-11 sm:h-11 rounded-full bg-gradient-to-br from-blue-600 to-indigo-800 border-2 border-white/20 flex items-center justify-center font-black text-xs text-white shadow-md shrink-0">
      {id.slice(0, 3)}
    </div>
  );
};

export const Scoreboard: React.FC<ScoreboardProps> = ({ matchState }) => {
  if (!matchState) {
    return null;
  }

  const {
    user_team,
    opponent_team,
    user_is_batting,
    score,
    wickets,
    overs,
    max_overs,
    target,
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

        let bgClass = 'bg-blue-600 text-white font-bold border border-blue-400';
        if (isWicket) bgClass = 'bg-red-600 text-white font-black border border-red-500';
        else if (isSix) bgClass = 'bg-gradient-to-r from-amber-400 to-yellow-300 text-slate-950 font-black';
        else if (isFour) bgClass = 'bg-amber-400 text-slate-950 font-black';
        else if (ball === 0) bgClass = 'bg-slate-800 text-slate-400 font-medium border border-slate-700';

        dots.push(
          <span
            key={i}
            className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] shadow-sm ${bgClass}`}
          >
            {ball}
          </span>
        );
      } else {
        dots.push(
          <span
            key={i}
            className="w-2.5 h-2.5 rounded-full bg-slate-800 border border-slate-700/80"
          />
        );
      }
    }
    return dots;
  };

  // Batters block: Runs and balls faced
  const renderBatters = () => (
    <div className="flex items-center space-x-3 sm:space-x-4 text-xs font-semibold">
      {/* Striker */}
      <div className="flex flex-col text-left">
        <span className="text-amber-400 text-[9px] uppercase font-black tracking-wider">
          Striker
        </span>
        <span className="font-extrabold text-white flex items-center">
          <span className="truncate max-w-[85px] sm:max-w-[105px]">{striker.name || 'Batter 1'}</span>
          <span className="text-amber-400 ml-0.5">*</span>
        </span>
        <span className="text-amber-300 text-xs sm:text-sm font-black">
          {striker.runs} ({striker.balls})
        </span>
      </div>

      {/* Non-Striker */}
      <div className="flex flex-col text-left">
        <span className="text-slate-400 text-[9px] uppercase font-bold tracking-wider">
          Non-Striker
        </span>
        <span className="font-bold text-slate-200 truncate max-w-[85px] sm:max-w-[105px]">
          {non_striker.name || 'Batter 2'}
        </span>
        <span className="text-slate-300 text-xs sm:text-sm font-bold">
          {non_striker.runs} ({non_striker.balls})
        </span>
      </div>
    </div>
  );

  // Bowler block
  const renderBowler = () => (
    <div className="flex flex-col text-left text-xs min-w-[90px] sm:min-w-[105px]">
      <span className="text-slate-400 text-[9px] uppercase font-bold tracking-wider">
        Bowler
      </span>
      <span className="font-bold text-white truncate max-w-[100px] sm:max-w-[120px]">
        {bowler.name || 'Bowler'}
      </span>
      <span className="text-amber-300 text-xs sm:text-sm font-black">
        {bowler.figures}
      </span>
    </div>
  );

  // Calculate remaining balls and runs if target is active
  const targetRuns = target !== null ? target - score : null;
  const currentOverFloat = parseFloat(overs) || 0;
  const completedBalls = Math.floor(currentOverFloat) * 6 + Math.round((currentOverFloat % 1) * 10);
  const totalBalls = max_overs * 6;
  const remainingBalls = Math.max(0, totalBalls - completedBalls);

  return (
    <div className="w-full max-w-4xl px-2 pb-2 sm:pb-3 z-20">
      <div className="bg-slate-950/85 backdrop-blur-xl border border-white/10 rounded-2xl sm:rounded-3xl shadow-2xl p-2.5 sm:p-3.5 text-white">
        {/* DESKTOP & TABLET SINGLE-ROW SCOREBOARD (sm and up) */}
        <div className="hidden sm:flex items-center justify-between gap-3 md:gap-5">
          {/* USER SIDE (Left) */}
          <div className="flex items-center space-x-3">
            {/* User Flag and Details */}
            <div className="flex items-center space-x-2.5">
              <TeamFlagBadge id={user_team.id} name={user_team.name} />
              <div className="text-left">
                <div className="text-xs font-black tracking-wide text-white uppercase truncate max-w-[85px]">
                  {user_team.name}
                </div>
                <div className="flex items-center space-x-1 mt-0.5">
                  <span className="text-[10px] text-slate-300 font-semibold">You</span>
                  <span
                    className={`text-[9px] font-black uppercase px-1.5 py-0.2 rounded-full ${
                      user_is_batting
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        : 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                    }`}
                  >
                    {user_is_batting ? 'Batting' : 'Bowling'}
                  </span>
                </div>
              </div>
            </div>

            {/* Left Player Stats: Batters if User is batting; Bowler if User is bowling */}
            <div className="pl-3 border-l border-white/10">
              {user_is_batting ? renderBatters() : renderBowler()}
            </div>
          </div>

          {/* CENTER AUTHORITATIVE SCORE BADGE (YELLOW BADGE MATCHING REFERENCE SPEC) */}
          <div className="flex flex-col items-center justify-center bg-gradient-to-b from-amber-400 via-yellow-400 to-amber-500 text-slate-950 font-black px-5 py-1.5 rounded-xl shadow-lg shadow-amber-500/20 min-w-[95px]">
            <span className="text-lg sm:text-xl tracking-tight leading-none font-black">
              {score}-{wickets}
            </span>
            <span className="text-[10px] font-extrabold text-slate-900 mt-0.5">
              ({overs} ov)
            </span>
          </div>

          {/* OPPONENT SIDE (Right) */}
          <div className="flex items-center space-x-3 justify-end">
            {/* Right Player Stats: Bowler if User is batting; Batters if Computer is batting */}
            <div className="pr-3 border-r border-white/10">
              {user_is_batting ? renderBowler() : renderBatters()}
            </div>

            {/* Opponent Details and Flag */}
            <div className="flex items-center space-x-2.5">
              <div className="text-right">
                <div className="text-xs font-black tracking-wide text-white uppercase truncate max-w-[85px]">
                  {opponent_team.name}
                </div>
                <div className="flex items-center justify-end space-x-1 mt-0.5">
                  <span
                    className={`text-[9px] font-black uppercase px-1.5 py-0.2 rounded-full ${
                      !user_is_batting
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        : 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                    }`}
                  >
                    {!user_is_batting ? 'Batting' : 'Bowling'}
                  </span>
                  <span className="text-[10px] text-slate-300 font-semibold">Comp</span>
                </div>
              </div>
              <TeamFlagBadge id={opponent_team.id} name={opponent_team.name} />
            </div>
          </div>
        </div>

        {/* MOBILE STACKED SCOREBOARD (screens < 640px) */}
        <div className="flex flex-col space-y-1.5 sm:hidden text-xs">
          {/* Top Row: Teams and Score Badge */}
          <div className="flex items-center justify-between">
            {/* User Team */}
            <div className="flex items-center space-x-1.5">
              <TeamFlagBadge id={user_team.id} name={user_team.name} />
              <div>
                <span className="font-black text-white text-xs block leading-tight">{user_team.name}</span>
                <span className="text-[8px] uppercase px-1 rounded bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                  {user_is_batting ? 'BAT' : 'BOWL'}
                </span>
              </div>
            </div>

            {/* Central Score Badge */}
            <div className="flex items-center space-x-1.5 bg-gradient-to-b from-amber-400 to-amber-500 text-slate-950 font-black px-3 py-1 rounded-xl shadow-md">
              <span className="text-sm font-black">{score}-{wickets}</span>
              <span className="text-[10px] text-slate-900 font-bold">({overs})</span>
            </div>

            {/* Opponent Team */}
            <div className="flex items-center space-x-1.5">
              <div className="text-right">
                <span className="font-black text-white text-xs block leading-tight">{opponent_team.name}</span>
                <span className="text-[8px] uppercase px-1 rounded bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                  {!user_is_batting ? 'BAT' : 'BOWL'}
                </span>
              </div>
              <TeamFlagBadge id={opponent_team.id} name={opponent_team.name} />
            </div>
          </div>

          {/* Middle Row: Batters / Bowler */}
          <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/10 text-[11px]">
            {/* Left Col */}
            <div className="flex flex-col text-left">
              {user_is_batting ? (
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-white font-bold truncate max-w-[85px]">{striker.name}*</span>
                    <span className="text-amber-300 font-black">{striker.runs} ({striker.balls})</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-300 text-[10px]">
                    <span className="truncate max-w-[85px]">{non_striker.name}</span>
                    <span className="font-bold">{non_striker.runs} ({non_striker.balls})</span>
                  </div>
                </div>
              ) : (
                <div>
                  <span className="text-[9px] uppercase font-bold text-slate-400">Bowler</span>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200 truncate">{bowler.name}</span>
                    <span className="text-amber-300 font-black text-[10px]">{bowler.figures}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Right Col */}
            <div className="flex flex-col text-right pl-2 border-l border-white/10">
              {!user_is_batting ? (
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-white font-bold truncate max-w-[85px]">{striker.name}*</span>
                    <span className="text-amber-300 font-black">{striker.runs} ({striker.balls})</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-300 text-[10px]">
                    <span className="truncate max-w-[85px]">{non_striker.name}</span>
                    <span className="font-bold">{non_striker.runs} ({non_striker.balls})</span>
                  </div>
                </div>
              ) : (
                <div>
                  <span className="text-[9px] uppercase font-bold text-slate-400">Bowler</span>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200 truncate">{bowler.name}</span>
                    <span className="text-amber-300 font-black text-[10px]">{bowler.figures}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* BOTTOM SUB-ROW: Target / Situation + Current Over Indicators */}
        <div className="flex items-center justify-between pt-1.5 mt-1 sm:mt-1.5 border-t border-white/10 text-[10px] sm:text-xs">
          {/* Situation / Target */}
          <div className="text-slate-300 font-bold truncate max-w-[60%] text-left">
            {target !== null && targetRuns !== null ? (
              <span className="text-amber-300 font-extrabold">
                Need {Math.max(1, targetRuns)} in {remainingBalls} balls
              </span>
            ) : (
              <span className="text-slate-400 font-medium">1st Innings</span>
            )}
          </div>

          {/* Current Over Ball Indicators */}
          <div className="flex items-center space-x-1 sm:space-x-1.5">
            <span className="text-[9px] sm:text-[10px] uppercase font-bold text-slate-400 tracking-wider mr-1">
              This Over:
            </span>
            {renderBallIndicators()}
          </div>
        </div>
      </div>
    </div>
  );
};
