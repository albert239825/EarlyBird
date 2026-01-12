# Integration Test Guide: Phase 1 & Phase 2

## Overview

This guide explains how Phase 1 and Phase 2 tests work, how to run integration tests, and how to persist test outputs for inspection.

## Test Structure

### Phase 1 Tests (`test_pipeline_phase1_assets.py`)

**Purpose**: Generate research documents and script files (no audio)

**What it generates**:
- `podcast.json` - Podcast metadata
- `research/story_*.md` - Research documents per story
- `script/story_*.json` - Script utterances per story

**Test Types**:
1. **Unit Test** (`test_generate_research_and_script_assets_writes_files`):
   - Mocks all API calls (Perplexity, OpenAI)
   - Fast, no external dependencies
   - Verifies file structure and state updates

2. **Integration Test** (`test_generate_research_and_script_assets_integration_full_pipeline`):
   - Uses real Perplexity API for headlines
   - Uses real OpenAI API for script generation
   - Marked with `@pytest.mark.integration`
   - Generates actual research and scripts

### Phase 2 Tests (`test_phase2_manifest_playback.py`)

**Purpose**: Generate audio segments from scripts and create manifest

**What it generates**:
- `audio/pregen/seg_*.mp3` - Audio segments (one per utterance)
- `manifest.json` - Manifest with segment metadata

**Test Types**:
1. **Unit Tests** (multiple):
   - `test_audio_generator_*` - Audio generation with mocked ElevenLabs
   - `test_storage_*` - Storage operations
   - `test_pipeline_generate_audio_segments_and_manifest_*` - Pipeline with dummy audio generator
   - `test_get_manifest_*`, `test_get_segment_*` - API route tests

2. **Integration Test** (`test_phase2_manifest_playback_integration_full`):
   - Uses pre-generated Phase 1 fixtures (via `_setup_phase2_test_fixtures`)
   - Uses real ElevenLabs API for audio generation
   - Generates actual MP3 files
   - Creates and validates manifest.json

## Running Integration Tests

### Basic Usage

Integration tests are **skipped by default**. To run them:

```bash
# Run all integration tests
pytest -m integration

# Run only Phase 1 integration test
pytest -m integration backend/tests/test_pipeline_phase1_assets.py::test_generate_research_and_script_assets_integration_full_pipeline

# Run only Phase 2 integration test
pytest -m integration backend/tests/test_phase2_manifest_playback.py::test_phase2_manifest_playback_integration_full
```

### Required Environment Variables

**Phase 1 Integration Test**:
- `PERPLEXITY_API_KEY` - For fetching headlines and research
- `OPENAI_API_KEY` - For script generation

**Phase 2 Integration Test**:
- `ELEVENLABS_API_KEY` - For audio generation
- (Phase 1 outputs are pre-generated as fixtures, so no API keys needed for that)

### Example: Running Phase 2 Integration Test

```bash
export ELEVENLABS_API_KEY="your_key_here"
pytest -m integration backend/tests/test_phase2_manifest_playback.py::test_phase2_manifest_playback_integration_full -v
```

## Persisting Test Outputs

### Automatic Persistence

The test suite includes an **automatic output persistence mechanism** via the `persist_test_output` fixture in `conftest.py`.

**How it works**:
1. Use `--keep-test-output` pytest flag
2. Run integration tests (marked with `@pytest.mark.integration`)
3. If test passes, outputs are automatically copied to:
   ```
   backend/tests/test_output/<test_name>_<timestamp>/
   ```

**Example**:
```bash
export ELEVENLABS_API_KEY="your_key_here"
pytest -m integration --keep-test-output backend/tests/test_phase2_manifest_playback.py::test_phase2_manifest_playback_integration_full -v
```

After the test passes, you'll see:
```
============================================================
Test output persisted to: backend/tests/test_output/test_phase2_manifest_playback_integration_full_20240115_143022
============================================================
```

### What Gets Persisted

**Phase 1 Integration Test Output**:
```
test_output/
└── test_generate_research_and_script_assets_integration_full_pipeline_<timestamp>/
    ├── podcast.json
    ├── research/
    │   └── story_0.md
    └── script/
        └── story_0.json
```

**Phase 2 Integration Test Output**:
```
test_output/
└── test_phase2_manifest_playback_integration_full_<timestamp>/
    ├── podcast.json
    ├── research/
    │   ├── story_0.md
    │   └── story_1.md
    ├── script/
    │   ├── story_0.json
    │   └── story_1.json
    ├── audio/
    │   └── pregen/
    │       ├── seg_0001.mp3
    │       ├── seg_0002.mp3
    │       └── ... (more segments)
    └── manifest.json
```

