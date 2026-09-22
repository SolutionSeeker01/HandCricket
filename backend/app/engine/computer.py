"""Headless Computer Player domain engine for Hand Cricket.

This module provides a headless ComputerPlayer abstraction responsible for
generating legal ball choices (1, 2, 3, 4, 6) across difficulty levels.

Difficulties:
- Difficulty.EASY: Un-opinionated uniform random integer from (1, 2, 3, 4, 6)
  for each turn. Maintains no state, history, tracking, or situational awareness.
- Difficulty.MEDIUM: Light intelligence. Maintains short recent history of revealed
  opponent choices. When bowling, applies modest bias (~25–35%) toward numbers the
  player repeats or favors. When batting, considers chase context (runs needed and
  balls remaining) and slightly evades the player's favorite bowling delivery.
- Difficulty.HARD: Strong adaptive intelligence. Analyzes first-order transitions
  (Markov patterns), streaks, recent and overall frequencies, and match situation
  pressure (chases, boundary requirements, death overs). When batting, aggressively
  evades the opponent's predicted delivery while tailoring scoring choices to the
  required run rate. Remains probabilistic with positive probability floors on all choices.

Randomness is injectable via custom chooser or random.Random for fully deterministic testing.
Validation of generated choices delegates directly to the ball engine to ensure
a single source of truth for legal ball choices.
"""

from dataclasses import dataclass
from enum import Enum
import random
from typing import Callable, Dict, List, Optional, Union

from backend.app.engine.ball import (
    MAX_BALL_CHOICE,
    MIN_BALL_CHOICE,
    VALID_BALL_CHOICES,
    InvalidBallChoiceError,
    validate_choice,
)

NumberChooser = Callable[[], int]
MAX_HISTORY_LENGTH: int = 30  # Bounded to 30 balls (exactly one full 5-over innings)


