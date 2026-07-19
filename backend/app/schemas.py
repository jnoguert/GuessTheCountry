from pydantic import BaseModel
from typing import Optional, List


class PuzzleResponse(BaseModel):
    puzzle_id: str
    max_guesses: int
    paragraphs: List[str]


class GuessRequest(BaseModel):
    lang: str
    puzzle_id: str
    guess_number: int
    guess_text: str


class GuessResponse(BaseModel):
    correct: bool
    game_over: bool
    next_paragraph: Optional[str] = None
    answer: Optional[dict] = None


class CountryItem(BaseModel):
    name: str
    iso2: str
