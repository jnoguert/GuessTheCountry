from fastapi import APIRouter, HTTPException
from ..schemas import PuzzleResponse, GuessRequest, GuessResponse
from .. import puzzle as puzzle_service
from ..data_loader import get_loader

router = APIRouter(prefix='/api', tags=['puzzle'])


@router.get('/puzzle/{lang}', response_model=PuzzleResponse)
async def get_puzzle(lang: str):
    puzzle = puzzle_service.get_todays_puzzle(lang)
    if not puzzle or not puzzle['paragraphs']:
        raise HTTPException(status_code=404, detail='Puzzle not found')

    return PuzzleResponse(
        puzzle_id=puzzle['puzzle_id'],
        max_guesses=puzzle['max_guesses'],
        paragraphs=[puzzle['paragraphs'][0]]
    )


@router.post('/guess', response_model=GuessResponse)
async def submit_guess(request: GuessRequest):
    country = puzzle_service.get_daily_country()
    if not country or request.lang not in country.get('i18n', {}):
        raise HTTPException(status_code=404, detail='Puzzle not found')

    result = puzzle_service.check_guess(request.lang, request.puzzle_id, request.guess_text)
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
