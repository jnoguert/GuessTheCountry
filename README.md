# Redactica 🌍

**Redactica** is a daily puzzle game where you guess a country from a censored
excerpt of its Wikipedia article — think Wordle, but for geography. Every
player gets the same secret country each day, in English, Català, or Español.

**▶️ Play now: https://jnoguert.github.io/Redactica/**

## How It Works

1. Read the censored paragraph. Every country name, capital, neighboring
   country, demonym, language, currency and other geographic giveaway is
   blacked out (`███`). The width of each black-out is deliberately
   scrambled by ±2-3 characters, so you can't count letters to narrow
   down the answer — a block never shows the hidden word's real length.
2. You have **5 guesses** and **3 hint unlocks**. You start with 1 paragraph
   and can unlock up to 3 more (4 total) — but the fewer hints you use, the
   higher your score.
3. **Scoring** is inverse: 0 hints → 100 pts, 1 → 70, 2 → 50, 3 → 30, minus
   10 per wrong guess (min 10 on a win, 0 on a loss).
4. Switching language mid-game **costs 1 hint unlock** and restarts you from
   paragraph 1 in the new language — no free peeking. It's free once the
   game is over.
5. Win or lose, the **full uncensored article** is revealed at the end so
   you can read about the country.
6. Come back daily to build a **streak**, tracked locally in your browser.
7. Optional **Easy Mode** (🗺️ button) opens an interactive world map where
   you can mark countries as considering (green) or discarded (red) as a
   scratchpad while you reason — it never submits a guess for you, you
   still type your answer in the box as always. Turning it on requires
   confirming a warning, since it **halves your score for the day** and
   can't be turned back off until the next day's puzzle.

The in-app **❓ How to Play** button (shown automatically on first visit)
covers all of this with the exact numbers.

## Features

- 🌐 **Multilingual**: English, Català, Español — same daily country in all three
- 🎯 **Smart censorship**: names, capitals, borders, demonyms, languages,
  currencies, and other proper nouns/toponyms are automatically redacted
  from real Wikipedia text
- 💡 **Hint system**: unlock up to 3 extra paragraphs; fewer hints = higher score
- 🗺️ **Easy Mode**: an interactive world map for marking candidate
  countries, at half score, opt-in fresh every day
- 🏆 **Inverse scoring** + day streak, both saved locally
- 📖 **Full reveal**: read the uncensored article once the game ends
- 🎨 **Modern UI** with light/dark theme
- 📱 **Fully client-side**: no backend, no server — the whole game is a single
  static bundle, deployable to GitHub Pages or any static host

## Architecture

The entire game — daily country selection, guess checking, hints, scoring —
runs **in the browser** against a single static file, `game.json`, generated
offline by a Python pipeline. There is no live server involved in gameplay.

```
Wikidata + Wikipedia  →  Python pipeline  →  game.json  →  React app
     (offline, run occasionally)              (bundled with the frontend build)
```

- **`frontend/`** — React + TypeScript + Vite + Tailwind. `src/lib/engine.ts`
  implements the game rules (daily rotation, guess matching, i18n text) purely
  against `game.json`; `src/lib/api.ts` wraps it in an API-shaped interface so
  the rest of the app doesn't care where answers come from.
- **`backend/pipeline/`** — offline data pipeline: queries Wikidata for
  country metadata (capital, borders, demonyms, languages, currency, highest
  point), fetches Wikipedia article text per language, and censors it with a
  layered regex/proper-noun engine. Outputs `countries.json` and the slim
  `frontend/public/game.json` the app actually ships.

There is no runtime backend — the pipeline runs occasionally and offline, and
its output is committed to the repo.

## Getting Started

### Just play

Open **https://jnoguert.github.io/Redactica/** — nothing to install.

### Run locally

**Frontend** — this is all you need to work on or play the game locally, since
`game.json` already ships in the repo:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

