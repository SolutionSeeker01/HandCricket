import asyncio
from typing import List
import pytest
from fastapi.testclient import TestClient

from backend.app.engine.teams import get_teams, get_team, is_valid_team_id
from backend.app.engine.toss import TossDecision
from backend.app.main import app
from backend.app.protocol.game import ComputerGameSession
from backend.app.protocol.messages import (
    TYPE_PRE_MATCH_STATE,
    TYPE_SELECT_TEAM,
    TYPE_CHOOSE_TOSS,
    TYPE_SELECT_BOWLER,
    TYPE_BOWLER_SELECTION_REQUIRED,
    TYPE_RESET_PRE_MATCH,
    TurnProtocolError,
)
from backend.app.transport.websocket import reset_standalone_computer_session

client = TestClient(app)


def test_get_teams_endpoint():
    """GET /teams returns the 4 predefined teams with 11 players each."""
    response = client.get("/teams")
    assert response.status_code == 200
    teams = response.json()
    assert len(teams) == 4
    team_ids = [t["id"] for t in teams]
    assert "IND" in team_ids
    assert "AUS" in team_ids
    assert "ENG" in team_ids
    assert "SA" in team_ids

    for team in teams:
        assert len(team["players"]) == 11
        for p in team["players"]:
            assert "id" in p
            assert "name" in p
            assert 1 <= p["id"] <= 11


def test_initial_state_is_team_selection():
    """Session created with skip_pre_match=False begins in TEAM_SELECTION stage."""
    session = ComputerGameSession(skip_pre_match=False)
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        msg = ws.receive_json()
        assert msg["type"] == TYPE_PRE_MATCH_STATE
        assert msg["stage"] == "TEAM_SELECTION"
        assert len(msg["available_teams"]) == 4
        assert msg["user_team"] is None
        assert msg["opponent_team"] is None
        assert msg["toss_winner"] is None
        assert msg["toss_decision"] is None


def test_user_selects_each_valid_predefined_team():
    """User can select IND, AUS, ENG, or SA and receives opponent team and toss result."""
    for team_id in ["IND", "AUS", "ENG", "SA"]:
        session = ComputerGameSession(
            skip_pre_match=False,
            toss_chooser=lambda: "A",
            computer_team_chooser=lambda: "AUS",
        )
        reset_standalone_computer_session(session)

        with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
            init_msg = ws.receive_json()
            assert init_msg["stage"] == "TEAM_SELECTION"

            ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": team_id})
            next_msg = ws.receive_json()
            assert next_msg["type"] == TYPE_PRE_MATCH_STATE
            assert next_msg["user_team"]["id"] == team_id
            assert next_msg["opponent_team"]["id"] == "AUS"
            assert next_msg["toss_winner"] == "user"
            assert next_msg["stage"] == "TOSS_DECISION"


def test_invalid_team_selection_rejected():
    """Invalid team ID sends an error to client."""
    session = ComputerGameSession(skip_pre_match=False)
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "INVALID"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "invalid_team_id"


def test_same_team_selection_allowed():
    """User and computer can both play with the same team (e.g., IND vs IND)."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "A",
        computer_team_chooser=lambda: "IND",
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})
        state = ws.receive_json()
        assert state["user_team"]["id"] == "IND"
        assert state["opponent_team"]["id"] == "IND"


def test_user_wins_toss_and_chooses_bat():
    """User wins toss and chooses BAT -> Computer chooses bowler -> Match starts directly."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "A",
        computer_team_chooser=lambda: "AUS",
        computer_bowler_chooser=lambda eligible: 8,  # Pat Cummins
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()  # init TEAM_SELECTION
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})
        toss_state = ws.receive_json()
        assert toss_state["toss_winner"] == "user"
        assert toss_state["stage"] == "TOSS_DECISION"

        # User chooses BAT
        ws.send_json({"type": TYPE_CHOOSE_TOSS, "decision": "BAT"})

        # Match starts, turn_started is emitted
        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "turn_started"
        assert turn_msg["match_state"]["user_is_batting"] is True
        assert turn_msg["match_state"]["user_batted_first"] is True
        assert turn_msg["match_state"]["user_team"]["id"] == "IND"
        assert turn_msg["match_state"]["opponent_team"]["id"] == "AUS"
        assert turn_msg["match_state"]["striker"]["name"] == "Rohit Sharma"
        assert turn_msg["match_state"]["non_striker"]["name"] == "Shubman Gill"
        assert turn_msg["match_state"]["bowler"]["name"] == "Pat Cummins"


