from fastapi import APIRouter, HTTPException
from typing import List
from ..schemas import PuzzleResponse, GuessRequest, GuessResponse
from .. import puzzle as puzzle_service
from ..data_loader import get_loader

router = APIRouter(prefix='/api', tags=['puzzle'])


@router.get('/puzzle/{lang}', response_model=PuzzleResponse)
async def get_puzzle(lang: str):
    puzzle = puzzle_service.get_todays_puzzle(lang)
    if not puzzle:
        raise HTTPException(status_code=404, detail='Puzzle not found')

    first_paragraph = puzzle['paragraphs'][0] if puzzle['paragraphs'] else ''
    return PuzzleResponse(
        puzzle_id=puzzle['puzzle_id'],
        max_guesses=puzzle['max_guesses'],
        paragraphs=[first_paragraph]
    )


@router.post('/guess', response_model=GuessResponse)
async def submit_guess(request: GuessRequest):
    result = puzzle_service.check_guess(request.lang, request.puzzle_id, request.guess_text)

    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])

    day_index = puzzle_service.today_day_index()
    loader = get_loader()
    qid = loader.get_daily_qid(day_index)

    if not qid:
        raise HTTPException(status_code=404, detail='Puzzle not found')

    country = loader.get_country(qid)
    if not country:
        raise HTTPException(status_code=404, detail='Puzzle not found')

    i18n_data = country['i18n'].get(request.lang, {})
    paragraphs = i18n_data.get('paragraphs', [])

    if result['correct']:
        return GuessResponse(
            correct=True,
            game_over=True,
            answer={
                'name': i18n_data.get('name', ''),
                'capital': i18n_data.get('capital', ''),
                'iso2': country.get('iso2', '')
            }
        )

    # Return next paragraph if available
    next_para_idx = request.guess_number
    game_over = next_para_idx >= len(paragraphs)
    next_paragraph = None if game_over else paragraphs[next_para_idx]

    answer = None
    if game_over:
        answer = {
            'name': i18n_data.get('name', ''),
            'capital': i18n_data.get('capital', ''),
            'iso2': country.get('iso2', '')
        }

    return GuessResponse(
        correct=False,
        game_over=game_over,
        next_paragraph=next_paragraph,
        answer=answer
    )


@router.get('/countries/{lang}')
async def get_countries(lang: str):
    loader = get_loader()
    countries = loader.get_all_countries_by_lang(lang)
    return countries
