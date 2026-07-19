# Guess the Country 🌍

A daily word-puzzle game where you guess countries based on censored Wikipedia excerpts. Similar to Wordle, but for geography!

## Features

- 🌐 **Multilingual**: English, Catalan, and Spanish
- 🎨 **Modern UI**: Clean, responsive design inspired by Worldle
- 🌙 **Dark Mode**: Light/dark theme toggle
- 📊 **Progressive Reveals**: Start with one censored paragraph, reveal more with each wrong guess
- 🎯 **Smart Censorship**: Automatically redacts country names, capitals, bordering countries, demonyms, and famous mountains
- 💾 **Persistent State**: Your progress is saved in localStorage

## Getting Started (Quickest Way - Docker!)

### Docker Setup (Recommended)

The easiest way to run the entire app with one command:

```bash
# Clone the repo
git clone https://github.com/jnoguert/GuessTheCountry.git
cd GuessTheCountry

# Start everything
docker-compose up --build
```

Then open **http://localhost:8000** — the whole game (frontend + API) is served
from that single port, so it works identically on your machine, in GitHub
Codespaces (just open the forwarded port 8000), or on any cloud host.

- **Game**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

**Useful commands:**
```bash
make help          # See all available commands
make up            # Start services
make down          # Stop services
make logs          # View logs
make rebuild       # Rebuild and restart
make clean         # Clean everything
```

### Manual Development Setup

If you prefer to run without Docker:

#### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd guess_the_country
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd ../frontend
   npm install
   ```

### Building the Game Data

First, generate the countries database from Wikidata and Wikipedia:

```bash
cd backend
python -m pipeline.build
```

This will:
1. Fetch country metadata from Wikidata (stage A)
2. Fetch lexical data (labels, aliases, demonyms) in EN/CA/ES (stage B)
3. Fetch Wikipedia articles and extract paragraphs (stage C1)
4. Apply smart censorship to the articles (stage C2)
5. Generate `data/countries.json` and `data/daily_order.json`

The process takes a few minutes and caches Wikipedia responses locally to avoid redundant fetches.

### Running Locally

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## How the Censorship Works

The pipeline automatically identifies and redacts:
- The country's own name and aliases
- The capital city
- Bordering countries and their demonyms
- The country's most famous mountain
- Plurals, genders, and case forms in Spanish and Catalan

Censorship is applied via a per-country regex that respects word boundaries, so "Niger" won't accidentally redact inside "Nigeria".

## Project Structure

```
guess_the_country/
├── backend/
│   ├── app/                 # FastAPI application
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── data_loader.py
│   │   ├── puzzle.py
│   │   └── routers/
│   ├── pipeline/            # Data generation pipeline
│   │   ├── wikidata_core.py
│   │   ├── wikidata_lexical.py
│   │   ├── wikipedia_fetch.py
│   │   ├── censor.py
│   │   └── build.py
│   ├── data/
│   │   ├── countries.json   # Final game data
│   │   └── daily_order.json # Daily rotation
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── i18n/            # Translation files
│   ├── index.html
│   └── package.json
└── README.md
```

## API Endpoints

- `GET /api/puzzle/{lang}` — Get today's puzzle in the specified language
- `POST /api/guess` — Submit a guess
- `GET /api/countries/{lang}` — Get list of countries for autocomplete
- `GET /health` — Health check

## Technologies

**Backend:**
- FastAPI for the REST API
- Python for the data pipeline
- Wikidata SPARQL and Wikipedia API for content

**Frontend:**
- React 18 with TypeScript
- Vite for fast builds
- Tailwind CSS for styling

## Performance

The entire game runs as a static dataset loaded once at startup:
- ~195 countries × 3 languages × ~5 paragraphs
- Total dataset: ~500KB JSON, loads instantly

No database queries at runtime — pure in-memory lookup.

## Future Improvements

- [ ] Leaderboard / stats tracking
- [ ] Difficulty levels (easy/hard)
- [ ] More languages
- [ ] Mobile app version
- [ ] Weekly/monthly challenges

## License

MIT

## Contributing

Pull requests welcome! Please note:
- The censorship pipeline is the complex bit — test edge cases like Niger/Nigeria thoroughly
- Language translations should be complete across all three languages
- UI changes should respect the light/dark theme toggle