def test_user_wins_toss_and_chooses_bowl():
    """User wins toss and chooses BOWL -> Stage transitions to BOWLER_SELECTION -> User chooses bowler -> Match starts."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "A",
        computer_team_chooser=lambda: "AUS",
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()  # init TEAM_SELECTION
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})
        ws.receive_json()  # toss state

        # User chooses BOWL
        ws.send_json({"type": TYPE_CHOOSE_TOSS, "decision": "BOWL"})

        bowler_prompt = ws.receive_json()
        assert bowler_prompt["type"] == TYPE_PRE_MATCH_STATE
        assert bowler_prompt["stage"] == "BOWLER_SELECTION"
        assert bowler_prompt["first_bowler_selector"] == "user"
        assert len(bowler_prompt["eligible_bowlers"]) == 11

        # User picks Mohammed Siraj (id=11)
        ws.send_json({"type": TYPE_SELECT_BOWLER, "bowler_id": 11})

        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "turn_started"
        assert turn_msg["match_state"]["user_is_batting"] is False
        assert turn_msg["match_state"]["user_batted_first"] is False
        assert turn_msg["match_state"]["striker"]["name"] == "David Warner"
        assert turn_msg["match_state"]["bowler"]["name"] == "Mohammed Siraj"


def test_computer_wins_toss_and_chooses_bat():
    """Computer wins toss and chooses BAT -> User bowls first -> BOWLER_SELECTION stage."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "B",
        computer_team_chooser=lambda: "AUS",
        computer_decision_chooser=lambda: TossDecision.BAT,
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})

        state = ws.receive_json()
        assert state["type"] == TYPE_PRE_MATCH_STATE
        assert state["stage"] == "BOWLER_SELECTION"
        assert state["toss_winner"] == "computer"
        assert state["toss_decision"] == "BAT"
        assert state["batting_first"] == "computer"
        assert state["bowling_first"] == "user"
        assert state["first_bowler_selector"] == "user"

        # User selects bowler (Mohammed Shami: id=10)
        ws.send_json({"type": TYPE_SELECT_BOWLER, "bowler_id": 10})

        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "turn_started"
        assert turn_msg["match_state"]["user_is_batting"] is False
        assert turn_msg["match_state"]["user_batted_first"] is False
        assert turn_msg["match_state"]["bowler"]["name"] == "Mohammed Shami"


def test_computer_wins_toss_and_chooses_bowl():
    """Computer wins toss and chooses BOWL -> Computer bowls first -> auto picks bowler -> Match starts."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "B",
        computer_team_chooser=lambda: "AUS",
        computer_decision_chooser=lambda: TossDecision.BOWL,
        computer_bowler_chooser=lambda eligible: 9,  # Mitchell Starc
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})

        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "turn_started"
        assert turn_msg["match_state"]["user_is_batting"] is True
        assert turn_msg["match_state"]["user_batted_first"] is True
        assert turn_msg["match_state"]["bowler"]["name"] == "Mitchell Starc"


def test_invalid_bowler_id_rejected():
    """Invalid bowler ID (<1 or >11) in pre-match is rejected."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "A",
        computer_team_chooser=lambda: "AUS",
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})
        ws.receive_json()
        ws.send_json({"type": TYPE_CHOOSE_TOSS, "decision": "BOWL"})
        ws.receive_json()

        # Send invalid bowler 99
        ws.send_json({"type": TYPE_SELECT_BOWLER, "bowler_id": 99})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "invalid_bowler_id"


