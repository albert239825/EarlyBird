# Early Bird: A Dynamic Podcast Generator

Our app is built with **Next.js** and **ShadCN** for the frontend, and **Flask** for the backend. We've implemented an agentic workflow that collects current events based on user-selected interests, and generates a personalized podcast. The podcast generation workflow is fully automated, with each step orchestrated through AI agents.

## Project Structure

```
backend/
├── app.py                      # Flask app entry point
├── cli.py                      # CLI commands
├── config.py                   # Centralized configuration
│
├── api/                        # API layer
│   ├── routes.py               # HTTP routes
│   ├── websocket.py            # WebSocket handlers
│   └── middleware.py           # Error handlers, CORS
│
├── core/                       # Business logic
│   ├── podcast_service.py      # Main podcast generation service
│   ├── pipeline.py             # Orchestration pipeline
│   └── state_manager.py        # State management
│
├── agents/                     # AI agents
│   ├── scraper.py              # News scraping
│   ├── researcher.py           # Deep research
│   ├── script_generator.py     # Script generation
│   └── perplexity.py           # Perplexity API wrapper
│
├── audio/                      # Audio generation
│   ├── generator.py            # Audio generation
│   └── voices.py               # Voice configuration
│
├── models/                     # Data models
│   └── article.py              # Article data model
│
├── storage/                    # File storage
│   ├── podcast_storage.py      # Podcast file management
│   └── paths.py                # Path utilities
│
└── utils/                      # Shared utilities
    └── logging_config.py       # Logging configuration
```

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- Required API keys (see Configuration)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/EarlyBird.git
cd EarlyBird
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Install frontend dependencies:**
```bash
cd client/early-bird
npm install
```

### Configuration

Create a `.env` file in the project root with the following API keys:

```env
# Required API Keys
PERPLEXITY_API_KEY=your_perplexity_key
OPENAI_API_KEY=your_openai_key
MISTRAL_API_KEY=your_mistral_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# Optional
NYT_API_KEY=your_nyt_key

# Flask Configuration (optional)
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=True

# Audio Generation (optional, defaults to true)
# Set to false to skip audio generation and save ElevenLabs credits
# Useful for testing scripts and research without generating audio
GENERATE_AUDIO=true

# ElevenLabs Model (optional, defaults to eleven_flash_v2_5)
# Options: eleven_flash_v2_5 (fast, low latency), eleven_v3 (high quality)
ELEVENLABS_MODEL_ID=eleven_flash_v2_5

# OpenAI Script Model (optional, defaults to gpt-4o)
# Options: gpt-4o, gpt-4-turbo, gpt-3.5-turbo, etc.
OPENAI_SCRIPT_MODEL=gpt-4o
```

### Running the Application

**Start both backend and frontend:**
```bash
# From project root - opens two separate Terminal windows
./start.sh
# or
npm start
```

The script automatically:
- Opens a Terminal window for the backend (uses `.venv/bin/python`)
- Opens a Terminal window for the frontend (runs `npx next dev -p 3000`)

## Running Tests

### Backend (pytest)

1. **Install Python dependencies (includes pytest):**

```bash
pip install -r requirements.txt
```

2. **Run unit tests (mocked by default):**

```bash
pytest
```

3. **Run integration tests (real external API calls):**

Integration tests are behind the `integration` marker and are **skipped by default**. Run them explicitly with:

```bash
pytest -m integration
```

4. **Required env vars for integration tests:**

- `OPENAI_API_KEY` (required by the OpenAI script writer integration smoke test)
- `PERPLEXITY_API_KEY` (required once we add Perplexity-backed integration tests)