### Manual Persistence (Alternative)

If you want to manually save outputs, you can:

1. **Use the test's tmp_podcast_dir directly**:
   - The test uses a temporary directory that's cleaned up after
   - You can inspect it during test execution (add breakpoints or print statements)

2. **Copy files manually in the test**:
   ```python
   import shutil
   from pathlib import Path
   
   # In your test
   output_dir = Path("backend/tests/test_output/manual_copy")
   shutil.copytree(tmp_podcast_dir, output_dir)
   ```

3. **Use PodcastStorage.save_manifest()**:
   ```python
   from backend.storage.podcast_storage import PodcastStorage
   
   storage = PodcastStorage(backend_root)
   storage.save_manifest(podcast_dir, manifest)
   ```

## Phase 2 Integration Test Details

### Test Flow

1. **Setup Phase 1 Fixtures** (`_setup_phase2_test_fixtures`):
   - Creates 2 stories with pre-generated scripts and research
   - Story 0: 4 utterances (AI technology topic)
   - Story 1: 3 utterances (renewable energy topic)
   - Total: 7 segments to generate

2. **Initialize Pipeline & Audio Generator**:
   - Creates `PodcastPipeline` instance
   - Creates `PodcastAudioGenerator` with real ElevenLabs client

3. **Generate Audio Segments**:
   - Reads script files from `script/story_*.json`
   - For each utterance, calls ElevenLabs API
   - Saves MP3 files to `audio/pregen/seg_*.mp3`
   - Records duration and metadata

4. **Create Manifest**:
   - Builds manifest.json with segment metadata:
     - `segment_id`: Sequential IDs (seg_0001, seg_0002, ...)
     - `utterance_id`: From script (u0, u1, ...)
     - `story_index`: Which story the segment belongs to
     - `speaker`: "host" or "expert"
     - `text`: The utterance text
     - `url`: API endpoint for playback
     - `duration_ms`: Audio duration in milliseconds
     - `source`: "pregen" (pre-generated)

5. **Validation**:
   - Verifies all MP3 files exist and are non-empty
   - Validates manifest structure
   - Checks segment ordering
   - Optionally validates MP3 files with pydub (if available)
   - Tests manifest save/load

### Expected Output Structure

```json
{
  "podcast_id": "podcast_test_...",
  "segments": [
    {
      "segment_id": "seg_0001",
      "utterance_id": "u0",
      "story_index": 0,
      "speaker": "host",
      "text": "Welcome back to Early Bird...",
      "url": "/podcasts/podcast_test_.../segments/seg_0001",
      "duration_ms": 4200,
      "source": "pregen"
    },
    // ... more segments
  ]
}
```

## Creating a Full End-to-End Integration Test

To test both Phase 1 and Phase 2 together:

```python
@pytest.mark.integration
def test_full_pipeline_phase1_and_2(tmp_podcast_dir: Path, state):
    """Full pipeline: Phase 1 + Phase 2 with real APIs"""
    
    # Phase 1: Generate research and scripts
    pipeline = PodcastPipeline(...)
    pipeline.generate_research_and_script_assets(tmp_podcast_dir, num_articles=2)
    
    # Phase 2: Generate audio and manifest
    audio_generator = PodcastAudioGenerator(...)
    manifest = pipeline.generate_audio_segments_and_manifest(tmp_podcast_dir, audio_generator)
    
    # Verify everything
    assert (tmp_podcast_dir / "manifest.json").exists()
    assert len(manifest["segments"]) > 0
    # ... more assertions
```

## Troubleshooting

### Integration tests are skipped
- Make sure you use `-m integration` flag
- Check that tests are marked with `@pytest.mark.integration`

### Outputs not persisting
- Verify `--keep-test-output` flag is used
- Check that test passed (only passing tests persist outputs)
- Check that test is marked with `@pytest.mark.integration`
- Look for error messages in test output

### API key errors
- Ensure environment variables are set before running pytest
- For Phase 2, only `ELEVENLABS_API_KEY` is required (Phase 1 outputs are fixtures)

### MP3 validation fails
- pydub requires ffmpeg to be installed
- This is optional - the test will continue even if pydub validation fails
- MP3 files are still generated and saved

## Best Practices

1. **Use integration tests sparingly**: They make real API calls and cost money
2. **Persist outputs for debugging**: Use `--keep-test-output` flag when debugging
3. **Clean up test_output directory**: Periodically remove old test outputs
4. **Check API quotas**: ElevenLabs and OpenAI have rate limits
5. **Use unit tests for development**: Faster feedback during development
