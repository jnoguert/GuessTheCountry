import re
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List

from .. import leaderboard_db as db
from ..scoring import compute_score, MAX_GUESSES, MAX_UNLOCKS

router = APIRouter(prefix='/api', tags=['leaderboard'])

USERNAME_RE = re.compile(r'^[A-Za-z0-9_\-]{3,20}$')


class ScoreSubmission(BaseModel):
    username: str
    token: str = Field(min_length=8, max_length=128)
    puzzle_id: str
    score: int
    guesses: int = Field(ge=0, le=MAX_GUESSES)
    unlocks: int = Field(ge=0, le=MAX_UNLOCKS)
    won: bool


class TodayEntry(BaseModel):
    username: str
    score: int
    guesses: int
    unlocks: int
    won: int


class AlltimeEntry(BaseModel):
    username: str
    total_score: int
    wins: int
    games: int


def _today_puzzle_id() -> str:
    return datetime.now(timezone.utc).date().isoformat()


@router.post('/scores', status_code=201)
async def submit_score(sub: ScoreSubmission):
    if not USERNAME_RE.match(sub.username):
        raise HTTPException(status_code=400, detail='Invalid username (3-20 chars: letters, digits, _ or -)')

    if sub.puzzle_id != _today_puzzle_id():
        raise HTTPException(status_code=400, detail='Scores can only be submitted for today')

    # The score must be exactly what the game rules produce for the
    # reported guesses/unlocks - anything else is a forged payload.
    wrong_guesses = sub.guesses - 1 if sub.won else sub.guesses
    expected = compute_score(sub.unlocks, max(0, wrong_guesses), sub.won)
    if sub.score != expected:
        raise HTTPException(status_code=400, detail='Score does not match game rules')

    try:
        db.submit_score(sub.username, sub.token, sub.puzzle_id, sub.score,
                        sub.guesses, sub.unlocks, sub.won)
    except db.UsernameTaken:
        raise HTTPException(status_code=409, detail='Username already taken')
    except db.AlreadySubmitted:
        raise HTTPException(status_code=409, detail='Score already submitted for today')

    return {'ok': True}


@router.get('/leaderboard/today', response_model=List[TodayEntry])
async def get_today():
    return db.leaderboard_today(_today_puzzle_id())


@router.get('/leaderboard/alltime', response_model=List[AlltimeEntry])
async def get_alltime():
    return db.leaderboard_alltime()
