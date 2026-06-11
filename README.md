# Early Bird: A Dynamic Podcast Generator

A personalized podcast app that scrapes current events based on user-selected interests, performs deep research, generates conversational scripts in the style of NPR's *Up First*, and converts them to natural-sounding audio — all orchestrated through AI agents.

Built with **Next.js 15** and **Shadcn/UI** on the frontend, **Flask** with **Flask-SocketIO** on the backend, and powered by **Perplexity Sonar**, **OpenAI GPT-4o**, and **ElevenLabs** for the AI pipeline.

## Demo

> Generate a podcast in under 2 minutes: select your topics, watch as research + scripts are generated in real-time, then listen with full playback controls and a live transcript.

## Project Structure

```
backend/
├── app.py                        # Flask + SocketIO entry point
├── cli.py                        # CLI commands for headless generation
├── config.py                     # Centralized configuration
│
├── api/                          # API layer
│   ├── routes.py                 # REST endpoints
│   ├── websocket.py              # SocketIO real-time handlers
│   └── middleware.py             # Error handlers, CORS
│
├── core/                         # Business logic
│   ├── podcast_service.py        # Service coordinating pipeline + storage
│   ├── pipeline.py               # Orchestration: scrape → research → script → audio
│   └── state_manager.py          # Generation state management
│
├── agents/                       # AI agents
│   ├── scraper.py                # News scraping via Perplexity
│   ├── researcher.py             # Deep research via Perplexity
│   ├── openai_script_writer.py   # Episode script generation (GPT-4o)
│   └── perplexity.py             # Perplexity SDK wrapper
│
├── audio/                        # Audio generation
│   ├── generator.py              # ElevenLabs TTS + segment management
│   └── voices.py                 # Voice configuration utility
│
├── models/                       # Data models
│   └── article.py                # Article data model
│
├── storage/                      # File storage
│   ├── podcast_storage.py        # Podcast file + metadata management
│   └── paths.py                  # Path utilities
│
├── tests/                        # Unit + integration tests
│   └── ...
│
└── utils/                        # Shared utilities
    └── logging_config.py         # Logging configuration

client/early-bird/
├── src/app/
│   ├── page.tsx                  # Home — podcast generation UI
│   ├── previous-podcasts/        # Browse & delete past episodes
│   ├── podcast-view/[id]/        # Playback with transcript
│   └── podcast-graph/            # 3D article embedding visualization
├── src/components/
│   ├── AudioPlayer.tsx           # Segment-based audio player
│   ├── PodcastCard.tsx           # Episode card component
│   └── ui/                       # Shadcn/UI primitives
└── ...
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- API keys (see [Configuration](#configuration))

### Installation

```bash
git clone https://github.com/albert239825/EarlyBird.git
cd EarlyBird

# Backend
pip install -r requirements.txt

# Frontend
cd client/early-bird
npm install
```

### Configuration

Create a `.env` file in the project root:

```env
# Required
PERPLEXITY_API_KEY=your_perplexity_key
OPENAI_API_KEY=your_openai_key
MISTRAL_API_KEY=your_mistral_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# Optional
NYT_API_KEY=your_nyt_key
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=True
GENERATE_AUDIO=true                    # Set false to skip TTS and save credits
ELEVENLABS_MODEL_ID=eleven_flash_v2_5  # or eleven_v3 for higher quality
OPENAI_SCRIPT_MODEL=gpt-4o            # Model used for script generation
```

### Running the Application

```bash
# Terminal 1 — Backend (port 8000)
python -m backend.app

# Terminal 2 — Frontend (port 3000)
cd client/early-bird
npx next dev -p 3000
```

On macOS, `./start.sh` opens both in separate Terminal windows automatically.

## How It Works

The generation pipeline is fully automated and runs in four stages:

```
User selects topics → Scrape headlines → Deep research → Generate script → Text-to-speech
```

### 1. Event Scraping

The `NewsScraperAgent` queries **Perplexity Sonar** for trending headlines in user-selected categories (Technology, Science, Business, etc.). Multiple headlines per category are fetched in a single API call.

### 2. Deep Research

The `DeepResearchAgent` performs follow-up research on each headline via Perplexity, gathering multiple perspectives, expert opinions, statistical data, and context to ensure unbiased coverage.

### 3. Script Generation

The `OpenAIScriptWriter` generates a full episode script in a single GPT-4o call. The output is a structured JSON of utterances between a **host** and an **expert**, tagged by section (`<INTRO>`, `<STORY_N>`, `<TRANSITION_A_B>`, `<OUTRO>`). Each story targets ~3 minutes of spoken audio.

### 4. Audio Generation

The `PodcastAudioGenerator` sends each utterance to **ElevenLabs** for TTS conversion, producing individual MP3 segments. A manifest file maps segments to stories, enabling the frontend's segment-based audio player with seek and speed controls.

### 5. Real-Time Progress

The frontend polls the `/generate/status/<id>` endpoint for progress updates. As each phase completes, artifacts (titles, research docs, scripts) become available for display.

## Architecture

The backend follows a clean, layered architecture:

| Layer | Directory | Responsibility |
|-------|-----------|---------------|
| **API** | `api/` | REST endpoints, WebSocket handlers, middleware |
| **Service** | `core/` | Business logic, pipeline orchestration, state |
| **Agents** | `agents/` | Individual AI agents (scraping, research, scripting) |
| **Audio** | `audio/` | ElevenLabs TTS integration |
| **Storage** | `storage/` | File management, metadata persistence |
| **Models** | `models/` | Data structures |

Key design decisions:
- **Two-phase generation**: Phase 1 (research + script) can run without API credits for ElevenLabs; Phase 2 (audio) is optional
- **Background threading**: Generation runs in a daemon thread so the API responds immediately with a `podcast_id`
- **Segment-based playback**: Instead of one monolithic MP3, each utterance is a separate file — enabling interruptions and seek

## Testing

```bash
# Unit tests (mocked, no API keys needed)
pytest

# Integration tests (requires API keys)
pytest -m integration
```

## CLI

```bash
# Full pipeline (research + script + audio)
python -m backend.cli generate

# Script only (Phase 1)
python -m backend.cli generate-script

# Audio only (Phase 2, requires existing scripts)
python -m backend.cli generate-audio <podcast_id>

# Custom categories
python -m backend.cli generate-script --num-articles 3 --categories '["Technology", null, "Science"]'

# Generate from existing transcript
python -m backend.cli from-transcript path/to/transcript.txt
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, Shadcn/UI |
| 3D Visualization | React Three Fiber, Three.js |
| Backend | Flask, Flask-SocketIO, Python |
| News Scraping | Perplexity Sonar API |
| Script Generation | OpenAI GPT-4o |
| Text-to-Speech | ElevenLabs (eleven_flash_v2_5 / eleven_v3) |
| Research | Perplexity Sonar (deep research mode) |
| Audio Processing | pydub |
| AI Framework | LangChain (research agent) |

## Inspiration

Every morning, I start my day by listening to *Up First* by NPR. While I love its concise format, I often found that:
- Some stories didn't capture my interest
- At times, the content felt biased
- I wished I could ask follow-up questions in real time

These frustrations inspired **Early Bird** — a dynamic podcast generator that curates the news you care about and lets you interact with it.

## License

MIT
