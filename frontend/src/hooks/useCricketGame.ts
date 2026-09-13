import { useCallback, useEffect, useRef, useState } from 'react';
import { EventFeedback, MatchState } from '../types';

export function useCricketGame() {
  const [matchState, setMatchState] = useState<MatchState | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'error' | 'disconnected'
  >('connecting');
  const [selectedNumber, setSelectedNumber] = useState<number | null>(null);
  const [isWaiting, setIsWaiting] = useState<boolean>(false);
  const [eventFeedback, setEventFeedback] = useState<EventFeedback | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const feedbackTimeoutRef = useRef<number | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

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

        if (data.type === 'turn_started') {
          if (data.match_state) {
            setMatchState(data.match_state);
          }
          setSelectedNumber(null);
          setIsWaiting(false);
        } else if (data.type === 'number_submitted') {
          // Acknowledgment received; choice stays hidden until resolution
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

              triggerFeedback({
                type: lastBall.event,
                runs: lastBall.runs,
                title,
                subtitle,
                number: lastBall.runs,
                userChoice: lastBall.user_choice,
                computerChoice: lastBall.computer_choice,
                userTimedOut: lastBall.user_timed_out,
              });
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

  const triggerFeedback = (feedback: EventFeedback) => {
    if (feedbackTimeoutRef.current) {
      window.clearTimeout(feedbackTimeoutRef.current);
    }
    setEventFeedback(feedback);
    feedbackTimeoutRef.current = window.setTimeout(() => {
      setEventFeedback(null);
    }, 1800);
  };

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
    matchState,
    connectionStatus,
    selectedNumber,
    isWaiting,
    eventFeedback,
    errorMessage,
    submitNumber,
    startNextInnings,
    resetGame,
    reconnect: connect,
  };
}
