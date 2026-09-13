import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AppStage,
  BowlerSelectionPrompt,
  EventFeedback,
  MatchState,
  MilestoneFeedback,
  PreMatchState,
} from '../types';

export function useCricketGame() {
  const [appStage, setAppStage] = useState<AppStage>('LANDING');
  const [preMatchState, setPreMatchState] = useState<PreMatchState | null>(null);
  const [bowlerSelectionPrompt, setBowlerSelectionPrompt] = useState<BowlerSelectionPrompt | null>(null);
  const [matchState, setMatchState] = useState<MatchState | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'error' | 'disconnected'
  >('connecting');
  const [selectedNumber, setSelectedNumber] = useState<number | null>(null);
  const [isWaiting, setIsWaiting] = useState<boolean>(false);
  const [eventFeedback, setEventFeedback] = useState<EventFeedback | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const [milestoneFeedback, setMilestoneFeedback] = useState<MilestoneFeedback | null>(null);
  const feedbackTimeoutRef = useRef<number | null>(null);
  const milestoneTimeoutRef = useRef<number | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const prevPlayerScoresRef = useRef<Record<string, number>>({});
  const celebratedMilestonesRef = useRef<Set<string>>(new Set<string>());

  const connect = useCallback(() => {
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    setConnectionStatus('connecting');
    setErrorMessage(null);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host =
      window.location.port === '5173'
        ? `${window.location.hostname || '127.0.0.1'}:8000`
        : window.location.host;
    const wsUrl = `${protocol}//${host}/ws?mode=computer`;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      if (socketRef.current !== ws) return;
      setConnectionStatus('connected');
      setErrorMessage(null);
    };

    ws.onmessage = (event) => {
      if (socketRef.current !== ws) return;
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'pre_match_state') {
          setPreMatchState(data);
          setIsWaiting(false);
          if (data.stage === 'IN_MATCH') {
            setAppStage('IN_MATCH');
          }
        } else if (data.type === 'bowler_selection_required') {
          setBowlerSelectionPrompt({
            current_over: data.current_over,
            eligible_bowlers: data.eligible_bowlers,
            used_bowlers: data.used_bowlers,
            match_state: data.match_state,
          });
          if (data.match_state) {
            setMatchState(data.match_state);
          }
          setIsWaiting(false);
        } else if (data.type === 'turn_started') {
          if (data.match_state) {
            setMatchState(data.match_state);
          }
          setAppStage('IN_MATCH');
          setBowlerSelectionPrompt(null);
          setSelectedNumber(null);
          setIsWaiting(false);
        } else if (data.type === 'number_submitted') {
          setIsWaiting(true);
        } else if (data.type === 'ball_result') {
          if (data.match_state) {
            setMatchState(data.match_state);

            const lastBall = data.match_state.last_ball;
            if (lastBall) {
              let title = '';
              let subtitle: string | undefined = undefined;

              if (lastBall.event === 'WICKET') {
                title = 'WICKET!';
                subtitle = lastBall.out_player
                  ? `${lastBall.out_player} is out!`
                  : 'Batter is out!';
              } else if (lastBall.event === 'SIX') {
                title = 'SIX!';
                subtitle = '+6 RUNS';
              } else if (lastBall.event === 'FOUR') {
                title = 'FOUR!';
                subtitle = '+4 RUNS';
              } else {
                title = lastBall.runs === 0 ? 'DOT BALL' : `+${lastBall.runs} ${lastBall.runs === 1 ? 'RUN' : 'RUNS'}`;
                subtitle = lastBall.runs === 0 ? '0 Runs scored' : `+${lastBall.runs} Runs scored`;
              }

              // Check for 50 or 100 milestone on striker
              let detectedMilestone: MilestoneFeedback | null = null;
              const striker = data.match_state.striker;
              if (striker && striker.name) {
                const pKey = `${striker.id ?? striker.name}`;
                const prevRuns = prevPlayerScoresRef.current[pKey] ?? 0;
                const newRuns = striker.runs;
                prevPlayerScoresRef.current[pKey] = newRuns;

                const fiftyKey = `${pKey}_50`;
                const centuryKey = `${pKey}_100`;

                if (prevRuns < 100 && newRuns >= 100 && !celebratedMilestonesRef.current.has(centuryKey)) {
                  celebratedMilestonesRef.current.add(centuryKey);
                  detectedMilestone = {
                    batsmanName: striker.name,
                    milestone: 100,
                    label: 'CENTURY!',
                  };
                } else if (prevRuns < 50 && newRuns >= 50 && !celebratedMilestonesRef.current.has(fiftyKey)) {
                  celebratedMilestonesRef.current.add(fiftyKey);
                  detectedMilestone = {
                    batsmanName: striker.name,
                    milestone: 50,
                    label: 'FIFTY!',
                  };
                }
              }

              const nonStriker = data.match_state.non_striker;
              if (nonStriker && nonStriker.name) {
                const nKey = `${nonStriker.id ?? nonStriker.name}`;
                prevPlayerScoresRef.current[nKey] = nonStriker.runs;
              }

              const ballFeedback: EventFeedback = {
                type: lastBall.event,
                runs: lastBall.runs,
                title,
                subtitle,
                number: lastBall.runs,
                batsmanChoice: lastBall.batsman_choice,
                userChoice: lastBall.user_choice,
                computerChoice: lastBall.computer_choice,
                userTimedOut: lastBall.user_timed_out,
              };

              if (detectedMilestone) {
                triggerFeedback(ballFeedback, 1400);
                if (milestoneTimeoutRef.current) {
                  window.clearTimeout(milestoneTimeoutRef.current);
                }
                milestoneTimeoutRef.current = window.setTimeout(() => {
                  setMilestoneFeedback(detectedMilestone);
                  milestoneTimeoutRef.current = window.setTimeout(() => {
                    setMilestoneFeedback(null);
                  }, 1500);
                }, 1400);
              } else {
                triggerFeedback(ballFeedback, 1800);
              }
            }
          }
        } else if (data.type === 'error') {
          setErrorMessage(data.message || 'An unexpected error occurred.');
          setIsWaiting(false);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = () => {
      if (socketRef.current !== ws) return;
      setConnectionStatus('error');
      setErrorMessage('Unable to connect to game server.');
    };

    ws.onclose = () => {
      if (socketRef.current === ws) {
        setConnectionStatus('disconnected');
        socketRef.current = null;
      }
    };
  }, []);

  const triggerFeedback = (feedback: EventFeedback, durationMs = 1800) => {
    if (feedbackTimeoutRef.current) {
      window.clearTimeout(feedbackTimeoutRef.current);
    }
    setEventFeedback(feedback);
    feedbackTimeoutRef.current = window.setTimeout(() => {
      setEventFeedback(null);
    }, durationMs);
  };

  const startVsComputer = useCallback(() => {
    setAppStage('PRE_MATCH');
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      connect();
    }
  }, [connect]);

  const goToLanding = useCallback(() => {
    setAppStage('LANDING');
  }, []);

  const selectTeam = useCallback((teamId: string) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setErrorMessage('Not connected to game server.');
      return;
    }
    setIsWaiting(true);
    socketRef.current.send(JSON.stringify({ type: 'select_team', team_id: teamId }));
  }, []);

  const chooseToss = useCallback((decision: 'BAT' | 'BOWL') => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setErrorMessage('Not connected to game server.');
      return;
    }
    setIsWaiting(true);
    socketRef.current.send(JSON.stringify({ type: 'choose_toss', decision }));
  }, []);

  const selectBowler = useCallback((bowlerId: number) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setErrorMessage('Not connected to game server.');
      return;
    }
    setIsWaiting(true);
    socketRef.current.send(JSON.stringify({ type: 'select_bowler', bowler_id: bowlerId }));
  }, []);

  const resetPreMatch = useCallback(() => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      connect();
      return;
    }
    setIsWaiting(false);
    socketRef.current.send(JSON.stringify({ type: 'reset_pre_match' }));
  }, [connect]);

  const submitNumber = useCallback((number: number) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setErrorMessage('Not connected to game server.');
      return;
    }
    setSelectedNumber(number);
    setIsWaiting(true);
    socketRef.current.send(
      JSON.stringify({
        type: 'submit_number',
        number,
        turn_id: matchState?.turn_id,
      })
    );
  }, [matchState?.turn_id]);

  const startNextInnings = useCallback(() => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      return;
    }
    socketRef.current.send(JSON.stringify({ type: 'start_innings_2' }));
  }, []);

  const resetGame = useCallback(() => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      connect();
      return;
    }
    setSelectedNumber(null);
    setIsWaiting(false);
    setEventFeedback(null);
    setMilestoneFeedback(null);
    prevPlayerScoresRef.current = {};
    celebratedMilestonesRef.current.clear();
    if (milestoneTimeoutRef.current) {
      window.clearTimeout(milestoneTimeoutRef.current);
      milestoneTimeoutRef.current = null;
    }
    setAppStage('PRE_MATCH');
    socketRef.current.send(JSON.stringify({ type: 'new_game' }));
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (feedbackTimeoutRef.current) {
        window.clearTimeout(feedbackTimeoutRef.current);
      }
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [connect]);

  return {
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
    reconnect: connect,
  };
}

