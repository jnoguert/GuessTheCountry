from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from ..schemas import PuzzleResponse, GuessRequest, GuessResponse
from .. import puzzle as puzzle_service
from ..data_loader import get_loader

router = APIRouter(prefix='/api', tags=['puzzle'])


def _day_index_from_puzzle_id(puzzle_id: str) -> int:
    """Puzzle ids are ISO dates; derive the rotation index from them so a
    guess is always checked against the puzzle the player is looking at,
    even right after midnight."""
    try:
        puzzle_date = date.fromisoformat(puzzle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid puzzle id')
    return (puzzle_date - puzzle_service.EPOCH_DATE.date()).days


@router.get('/puzzle/{lang}', response_model=PuzzleResponse)
async def get_puzzle(lang: str, day: Optional[int] = Query(default=None)):
    """Return today's puzzle. Pass ?day=N to simulate another day."""
    puzzle = puzzle_service.get_todays_puzzle(lang, day_index=day)
    if not puzzle or not puzzle['paragraphs']:
        raise HTTPException(status_code=404, detail='Puzzle not found')

    return PuzzleResponse(
        puzzle_id=puzzle['puzzle_id'],
        max_guesses=puzzle['max_guesses'],
        paragraphs=[puzzle['paragraphs'][0]]
    )


@router.post('/guess', response_model=GuessResponse)
async def submit_guess(request: GuessRequest):
    day_index = _day_index_from_puzzle_id(request.puzzle_id)

    country = puzzle_service.get_daily_country(day_index, request.lang)
    if not country or request.lang not in country.get('i18n', {}):
        raise HTTPException(status_code=404, detail='Puzzle not found')

    result = puzzle_service.check_guess(request.lang, request.guess_text, day_index=day_index)
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])

    i18n_data = country['i18n'][request.lang]
    paragraphs = i18n_data.get('paragraphs', [])

    answer_payload = {
        'name': i18n_data.get('name', ''),
        'capital': i18n_data.get('capital', ''),
        'iso2': country.get('iso2', '')
    }

    if result['correct']:
        return GuessResponse(correct=True, game_over=True, answer=answer_payload)

    # Wrong guess: reveal the next paragraph if any remain
    next_para_idx = request.guess_number
    game_over = next_para_idx >= len(paragraphs)
    next_paragraph = None if game_over else paragraphs[next_para_idx]

    return GuessResponse(
        correct=False,
        game_over=game_over,
        next_paragraph=next_paragraph,
        answer=answer_payload if game_over else None
    )


@router.get('/countries/{lang}')
async def get_countries(lang: str):
    loader = get_loader()
    return loader.get_all_countries_by_lang(lang)