**Using the CLI:**
```bash
# Generate a new podcast (full pipeline: scripts + audio)
python -m backend.cli generate

# Generate scripts only (Phase 1) - creates new podcast
python -m backend.cli generate-script

# Generate scripts for existing podcast
python -m backend.cli generate-script podcast_20260112_100034_2d5ffbab

# Generate scripts with custom categories (use null for random)
python -m backend.cli generate-script --num-articles 3 --categories '["Technology", null, "Squash (Sport)"]'

# Generate audio for existing podcast (Phase 2)
python -m backend.cli generate-audio podcast_20260112_100034_2d5ffbab

# Generate audio from existing transcript
python -m backend.cli from-transcript path/to/transcript.txt
```

## Workflow

1. **Event Scraping:**  
   We begin by launching a request to **Perplexity Sonar** to scrape current events based on predefined categories. The result is a list of headlines that represent the most relevant news stories.

2. **Deep Research:**  
   The headlines are sent to a **Perplexity Sonar agent** for thorough research, gathering additional information and context about each story.

3. **Podcast Script Generation:**  
   Specialized **Mistral agents** (Expert and Host) collaborate to generate the podcast script, creating a natural, flowing conversation.

4. **Text-to-Speech:**  
   The script is sent to **ElevenLabs** for text-to-speech conversion, creating natural-sounding audio.

5. **User Interaction:**  
   The generated audio is presented to the user, who can interrupt at any point to ask follow-up questions. The Expert Agent responds in real time.

## Architecture

The backend follows a clean, layered architecture:

- **API Layer** (`api/`): Handles HTTP requests and WebSocket connections
- **Service Layer** (`core/`): Contains business logic and orchestration
- **Agent Layer** (`agents/`): Individual AI agents for specific tasks
- **Storage Layer** (`storage/`): File management and persistence
- **Models** (`models/`): Data structures and domain models

This separation ensures:
- **Testability**: Each layer can be tested independently
- **Maintainability**: Changes in one layer don't affect others
- **Clarity**: Clear responsibilities for each component
- **Extensibility**: Easy to add new features

## Inspiration

Every morning, I start my day by listening to *Up First* by NPR. While I love its concise format, I often found that:
- Some stories didn't capture my interest.
- At times, the content felt biased.
- I wished I could ask follow-up questions in real time.

These frustrations inspired us to build **Early Bird**—a dynamic podcast generator that not only curates the news you care about but also lets you interact with it.

## What it does

- Curates a personalized podcast based on current events
- Allows real-time interaction through dynamic interruptions and expert responses
- Provides a clean, modern interface for podcast consumption

## How we built it

- **Front End:**  
  - **Next.js** with **ShadCN** for a responsive, modern user interface.
- **Search:**  
  - Integrated **Perplexity Sonar** to fetch up-to-date news.
- **Response Generation:**  
  - Employed **Mistral** for low-latency, dynamic response generation.
- **Backend:**  
  - Built using **Flask** in Python with a clean, layered architecture.
- **Voice Generation:**  
  - Leveraged **ElevenLabs** to convert scripts into natural-sounding audio.

## Challenges we ran into

- **Building an Interruption System:**  
  - Initially, we generated a single MP3 file for each podcast, which made it difficult to incorporate interactivity. This led to challenges in ensuring real-time responsiveness to user questions.
- **Pivoting for Reactivity:**  
  - We quickly learned that listeners needed to interact with the content. This realization forced us to reengineer our pipeline to support dynamic interruptions and follow-up responses.

## Accomplishments that we're proud of

- Successfully implementing a fully agentic pipeline for podcast generation
- Creating a responsive, immersive experience that gives users control over their podcast content
- Building a clean, maintainable architecture that's easy to understand and extend

## What we learned

- The importance of reactivity in content delivery: Podcasts can be more engaging when listeners have the ability to interact with the content
- The power of automation: By using AI agents, we were able to automate complex workflows
- Clean architecture matters: Separating concerns makes the codebase easier to maintain and extend

## What's next for Early Bird

- Expanding personalization options with user interest profiles
- Improving the accuracy and depth of the research agents
- Further enhancing interactivity with more dynamic user feedback mechanisms
- Adding support for multiple languages and voices

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your license here]