**Pipeline** (optional — only needed to regenerate the dataset or run the
Python test suite):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
```

## Regenerating the Game Data

The repo already ships a complete, built dataset (`backend/data/countries.json`
and `frontend/public/game.json`), so this step is only needed if you want to
refresh the content (e.g. Wikipedia articles changed) or tweak the censorship
rules.

```bash
cd backend
python -m pipeline.build
```

This runs, in order:
1. **Wikidata core** — country roster + capital, highest point, ISO codes,
   currency, bordering countries (SPARQL)
2. **Wikidata lexical** — labels/aliases/demonyms/official languages in
   en/ca/es for every entity referenced above (batched `wbgetentities`)
3. **Wikipedia fetch** — article extracts per language, split into
   paragraphs, cached locally (resumable — re-runs skip already-fetched
   articles and only pull what's missing)
4. **Censorship** — layered redaction (see below), producing exactly 4
   paragraphs per country per language (1 starting + 3 unlockable hints)
5. **Daily order** — a fixed, seeded shuffle of all fully-playable countries,
   so every day serves a different, non-alphabetical answer with no
   short-term repeats
6. **`game.json` export** — the slim, client-side dataset the frontend ships;
   unplayable countries keep only their name (for autocomplete), and every
   playable country carries both the censored and original (`plain`) text

The pipeline caches all Wikidata/Wikipedia responses under `backend/data/raw/`,
so re-runs after a tweak to the censorship logic are near-instant — only
`censor.py`'s output changes, no network calls are repeated.

## How the Censorship Works

Censorship runs in layered passes over the real Wikipedia text:

1. **Known-term pass** — the country's own name/aliases, capital, bordering
   countries (+ their demonyms), the country's own demonym (with
   language-specific plural/gender inflection), official/spoken languages,
   currency name, and highest point/mountain — all pulled from Wikidata,
   matched with word-boundary-safe regex (so "Niger" never matches inside
   "Nigeria").
2. **Proper-noun pass** — every remaining capitalized word appearing
   mid-sentence anywhere in the article (and that same word even where it
   starts a sentence) gets redacted too — this catches regions, historical
   entities, and other place names Wikidata doesn't model explicitly (e.g.
   "Catalonia", "the county of Urgell").
3. **Name-stem pass** — lowercase words derived from the country's own name
   (e.g. Spanish "austríaco", Catalan "sud-africà", or compounds like
   "afrobolivians") are caught by substring matching on normalized stems.

Every block produced by any of the three passes above then goes through one
more step:

4. **Length obfuscation** — the number of `█` characters shown is the real
   word's length **shifted by 2 or 3 characters**, direction chosen at
   random per occurrence (`fuzz_block_length` in `censor.py`). Without this,
   a block's width directly tells you how many letters the hidden word has
   — a huge shortcut for a 4-6 letter country name. The shift is seeded
   (`CENSOR_RNG_SEED`), so a full rebuild with unchanged inputs always
   produces byte-identical output — useful for reviewing diffs and for the
   test suite, while still being unpredictable to a player who only sees
   the rendered blocks.

A data-quality test suite (`test_real_data.py`) verifies the *built* dataset
directly: no country's own name leaks into its own paragraphs, every
playable country has exactly 4 paragraphs and a non-empty capital in all
three languages, the daily rotation contains no duplicates and isn't
alphabetical, and a simulated year of days always produces a playable puzzle.

## Easy Mode Map

`WorldMapModal` renders an interactive, clickable choropleth (via
[react-simple-maps](https://www.react-simple-maps.io/)) using
[world-atlas](https://www.npmjs.com/package/world-atlas)'s 50m-resolution
TopoJSON — good country-shape detail at ~740KB, far smaller than the 10m
tier (14+ MB) that level of detail isn't needed for a click target. Each
map region carries a numeric ISO 3166-1 id; `frontend/src/assets/iso2-to-map-id.json`
is a small, pre-generated crosswalk from our own `iso2` codes to those
numeric ids (produced once from the `i18n-iso-countries` package's
conversion table, which is **not** a runtime dependency — only its output
is committed). Validated against the real dataset: 191 of 192 playable
countries resolve to a clickable region; Tuvalu's landmass is too small to
render even at 50m resolution, so it remains guessable by text as normal,
just not clickable on the map. Greenland renders as its own large,
separate landmass (id `304`) but isn't itself one of our 194 playable
countries — since our game already models it as part of Denmark's
sovereign state (see the Denmark fix above), clicking Greenland is
manually mapped to mark Denmark instead of being dead space.

**Interaction is mode-based, not click-to-cycle**: three buttons
(Consider / Discard / Unmark) select the active mode, and every
subsequent country click applies that mode directly — so marking many
countries the same way is one click each, not up to three. Hover only
thickens a country's border for feedback; no color (blue or otherwise)
is ever applied on hover or press, only on an actual click.

The whole map — component, `react-simple-maps`, and the topology data —
is loaded via `React.lazy()`, so it's absent from the main bundle entirely
until a player actually turns on Easy Mode (confirmed by build output: the
main chunk stays ~180KB, the map lazy-chunk is a separate ~860KB/272KB
gzipped download).

## Project Structure

```
redactica/
├── .github/workflows/
│   └── deploy-pages.yml      # Builds frontend + game.json, deploys to GitHub Pages
├── backend/                  # Offline data pipeline (no runtime server)
│   ├── pipeline/              # Data generation
│   │   ├── wikidata_core.py
│   │   ├── wikidata_lexical.py
│   │   ├── wikipedia_fetch.py
│   │   ├── censor.py          # Layered censorship + geo_adjectives.py lexicon
│   │   └── build.py
│   ├── data/
│   │   ├── countries.json     # Full dataset (censored + plain text)
│   │   ├── daily_order.json   # Shuffled rotation of playable countries
│   │   └── raw/               # Cached Wikidata/Wikipedia API responses
│   ├── tests/                 # pytest suite (censorship, rotation, data quality)
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── game.json          # Client-side dataset (generated, bundled at build time)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── assets/
│   │   │   └── iso2-to-map-id.json  # iso2 -> world-atlas numeric id crosswalk
│   │   ├── components/        # LanguageSelect, HintPanel, ResultModal,
│   │   │                       InstructionsModal, LanguageWarningModal,
│   │   │                       EasyModeWarningModal, WorldMapModal, ...
│   │   ├── lib/
│   │   │   ├── engine.ts      # Game rules, run entirely client-side
│   │   │   ├── api.ts         # API-shaped wrapper around engine.ts
│   │   │   ├── score.ts       # Inverse scoring + Easy Mode halving
│   │   │   └── storage.ts     # localStorage: game state, streak, theme
│   │   └── i18n/               # en / ca / es translation strings
│   └── package.json
└── README.md
```

## Testing

```bash
cd backend
.venv\Scripts\activate
python -m pytest tests/ -v
```

The suite covers: censorship edge cases (Niger/Nigeria, Guinea family,
accents, elision, proper nouns, name-stem matching, geographic-adjective
scrubbing, phonetic/IPA stripping, lede trimming) and data-quality checks
against the real built dataset (no name leaks, exactly 4 paragraphs, capitals
and ISO codes present, a shuffled rotation, and a playable puzzle every day
for a simulated year).

```bash
cd frontend
npm run build   # type-checks and builds; fails on any TypeScript error
```

## Deployment

- **GitHub Pages** (live site): `.github/workflows/deploy-pages.yml` builds
  the frontend (with `game.json` bundled in) and deploys on every push to
  `main`. Requires **Settings → Pages → Source: GitHub Actions** to be set
  once per repo.
- **Any static host**: the built `frontend/dist/` is a plain static bundle —
  drop it on Netlify, Cloudflare Pages, S3, or a plain web server.

## Optional Add-ons (branches)

A couple of features were built but are kept off `main` to keep the core
game simple:

- **`feature/leaderboard`** — usernames, daily scores, and today/all-time
  rankings backed by a FastAPI service + SQLite. Requires a real hosted
  backend (not compatible with pure static hosting like GitHub Pages), so it
  reintroduces the server-side code that `main` no longer ships.
- **`feature/android-apk`** — Capacitor packaging + a CI workflow that
  builds a downloadable, fully offline Android APK from the same frontend.

Merge either into `main` (`git merge feature/<name>`) when you're ready to
use them.

## License

MIT

## Contributing

- The censorship pipeline is the most delicate part — test edge cases like
  Niger/Nigeria and the Guinea family thoroughly before changing it.
- Keep all three language translations in sync (`frontend/src/i18n/*.json`).
- Run `python -m pytest tests/ -v` and `npm run build` before submitting changes.