def test_reset_pre_match_resets_session():
    """Client can reset pre-match back to team selection."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "A",
        computer_team_chooser=lambda: "AUS",
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})
        ws.receive_json()

        # Reset
        ws.send_json({"type": TYPE_RESET_PRE_MATCH})
        reset_state = ws.receive_json()
        assert reset_state["type"] == TYPE_PRE_MATCH_STATE
        assert reset_state["stage"] == "TEAM_SELECTION"
        assert reset_state["user_team"] is None


def test_play_first_ball_after_pre_match():
    """After pre-match flow completes, user can play ball 1 and get results."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "A",
        computer_team_chooser=lambda: "ENG",
        computer_bowler_chooser=lambda eligible: 11,
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})
        ws.receive_json()
        ws.send_json({"type": TYPE_CHOOSE_TOSS, "decision": "BAT"})
        init_turn = ws.receive_json()
        assert init_turn["type"] == "turn_started"

        # User submits 4
        ws.send_json({"type": "submit_number", "number": 4})
        ack = ws.receive_json()
        assert ack["type"] == "number_submitted"

        ball_res = ws.receive_json()
        assert ball_res["type"] == "ball_result"
        assert "batsman_choice" in ball_res
        assert "bowler_choice" in ball_res


def test_over_by_over_bowler_selection_when_user_bowls():
    """When user is bowling and an over ends, user is prompted to select next bowler, used bowlers cannot be reselected."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "A",
        computer_team_chooser=lambda: "AUS",
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})
        ws.receive_json()
        ws.send_json({"type": TYPE_CHOOSE_TOSS, "decision": "BOWL"})
        ws.receive_json()

        # Over 1 bowler: Mohammed Siraj (11)
        ws.send_json({"type": TYPE_SELECT_BOWLER, "bowler_id": 11})
        ws.receive_json()  # turn_started ball 1

        # Play 6 balls (1 over)
        for ball in range(1, 7):
            ws.send_json({"type": "submit_number", "number": 1})
            ws.receive_json()  # number_submitted
            res = ws.receive_json()  # ball_result
            if ball < 6:
                next_turn = ws.receive_json()
                assert next_turn["type"] == "turn_started"

        # After ball 6 of Over 1, user must select bowler for Over 2
        prompt = ws.receive_json()
        assert prompt["type"] == TYPE_BOWLER_SELECTION_REQUIRED
        assert prompt["current_over"] == 2
        used_ids = [b["id"] for b in prompt["used_bowlers"]]
        assert 11 in used_ids
        eligible_ids = [b["id"] for b in prompt["eligible_bowlers"]]
        assert 11 not in eligible_ids

        # Attempt to select Siraj (11) again -> rejected
        ws.send_json({"type": TYPE_SELECT_BOWLER, "bowler_id": 11})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "bowler_already_bowled"

        # Select Mohammed Shami (10) -> accepted and next turn starts
        ws.send_json({"type": TYPE_SELECT_BOWLER, "bowler_id": 10})
        next_turn = ws.receive_json()
        assert next_turn["type"] == "turn_started"
        assert next_turn["match_state"]["bowler"]["name"] == "Mohammed Shami"


def test_over_by_over_bowler_selection_when_computer_bowls():
    """When computer is bowling and an over ends, computer automatically selects next bowler without pausing."""
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: "A",
        computer_team_chooser=lambda: "AUS",
        computer_bowler_chooser=lambda eligible: eligible[0],
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        ws.receive_json()
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})
        ws.receive_json()
        ws.send_json({"type": TYPE_CHOOSE_TOSS, "decision": "BAT"})
        ws.receive_json()  # turn_started ball 1

        # Play 6 balls (Over 1)
        for ball in range(1, 7):
            ws.send_json({"type": "submit_number", "number": 1})
            ws.receive_json()  # ack
            ws.receive_json()  # ball_result
            if ball < 6:
                ws.receive_json()  # turn_started

        # After ball 6, turn_started for Over 2 ball 1 should arrive automatically!
        turn_over_2 = ws.receive_json()
        assert turn_over_2["type"] == "turn_started"
        assert turn_over_2["match_state"]["overs"] == "1.0"


def test_first_innings_role_derivation_permutations():
    """Verify all 4 toss permutations produce correct batting_first and bowling_first."""
    cases = [
        ("A", TossDecision.BAT, "user", "computer", "computer"),
        ("A", TossDecision.BOWL, "computer", "user", "user"),
        ("B", TossDecision.BAT, "computer", "user", "user"),
        ("B", TossDecision.BOWL, "user", "computer", "computer"),
    ]

    for winner_char, decision, exp_bat_first, exp_bowl_first, exp_bowler_sel in cases:
        session = ComputerGameSession(
            skip_pre_match=False,
            toss_chooser=lambda w=winner_char: w,
            computer_team_chooser=lambda: "ENG",
            computer_decision_chooser=lambda d=decision: d,
            computer_bowler_chooser=lambda eligible: 11,
        )
        reset_standalone_computer_session(session)

        with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
            ws.receive_json()
            ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})

            if winner_char == "A":
                # User won toss
                toss_msg = ws.receive_json()
                assert toss_msg["toss_winner"] == "user"
                ws.send_json({"type": TYPE_CHOOSE_TOSS, "decision": decision.value})

            # Next message is either turn_started or bowler_selection
            next_msg = ws.receive_json()
            if exp_bowler_sel == "user":
                assert next_msg["type"] == TYPE_PRE_MATCH_STATE
                assert next_msg["stage"] == "BOWLER_SELECTION"
                assert next_msg["batting_first"] == exp_bat_first
                assert next_msg["bowling_first"] == exp_bowl_first
                assert next_msg["first_bowler_selector"] == "user"
            else:
                assert next_msg["type"] == "turn_started"
                assert next_msg["match_state"]["user_is_batting"] is (exp_bat_first == "user")


def test_reset_game_starts_fresh_pre_match_lifecycle():
    """Client sending new_game must initiate fresh pre-match lifecycle with fresh toss."""
    # First game: User won toss ('A')
    # Second game: Computer won toss ('B')
    tosses = iter(["A", "B"])
    session = ComputerGameSession(
        skip_pre_match=False,
        toss_chooser=lambda: next(tosses),
        computer_team_chooser=lambda: "AUS",
        computer_decision_chooser=lambda: TossDecision.BAT,
        computer_bowler_chooser=lambda eligible: 11,
    )
    reset_standalone_computer_session(session)

    with client.websocket_connect("/ws?mode=computer&skip_pre_match=false") as ws:
        # 1. Initial pre-match state
        init_msg = ws.receive_json()
        assert init_msg["type"] == TYPE_PRE_MATCH_STATE
        assert init_msg["stage"] == "TEAM_SELECTION"

        # 2. Select team -> First toss: User wins
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "IND"})
        toss_1 = ws.receive_json()
        assert toss_1["type"] == TYPE_PRE_MATCH_STATE
        assert toss_1["stage"] == "TOSS_DECISION"
        assert toss_1["toss_winner"] == "user"

        # Choose BAT -> Match starts
        ws.send_json({"type": TYPE_CHOOSE_TOSS, "decision": "BAT"})
        turn_1 = ws.receive_json()
        assert turn_1["type"] == "turn_started"
        assert session.match is not None

        # 3. Request new_game restart
        ws.send_json({"type": "new_game"})
        restart_msg = ws.receive_json()
        assert restart_msg["type"] == TYPE_PRE_MATCH_STATE
        assert restart_msg["stage"] == "TEAM_SELECTION"
        assert restart_msg["user_team"] is None
        assert restart_msg["toss_winner"] is None
        assert session.match is None  # Previous match discarded

        # 4. Select team again -> Second toss: Computer wins
        ws.send_json({"type": TYPE_SELECT_TEAM, "team_id": "SA"})
        toss_2 = ws.receive_json()
        assert toss_2["type"] == TYPE_PRE_MATCH_STATE
        # Computer chose BAT, so stage is BOWLER_SELECTION for user
        assert toss_2["stage"] == "BOWLER_SELECTION"
        assert toss_2["toss_winner"] == "computer"
        assert toss_2["batting_first"] == "computer"
        assert toss_2["bowling_first"] == "user"