class Difficulty(str, Enum):
    """Supported difficulty levels for the computer player."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass(frozen=True)
class MatchContext:
    """Read-only situational context provided to the computer player for a delivery.

    Attributes:
        role: Computer's role on this delivery ('bat' or 'bowl'). Defaults to 'bowl'.
        target: Target runs to win in Innings 2, or None in Innings 1.
        runs_needed: Runs remaining to reach target, or None in Innings 1.
        balls_remaining: Legal balls remaining in the innings, or None.
        innings: Current innings number (1 or 2). Defaults to 1.
    """

    role: str = "bowl"
    target: Optional[int] = None
    runs_needed: Optional[int] = None
    balls_remaining: Optional[int] = None
    innings: int = 1


def default_number_chooser() -> int:
    """Production default random chooser generating an integer in (1, 2, 3, 4, 6)."""
    return random.choice(VALID_BALL_CHOICES)


def _analyze_transitions(history: List[int]) -> Dict[int, Dict[int, int]]:
    """Compute first-order Markov transition counts from an ordered sequence of choices.

    Returns:
        Mapping from previous choice to a dictionary of {successor_choice: count}.
    """
    transitions: Dict[int, Dict[int, int]] = {}
    for i in range(len(history) - 1):
        prev = history[i]
        curr = history[i + 1]
        if prev not in transitions:
            transitions[prev] = {}
        transitions[prev][curr] = transitions[prev].get(curr, 0) + 1
    return transitions


class ComputerPlayer:
    """Headless Computer Player for Hand Cricket.

    Generates legal number choices (1, 2, 3, 4, 6) for batting or bowling turns.

    Invariants:
        - Returned choices are strictly integers in VALID_BALL_CHOICES (1, 2, 3, 4, 6).
        - Reuses ball.py's validate_choice() as the single source of truth.
        - Supports dependency injection of the chooser callable or custom RNG.
        - In Difficulty.EASY, choices are uniformly random with no match context or memory.
        - In Difficulty.MEDIUM, choices reflect lightweight situational weights (~25–35% bias).
        - In Difficulty.HARD, choices reflect adaptive multi-layered pattern modeling and chase pressure.
        - Never accesses unrevealed opponent choices; learns only from recorded historical balls.
        - History is bounded to MAX_HISTORY_LENGTH (30 balls) per discipline.
    """

    def __init__(
        self,
        chooser: Optional[NumberChooser] = None,
        difficulty: Union[Difficulty, str] = Difficulty.EASY,
        rng: Optional[random.Random] = None,
    ) -> None:
        if chooser is not None and not callable(chooser):
            raise TypeError(
                f"Expected callable for chooser, got {type(chooser).__name__}."
            )

        if isinstance(difficulty, str):
            try:
                self._difficulty = Difficulty(difficulty.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid difficulty {difficulty!r}. Must be one of {[d.value for d in Difficulty]}."
                )
        elif isinstance(difficulty, Difficulty):
            self._difficulty = difficulty
        else:
            raise TypeError(
                f"Expected Difficulty enum or str, got {type(difficulty).__name__}."
            )

        self._chooser: Optional[NumberChooser] = (
            chooser
            if chooser is not None
            else (default_number_chooser if self._difficulty == Difficulty.EASY else None)
        )
        self._rng: random.Random = rng if rng is not None else random.Random()
        self._opponent_batting_history: List[int] = []
        self._opponent_bowling_history: List[int] = []

    @property
    def difficulty(self) -> Difficulty:
        """The active difficulty level of the computer player."""
        return self._difficulty

    def record_opponent_choice(self, choice: int, role: str = "bat") -> None:
        """Record an opponent's revealed choice after a ball is resolved.

        Args:
            choice: The integer choice (1, 2, 3, 4, 6) revealed by the opponent.
            role: The role the opponent was playing ('bat' or 'bowl'). Defaults to 'bat'.

        Raises:
            InvalidBallChoiceError: If the choice is not in VALID_BALL_CHOICES.
            ValueError: If role is not 'bat' or 'bowl'.
        """
        valid_choice = validate_choice(choice, role="user")
        normalized_role = role.strip().lower()
        if normalized_role == "bat":
            self._opponent_batting_history.append(valid_choice)
            if len(self._opponent_batting_history) > MAX_HISTORY_LENGTH:
                self._opponent_batting_history = self._opponent_batting_history[-MAX_HISTORY_LENGTH:]
        elif normalized_role == "bowl":
            self._opponent_bowling_history.append(valid_choice)
            if len(self._opponent_bowling_history) > MAX_HISTORY_LENGTH:
                self._opponent_bowling_history = self._opponent_bowling_history[-MAX_HISTORY_LENGTH:]
        else:
            raise ValueError(f"Invalid role {role!r}. Expected 'bat' or 'bowl'.")

    def reset_history(self) -> None:
        """Clear all recorded opponent history (e.g. for a new match)."""
        self._opponent_batting_history.clear()
        self._opponent_bowling_history.clear()

    def calculate_weights(self, context: Optional[MatchContext] = None) -> Dict[int, float]:
        """Compute the probability weights for each legal choice under the active difficulty.

        Returns:
            Dictionary mapping each choice in VALID_BALL_CHOICES to its positive weight.
        """
        if self._difficulty == Difficulty.EASY:
            return {c: 1.0 for c in VALID_BALL_CHOICES}

        ctx = context if context is not None else MatchContext()

        if self._difficulty == Difficulty.MEDIUM:
            return self._calculate_medium_weights(ctx)

        if self._difficulty == Difficulty.HARD:
            return self._calculate_hard_weights(ctx)

        return {c: 1.0 for c in VALID_BALL_CHOICES}

    def _calculate_medium_weights(self, ctx: MatchContext) -> Dict[int, float]:
        """Compute Medium-difficulty weights based on role, short history, and chase state."""
        weights = {c: 1.0 for c in VALID_BALL_CHOICES}

        if ctx.role == "bowl":
            recent = self._opponent_batting_history[-6:]
            if len(recent) >= 2:
                counts: Dict[int, int] = {}
                for c in recent:
                    counts[c] = counts.get(c, 0) + 1

                is_repetition = len(recent) >= 2 and recent[-1] == recent[-2]
                if is_repetition:
                    weights[recent[-1]] += 0.9
                else:
                    most_common_choice = max(counts, key=counts.get)
                    if counts[most_common_choice] >= 2:
                        weights[most_common_choice] += 0.7
            return weights

        elif ctx.role == "bat":
            if (
                ctx.runs_needed is not None
                and ctx.balls_remaining is not None
                and ctx.balls_remaining > 0
            ):
                if ctx.runs_needed <= 2:
                    weights = {1: 2.0, 2: 2.0, 3: 0.8, 4: 0.5, 6: 0.5}
                else:
                    rrr = ctx.runs_needed / ctx.balls_remaining
                    if rrr >= 2.0:
                        weights = {1: 0.5, 2: 0.6, 3: 0.8, 4: 1.8, 6: 2.0}
                    else:
                        weights = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.3, 6: 1.2}
            else:
                # Innings 1 / Setting Target
                if ctx.balls_remaining is not None and ctx.balls_remaining <= 6:
                    # Over 5 (Death overs): surge
                    weights = {1: 0.7, 2: 0.9, 3: 1.2, 4: 2.2, 6: 2.2}
                elif ctx.balls_remaining is not None and ctx.balls_remaining <= 18:
                    # Overs 3-4 (Middle overs): accelerate
                    weights = {1: 1.0, 2: 1.1, 3: 1.3, 4: 1.7, 6: 1.5}
                else:
                    # Overs 1-2 (balls_remaining > 18 or None): play safe, build platform, try not to get out
                    weights = {1: 1.6, 2: 1.6, 3: 1.4, 4: 0.9, 6: 0.7}

            recent_bowl = self._opponent_bowling_history[-5:]
            if len(recent_bowl) >= 2:
                counts_bowl: Dict[int, int] = {}
                for c in recent_bowl:
                    counts_bowl[c] = counts_bowl.get(c, 0) + 1
                favored_bowl = max(counts_bowl, key=counts_bowl.get)
                if counts_bowl[favored_bowl] >= 2:
                    weights[favored_bowl] = max(0.2, weights[favored_bowl] - 0.7)

            return weights

        return weights

    def _calculate_hard_weights(self, ctx: MatchContext) -> Dict[int, float]:
        """Compute Hard-difficulty weights using transitions, frequencies, repetition, and situations."""
        weights = {c: 1.0 for c in VALID_BALL_CHOICES}

        if ctx.role == "bowl":
            history = self._opponent_batting_history
            m = len(history)

            # Cold start: 0 to 2 observations -> weak/no pattern assertion
            if m < 3:
                if m == 2 and history[-1] == history[-2]:
                    # Gentle repetition awareness even on early ball 2
                    weights[history[-1]] += 0.5
            else:
                # 1. First-Order Markov Transition Modeling
                prev = history[-1]
                transitions = _analyze_transitions(history)
                if prev in transitions:
                    next_counts = transitions[prev]
                    favored_next, t_count = max(next_counts.items(), key=lambda item: item[1])
                    # Transition confidence ramps with evidence support (1.2 for 1 observation, up to 2.4)
                    trans_boost = 1.2 + min(t_count - 1, 2) * 0.6
                    weights[favored_next] += trans_boost

                # 2. Immediate Repetition / Streak Analysis
                streak = 1
                while streak < m and history[-1 - streak] == history[-1]:
                    streak += 1

                if streak == 2:
                    weights[history[-1]] += 1.3
                elif streak >= 3:
                    weights[history[-1]] += 1.6

                # 3. Recent Frequency Layer (last 8 balls)
                recent = history[-8:]
                counts: Dict[int, int] = {}
                for c in recent:
                    counts[c] = counts.get(c, 0) + 1
                most_freq_choice = max(counts, key=counts.get)
                if counts[most_freq_choice] >= 3:
                    weights[most_freq_choice] += 1.1

            # 4. Situational Prediction Layer (Match Context Pressure)
            if (
                ctx.runs_needed is not None
                and ctx.balls_remaining is not None
                and ctx.balls_remaining > 0
            ):
                if ctx.runs_needed > ctx.balls_remaining * 4:
                    # Mathematical boundary necessity: opponent must hit 6 to win/survive
                    weights[6] += 3.0
                    weights[4] += 1.0
                elif ctx.runs_needed > ctx.balls_remaining * 2:
                    # High RRR: boundaries heavily expected
                    weights[6] += 1.8
                    weights[4] += 1.5
                elif ctx.runs_needed <= 2:
                    # Small target: opponent expected to pick safe 1 or 2
                    weights[1] += 2.0
                    weights[2] += 2.0
                    weights[4] = max(0.4, weights[4] - 0.6)
                    weights[6] = max(0.4, weights[6] - 0.6)

            # Death overs pressure in any innings (last 3 balls)
            if ctx.balls_remaining is not None and 1 <= ctx.balls_remaining <= 3:
                weights[6] += 1.0
                weights[4] += 0.8

            # Ensure positive floor on all choices so prediction remains strictly probabilistic
            for c in VALID_BALL_CHOICES:
                weights[c] = max(0.4, weights[c])

            return weights

        elif ctx.role == "bat":
            # Computer is BATTING: adapt against human bowler
            bowl_history = self._opponent_bowling_history
            m_bowl = len(bowl_history)

            predicted_bowl: Optional[int] = None

            if m_bowl >= 2:
                prev_bowl = bowl_history[-1]
                transitions = _analyze_transitions(bowl_history)
                if prev_bowl in transitions:
                    next_counts = transitions[prev_bowl]
                    predicted_bowl = max(next_counts, key=next_counts.get)
                elif bowl_history[-1] == bowl_history[-2]:
                    predicted_bowl = prev_bowl
                else:
                    recent_bowl = bowl_history[-8:]
                    counts = {}
                    for c in recent_bowl:
                        counts[c] = counts.get(c, 0) + 1
                    most_common = max(counts, key=counts.get)
                    if counts[most_common] >= 2:
                        predicted_bowl = most_common

            # Chase Strategy
            if (
                ctx.runs_needed is not None
                and ctx.balls_remaining is not None
                and ctx.balls_remaining > 0
            ):
                if ctx.runs_needed == 1:
                    # Needs 1 run: strongly favor 1 (or 2 if 1 is predicted to be bowled)
                    weights = {1: 4.0, 2: 2.0, 3: 0.5, 4: 0.2, 6: 0.2}
                elif ctx.runs_needed == 2:
                    # Needs 2 runs: strongly favor 2 and 1
                    weights = {1: 2.5, 2: 3.5, 3: 0.8, 4: 0.3, 6: 0.3}
                elif ctx.runs_needed <= 4:
                    # Small chase (3 or 4 runs): tactical safe choices
                    weights = {1: 1.2, 2: 1.8, 3: 2.0, 4: 1.8, 6: 0.5}
                else:
                    rrr = ctx.runs_needed / ctx.balls_remaining
                    if rrr >= 2.0:
                        # High RRR: boundary urgency
                        weights = {1: 0.3, 2: 0.4, 3: 0.7, 4: 2.4, 6: 2.6}
                    elif rrr >= 1.2:
                        weights = {1: 0.8, 2: 1.0, 3: 1.4, 4: 1.8, 6: 1.6}
                    else:
                        weights = {1: 1.2, 2: 1.5, 3: 1.3, 4: 1.2, 6: 1.0}
            else:
                # Innings 1 or setting target
                if ctx.balls_remaining is not None and ctx.balls_remaining <= 6:
                    weights = {1: 0.5, 2: 0.8, 3: 1.2, 4: 2.4, 6: 2.6}
                else:
                    weights = {1: 0.9, 2: 1.3, 3: 1.8, 4: 2.0, 6: 1.8}

            # Active Evasion of predicted human delivery & Anti-Bait Counter
            if predicted_bowl is not None:
                weights[predicted_bowl] = max(0.15, weights[predicted_bowl] * 0.2)
                if ctx.runs_needed is None:
                    if predicted_bowl == 6:
                        weights[3] += 1.0
                        weights[4] += 1.0
                    elif predicted_bowl == 4:
                        weights[6] += 1.0
                        weights[3] += 1.0
                    elif predicted_bowl in (1, 2):
                        weights[4] += 0.8
                        weights[6] += 0.8

            # Ensure positive floor on all choices
            for c in VALID_BALL_CHOICES:
                weights[c] = max(0.1, weights[c])

            return weights

        return weights

    def choose_number(self, context: Optional[MatchContext] = None) -> int:
        """Generate and validate a ball choice under the active difficulty strategy.

        Args:
            context: Optional situational context (role, target, runs needed, balls left).

        Returns:
            An integer in (1, 2, 3, 4, 6).

        Raises:
            InvalidBallChoiceError: If an injected chooser produces an invalid choice.
        """
        if self._chooser is not None:
            raw_choice = self._chooser()
            return validate_choice(raw_choice, role="computer")

        if self._difficulty == Difficulty.EASY:
            raw_choice = default_number_chooser()
            return validate_choice(raw_choice, role="computer")

        if self._difficulty in (Difficulty.MEDIUM, Difficulty.HARD):
            weights = self.calculate_weights(context)
            choices = list(VALID_BALL_CHOICES)
            weights_list = [weights[c] for c in choices]
            selected = self._rng.choices(choices, weights=weights_list, k=1)[0]
            return validate_choice(selected, role="computer")

        raw_choice = default_number_chooser()
        return validate_choice(raw_choice, role="computer")

    def __repr__(self) -> str:
        chooser_name = (
            self._chooser.__name__
            if hasattr(self._chooser, "__name__")
            else repr(self._chooser)
            if self._chooser is not None
            else "strategy_weighted"
        )
        return f"ComputerPlayer(difficulty={self._difficulty.value!r}, chooser={chooser_name})"
