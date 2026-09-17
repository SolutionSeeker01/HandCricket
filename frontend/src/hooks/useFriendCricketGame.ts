import { useCallback, useEffect, useRef, useState } from 'react';
import {
  BowlerSelectionPrompt,
  ConnectionStatus,
  EventFeedback,
  MatchState,
  MilestoneFeedback,
  TurnCountdown,
} from '../types';
import { soundManager } from '../utils/sound';

interface UseFriendCricketGameProps {
  roomCode: string | null;
  playerToken: string | null;
  participantSeat: 'A' | 'B' | null;
  onLeave: () => void;
}

export function useFriendCricketGame({
  roomCode,
  playerToken,
  participantSeat,
  onLeave,
}: UseFriendCricketGameProps) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  const [stage, setStage] = useState<string>('WAITING_FOR_PLAYER');
  const [participant, setParticipant] = useState<'A' | 'B' | null>(participantSeat);
  const [userTeam, setUserTeam] = useState<any>(null);
  const [opponentTeam, setOpponentTeam] = useState<any>(null);
  const userTeamRef = useRef<any>(null);
  const opponentTeamRef = useRef<any>(null);
  const [tossWinner, setTossWinner] = useState<'A' | 'B' | null>(null);
  const [tossDecision, setTossDecision] = useState<'BAT' | 'BOWL' | null>(null);
  const [bowlerSelector, setBowlerSelector] = useState<'A' | 'B' | null>(null);
  const [bowlerSelectionPrompt, setBowlerSelectionPrompt] = useState<BowlerSelectionPrompt | null>(null);
  const [matchState, setMatchState] = useState<MatchState | null>(null);

  // Turn gameplay states
  const [currentTurnId, setCurrentTurnId] = useState<number | null>(null);
  const [selectedNumber, setSelectedNumber] = useState<number | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState<boolean>(false);
  const [opponentSubmitted, setOpponentSubmitted] = useState<boolean>(false);
  const [eventFeedback, setEventFeedback] = useState<EventFeedback | null>(null);
  const [milestoneFeedback, setMilestoneFeedback] = useState<MilestoneFeedback | null>(null);
  const [turnCountdown, setTurnCountdown] = useState<TurnCountdown | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [opponentDisconnected, setOpponentDisconnected] = useState<boolean>(false);
  const [opponentGraceSeconds, setOpponentGraceSeconds] = useState<number>(60);
  const [inningsBreakReady, setInningsBreakReady] = useState<boolean>(false);
  const [rematchRequested, setRematchRequested] = useState<boolean>(false);
  const [opponentRematchRequested, setOpponentRematchRequested] = useState<boolean>(false);

  const socketRef = useRef<WebSocket | null>(null);
  const countdownIntervalRef = useRef<number | null>(null);
  const turnStartTimeRef = useRef<number | null>(null);
  const turnTotalSecondsRef = useRef<number>(10);
  const feedbackTimeoutRef = useRef<number | null>(null);
  const milestoneTimeoutRef = useRef<number | null>(null);
  const prevPlayerScoresRef = useRef<Record<string, number>>({});
  const celebratedMilestonesRef = useRef<Set<string>>(new Set());
  const reconnectAttemptRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const isUnmountedRef = useRef<boolean>(false);
  const isStartingInningsRef = useRef<boolean>(false);
  const lastUrgentSecondRef = useRef<number | null>(null);

  const stopCountdown = useCallback(() => {
    if (countdownIntervalRef.current) {
      window.clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
    setTurnCountdown(null);
  }, []);

  const startCountdown = useCallback((totalSeconds: number = 10) => {
    stopCountdown();
    lastUrgentSecondRef.current = null;
    turnStartTimeRef.current = Date.now();
    turnTotalSecondsRef.current = totalSeconds;

    setTurnCountdown({
      remainingSeconds: totalSeconds,
      totalSeconds,
      isUrgent: false,
    });

    countdownIntervalRef.current = window.setInterval(() => {
      if (!turnStartTimeRef.current) return;
      const elapsed = (Date.now() - turnStartTimeRef.current) / 1000;
      const remaining = Math.max(0, turnTotalSecondsRef.current - elapsed);
      const roundedCeil = Math.ceil(remaining);
      const isUrgent = remaining <= 3.0 && remaining > 0;

      if (isUrgent && lastUrgentSecondRef.current !== roundedCeil) {
        lastUrgentSecondRef.current = roundedCeil;
        soundManager.playTimerWarning(roundedCeil);
      }

      setTurnCountdown({
        remainingSeconds: roundedCeil,
        totalSeconds: turnTotalSecondsRef.current,
        isUrgent,
      });

      if (remaining <= 0) {
        stopCountdown();
      }
    }, 100);
  }, [stopCountdown]);

  // Connect WebSocket with reconnection backoff
  useEffect(() => {
    if (!roomCode || !playerToken) return;

    isUnmountedRef.current = false;

    const connectWs = () => {
      if (isUnmountedRef.current) return;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host =
        window.location.port === '5173'
          ? `${window.location.hostname || '127.0.0.1'}:8000`
          : (window.location.host || 'localhost:8000');
      const wsUrl = `${protocol}//${host}/ws/friend?room=${roomCode}&token=${playerToken}`;

      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      if (reconnectAttemptRef.current === 0) {
        setConnectionStatus('connecting');
      }

      ws.onopen = () => {
        if (isUnmountedRef.current) {
          ws.close();
          return;
        }
        reconnectAttemptRef.current = 0;
        setConnectionStatus('connected');
        setErrorMessage(null);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleServerMessage(msg);
        } catch (e) {
          console.error('Failed to parse WebSocket message', e);
        }
      };

      ws.onerror = () => {
        if (socketRef.current === ws) {
          setConnectionStatus('error');
          setErrorMessage('Connection error.');
        }
      };

      ws.onclose = () => {
        if (isUnmountedRef.current) return;
        if (socketRef.current === ws) {
          stopCountdown();
          if (reconnectAttemptRef.current < 6) {
            setConnectionStatus('reconnecting');
            const delay = Math.min(1000 * Math.pow(1.5, reconnectAttemptRef.current), 4000);
            reconnectAttemptRef.current += 1;
            reconnectTimeoutRef.current = window.setTimeout(connectWs, delay);
          } else {
            setConnectionStatus('disconnected');
          }
        }
      };
    };

    connectWs();

    return () => {
      isUnmountedRef.current = true;
      stopCountdown();
      if (feedbackTimeoutRef.current) window.clearTimeout(feedbackTimeoutRef.current);
      if (milestoneTimeoutRef.current) window.clearTimeout(milestoneTimeoutRef.current);
      if (reconnectTimeoutRef.current) window.clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [roomCode, playerToken]);

  const handleServerMessage = (msg: any) => {
    switch (msg.type) {
      case 'room_joined':
        setParticipant(msg.participant);
        setStage(msg.stage);
        break;

      case 'sync_state': {
        setParticipant(msg.participant);
        setStage(msg.stage);
        setConnectionStatus('connected');

        if (msg.opponent_connected !== undefined) {
          setOpponentDisconnected(!msg.opponent_connected);
        }

        // Restore team selection if present
        const restoredUserTeam = msg.user_team || msg.match_state?.user_team;
        if (restoredUserTeam) {
          setUserTeam(restoredUserTeam);
          userTeamRef.current = restoredUserTeam;
        }
        const restoredOpponentTeam = msg.opponent_team || msg.match_state?.opponent_team;
        if (restoredOpponentTeam) {
          setOpponentTeam(restoredOpponentTeam);
          opponentTeamRef.current = restoredOpponentTeam;
        }
        if (msg.toss_winner) {
          setTossWinner(msg.toss_winner);
        }
        if (msg.toss_decision) {
          setTossDecision(msg.toss_decision);
        }

        // Restore match state
        if (msg.match_state && Object.keys(msg.match_state).length > 0) {
          const userIsBatting = (msg.match_state.batting_participant ?? msg.batting_participant) !== undefined
            ? (msg.match_state.batting_participant ?? msg.batting_participant) === participant
            : Boolean(msg.match_state.user_is_batting);
          const resolvedUserTeam = userTeamRef.current ?? msg.match_state.user_team ?? (userIsBatting ? msg.match_state.batting_team : msg.match_state.bowling_team);
          const resolvedOpponentTeam = opponentTeamRef.current ?? msg.match_state.opponent_team ?? (userIsBatting ? msg.match_state.bowling_team : msg.match_state.batting_team);
          setMatchState({
            ...msg.match_state,
            user_is_batting: userIsBatting,
            user_team: resolvedUserTeam,
            opponent_team: resolvedOpponentTeam,
          });
        }

        // Restore turn state
        if (msg.current_turn_id) {
          setCurrentTurnId(msg.current_turn_id);
          setHasSubmitted(Boolean(msg.has_submitted));
          setOpponentSubmitted(Boolean(msg.opponent_submitted));

          if (msg.turn_remaining_seconds > 0) {
            startCountdown(msg.turn_remaining_seconds);
          } else {
            stopCountdown();
          }
        } else {
          stopCountdown();
        }

        // Restore bowler selection prompt if in that stage
        if (msg.bowler_selection_prompt) {
          setBowlerSelector(msg.bowler_selection_prompt.bowler_selector);
          setBowlerSelectionPrompt({
            current_over: msg.bowler_selection_prompt.current_over,
            eligible_bowlers: msg.bowler_selection_prompt.eligible_bowlers || [],
            used_bowlers: msg.bowler_selection_prompt.used_bowlers || [],
          });
        }

        // Restore innings break & rematch readiness
        if (Array.isArray(msg.innings_break_ready)) {
          setInningsBreakReady(msg.innings_break_ready.includes(participant));
        }
        if (Array.isArray(msg.rematch_ready)) {
          setRematchRequested(msg.rematch_ready.includes(participant));
          const opp = participant === 'A' ? 'B' : 'A';
          setOpponentRematchRequested(msg.rematch_ready.includes(opp));
        }
        break;
      }

      case 'player_disconnected':
        setOpponentDisconnected(true);
        setOpponentGraceSeconds(msg.grace_seconds || 60);
        break;

      case 'player_reconnected':
        setOpponentDisconnected(false);
        break;

      case 'player_joined':
      case 'stage_changed':
        setStage(msg.stage);
        break;

      case 'team_selected':
        if (msg.participant === participant) {
          const uTeam = { id: msg.team_id, name: msg.team_name };
          setUserTeam(uTeam);
          userTeamRef.current = uTeam;
        } else {
          const oTeam = { id: msg.team_id, name: msg.team_name };
          setOpponentTeam(oTeam);
          opponentTeamRef.current = oTeam;
        }
        break;

      case 'toss_result':
        soundManager.playCoinToss();
        soundManager.preloadAll();
        setTossWinner(msg.winner);
        setTossDecision(null);
        setBowlerSelector(null);
        setBowlerSelectionPrompt(null);
        setMatchState(null);
        setCurrentTurnId(null);
        setSelectedNumber(null);
        setHasSubmitted(false);
        setOpponentSubmitted(false);
        setEventFeedback(null);
        setMilestoneFeedback(null);
        setInningsBreakReady(false);
        setRematchRequested(false);
        setOpponentRematchRequested(false);
        prevPlayerScoresRef.current = {};
        celebratedMilestonesRef.current.clear();
        setStage('TOSS_DECISION');
        break;

      case 'toss_decision_result':
        setTossDecision(msg.decision);
        setBowlerSelector(msg.bowler_selector);
        setStage('BOWLER_SELECTION');
        setBowlerSelectionPrompt({
          current_over: msg.current_over || 1,
          eligible_bowlers: msg.eligible_bowlers || [],
          used_bowlers: msg.used_bowlers || [],
        });
        break;

      case 'match_started': {
        setStage('IN_MATCH');
        const ms = msg.match_state;
        const userIsBatting = msg.batting_participant === participant;
        const resolvedUserTeam = userTeamRef.current ?? (userIsBatting ? msg.batting_team : msg.bowling_team);
        const resolvedOpponentTeam = opponentTeamRef.current ?? (userIsBatting ? msg.bowling_team : msg.batting_team);
        setMatchState({
          ...ms,
          status: 'INNINGS_1',
          user_is_batting: userIsBatting,
          user_team: resolvedUserTeam,
          opponent_team: resolvedOpponentTeam,
        });
        break;
      }

      case 'turn_started':
        if (currentTurnId !== null && typeof msg.turn_id === 'number' && msg.turn_id < currentTurnId) {
          return;
        }
        setCurrentTurnId(msg.turn_id);
        setSelectedNumber(null);
        setHasSubmitted(false);
        setOpponentSubmitted(false);
        setInningsBreakReady(false);
        setStage('IN_MATCH');
        setBowlerSelectionPrompt(null);
        if (msg.match_state) {
          setMatchState((prev) => {
            if (!prev) return null;
            const isUserBatting = (msg.match_state.batting_participant ?? msg.batting_participant ?? prev.batting_participant) !== undefined
              ? (msg.match_state.batting_participant ?? msg.batting_participant ?? prev.batting_participant) === participant
              : prev.user_is_batting;
            return {
              ...prev,
              ...msg.match_state,
              user_is_batting: isUserBatting,
              user_team: userTeamRef.current ?? prev.user_team ?? msg.match_state.user_team,
              opponent_team: opponentTeamRef.current ?? prev.opponent_team ?? msg.match_state.opponent_team,
            };
          });
        }
        startCountdown(msg.timeout_seconds || 10);
        break;

      case 'number_submitted':
        if (msg.participant === participant) {
          setHasSubmitted(true);
        } else {
          setOpponentSubmitted(true);
        }
        break;

      case 'ball_result': {
        if (currentTurnId !== null && typeof msg.turn_id === 'number' && msg.turn_id < currentTurnId) {
          return;
        }
        stopCountdown();
        const runs = msg.runs;
        const isWicket = msg.is_wicket;
        const outPlayer = msg.out_player || msg.match_state?.last_ball?.out_player;

        // Feedback sound & animation
        let fbType: 'FOUR' | 'SIX' | 'WICKET' | 'NORMAL' = 'NORMAL';
        let title = '';
        let subtitle: string | undefined = undefined;
        if (isWicket) {
          fbType = 'WICKET';
          title = 'WICKET!';
          subtitle = outPlayer ? `${outPlayer} is out!` : 'Batter is out!';
          soundManager.playWicket();
        } else if (runs === 6) {
          fbType = 'SIX';
          title = 'SIX!';
          subtitle = '+6 RUNS';
          soundManager.playSix();
        } else if (runs === 4) {
          fbType = 'FOUR';
          title = 'FOUR!';
          subtitle = '+4 RUNS';
          soundManager.playFour();
        } else {
          fbType = 'NORMAL';
          title = runs === 0 ? 'DOT BALL' : `+${runs} ${runs === 1 ? 'RUN' : 'RUNS'}`;
          subtitle = runs === 0 ? '0 Runs scored' : `+${runs} Runs scored`;
          soundManager.playBatHit(runs);
        }

        // Check for 50 or 100 milestone on striker or non-striker
        let detectedMilestone: MilestoneFeedback | null = null;
        if (msg.match_state) {
          const playersToCheck = [msg.match_state.striker, msg.match_state.non_striker].filter(Boolean);
          for (const p of playersToCheck) {
            if (p && p.name) {
              const pKey = `${p.id ?? p.name}`;
              const prevRuns = prevPlayerScoresRef.current[pKey] ?? 0;
              const newRuns = p.runs;
              prevPlayerScoresRef.current[pKey] = newRuns;

              const fiftyKey = `${pKey}_50`;
              const centuryKey = `${pKey}_100`;

              if (prevRuns < 100 && newRuns >= 100 && !celebratedMilestonesRef.current.has(centuryKey)) {
                celebratedMilestonesRef.current.add(centuryKey);
                detectedMilestone = {
                  batsmanName: p.name,
                  milestone: 100,
                  label: 'CENTURY!',
                };
                break;
              } else if (prevRuns < 50 && newRuns >= 50 && !celebratedMilestonesRef.current.has(fiftyKey)) {
                celebratedMilestonesRef.current.add(fiftyKey);
                detectedMilestone = {
                  batsmanName: p.name,
                  milestone: 50,
                  label: 'FIFTY!',
                };
                break;
              }
            }
          }
        }

        const userTimedOut = participant === 'A' ? Boolean(msg.a_timed_out) : Boolean(msg.b_timed_out);

        setEventFeedback({
          type: fbType,
          runs,
          title,
          subtitle,
          number: runs,
          batsmanChoice: msg.batsman_choice,
          userChoice: participant === 'A' ? msg.choice_a : msg.choice_b,
          computerChoice: participant === 'A' ? msg.choice_b : msg.choice_a,
          userTimedOut,
        });

        if (detectedMilestone) {
          const milestoneToCelebrate = detectedMilestone;
          if (feedbackTimeoutRef.current) window.clearTimeout(feedbackTimeoutRef.current);
          feedbackTimeoutRef.current = window.setTimeout(() => {
            setEventFeedback(null);
          }, 1400);

          if (milestoneTimeoutRef.current) window.clearTimeout(milestoneTimeoutRef.current);
          milestoneTimeoutRef.current = window.setTimeout(() => {
            setMilestoneFeedback(milestoneToCelebrate);
            if (milestoneToCelebrate.milestone === 100) {
              soundManager.playCentury();
            } else if (milestoneToCelebrate.milestone === 50) {
              soundManager.playFifty();
            }
            milestoneTimeoutRef.current = window.setTimeout(() => {
              setMilestoneFeedback(null);
            }, 1500);
          }, 1400);
        } else {
          if (feedbackTimeoutRef.current) window.clearTimeout(feedbackTimeoutRef.current);
          feedbackTimeoutRef.current = window.setTimeout(() => {
            setEventFeedback(null);
          }, 1500);
        }

        if (msg.match_state) {
          setMatchState((prev) => {
            if (!prev) return null;
            const isUserBatting = (msg.match_state.batting_participant ?? msg.batting_participant ?? prev.batting_participant) !== undefined
              ? (msg.match_state.batting_participant ?? msg.batting_participant ?? prev.batting_participant) === participant
              : prev.user_is_batting;
            return {
              ...prev,
              ...msg.match_state,
              user_is_batting: isUserBatting,
              user_team: userTeamRef.current ?? prev.user_team ?? msg.match_state.user_team,
              opponent_team: opponentTeamRef.current ?? prev.opponent_team ?? msg.match_state.opponent_team,
            };
          });
        }
        break;
      }

      case 'bowler_selection_required': {
        setStage('BOWLER_SELECTION');
        setBowlerSelector(msg.bowler_selector);
        setBowlerSelectionPrompt({
          current_over: msg.current_over,
          eligible_bowlers: msg.eligible_bowlers || [],
          used_bowlers: msg.used_bowlers || [],
        });
        break;
      }

      case 'innings_break':
        stopCountdown();
        setStage('INNINGS_BREAK');
        if (msg.match_state) {
          setMatchState((prev) => {
            if (!prev) return null;
            const isUserBatting = (msg.match_state.batting_participant ?? msg.batting_participant ?? prev.batting_participant) !== undefined
              ? (msg.match_state.batting_participant ?? msg.batting_participant ?? prev.batting_participant) === participant
              : prev.user_is_batting;
            return {
              ...prev,
              ...msg.match_state,
              user_is_batting: isUserBatting,
              user_team: userTeamRef.current ?? prev.user_team ?? msg.match_state.user_team,
              opponent_team: opponentTeamRef.current ?? prev.opponent_team ?? msg.match_state.opponent_team,
              status: 'INNINGS_BREAK',
            };
          });
        }
        break;

      case 'match_completed': {
        stopCountdown();
        setStage('MATCH_COMPLETED');
        const userWon = Boolean(userTeam && msg.winner === userTeam.name);
        if (userWon) {
          soundManager.playMatchWin();
        } else if (!msg.is_tie) {
          soundManager.playMatchLoss();
        }
        if (msg.match_state) {
          setMatchState((prev) => {
            if (!prev) return null;
            const isUserBatting = (msg.match_state.batting_participant ?? msg.batting_participant ?? prev.batting_participant) !== undefined
              ? (msg.match_state.batting_participant ?? msg.batting_participant ?? prev.batting_participant) === participant
              : prev.user_is_batting;
            return {
              ...prev,
              ...msg.match_state,
              user_is_batting: isUserBatting,
              user_team: userTeamRef.current ?? prev.user_team ?? msg.match_state.user_team,
              opponent_team: opponentTeamRef.current ?? prev.opponent_team ?? msg.match_state.opponent_team,
              status: 'COMPLETED',
            };
          });
        }
        break;
      }

      case 'innings_break_acknowledged':
        if (msg.participant === participant || (Array.isArray(msg.ready_participants) && msg.ready_participants.includes(participant))) {
          setInningsBreakReady(true);
        }
        break;

      case 'rematch_requested':
        if (msg.participant === participant) {
          setRematchRequested(true);
        } else {
          setOpponentRematchRequested(true);
        }
        break;

      case 'room_abandoned':
        stopCountdown();
        setStage('ABANDONED');
        setErrorMessage(msg.reason || 'Room has been abandoned.');
        break;

      case 'error':
        setErrorMessage(msg.message || msg.code);
        setTimeout(() => setErrorMessage(null), 3000);
        break;

      default:
        break;
    }
  };

  // Client actions
  const selectTeam = (teamId: string) => {
    soundManager.playClick();
    soundManager.preloadAll();
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'select_team', team_id: teamId }));
    }
  };

  const chooseToss = (decision: 'BAT' | 'BOWL') => {
    soundManager.playClick();
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'choose_toss', decision }));
    }
  };

  const selectBowler = (bowlerId: number) => {
    soundManager.playClick();
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'select_bowler', bowler_id: bowlerId }));
    }
  };

  const submitNumber = (num: number) => {
    if (hasSubmitted || !currentTurnId) return;
    soundManager.playClick();
    setSelectedNumber(num);
    setHasSubmitted(true);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'submit_number',
          turn_id: currentTurnId,
          number: num,
        })
      );
    }
  };

  const startNextInnings = () => {
    if (isStartingInningsRef.current) return;
    soundManager.playClick();
    isStartingInningsRef.current = true;
    setInningsBreakReady(true);
    setTimeout(() => {
      isStartingInningsRef.current = false;
    }, 2000);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'start_innings_2' }));
    }
  };

  const requestRematch = () => {
    soundManager.playClick();
    setRematchRequested(true);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'request_rematch' }));
    }
  };

  const leaveRoom = () => {
    soundManager.playClick();
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'leave_room' }));
    }
    onLeave();
  };

  return {
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
    currentTurnId,
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
    onLeave,
  };
}
