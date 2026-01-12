# Test Analysis: Phase 1 & Phase 2 Integration Tests

## Executive Summary

This document analyzes the Phase 1 and Phase 2 test suites, explains how integration tests work, and provides guidance on persisting test outputs.

## Phase 1 Test Analysis

### Test File: `test_pipeline_phase1_assets.py`

**Purpose**: Test research and script generation (no audio)

**Key Components**:
- **Unit Test**: `test_generate_research_and_script_assets_writes_files`
  - Mocks Perplexity scraper, researcher, and OpenAI script writer
  - Verifies file structure: `podcast.json`, `research/story_*.md`, `script/story_*.json`
  - Validates state updates

- **Integration Test**: `test_generate_research_and_script_assets_integration_full_pipeline`
  - Uses real Perplexity API for headlines and research
  - Uses real OpenAI API for script generation
  - Generates actual research documents and scripts
  - Marked with `@pytest.mark.integration`

**Outputs Generated**:
```
podcast_dir/
├── podcast.json              # Metadata with stories
├── research/
│   └── story_0.md            # Research document
└── script/
    └── story_0.json          # Script with utterances
```

## Phase 2 Test Analysis

### Test File: `test_phase2_manifest_playback.py`

**Purpose**: Test audio generation and manifest creation

**Key Components**:

1. **Unit Tests** (multiple):
   - `test_audio_generator_*` - Test audio generation with mocked ElevenLabs
   - `test_storage_*` - Test storage operations
   - `test_pipeline_generate_audio_segments_and_manifest_*` - Test pipeline with dummy audio generator
   - `test_get_manifest_*`, `test_get_segment_*` - Test API routes

2. **Integration Test**: `test_phase2_manifest_playback_integration_full`
   - Uses `_setup_phase2_test_fixtures()` to create pre-generated Phase 1 outputs
   - Uses real ElevenLabs API for audio generation
   - Generates actual MP3 files
   - Creates manifest structure
   - Validates all outputs

**Outputs Generated**:
```
podcast_dir/
├── podcast.json              # From Phase 1 fixtures
├── research/
│   ├── story_0.md
│   └── story_1.md
├── script/
│   ├── story_0.json
│   └── story_1.json
├── audio/
│   └── pregen/
│       ├── seg_0001.mp3      # Generated audio segments
│       ├── seg_0002.mp3
│       └── ...
└── manifest.json             # Created during test (not by pipeline method)
```

**Note**: The `generate_audio_segments_and_manifest()` method returns the manifest but doesn't save it. The test manually saves it for validation.

## Integration Test Workflow

### Phase 1 Integration Test Flow

```
1. Initialize PodcastPipeline with real API keys
2. Call generate_research_and_script_assets()
   ├─ Fetch headlines from Perplexity
   ├─ Research stories via Perplexity
   ├─ Generate scripts via OpenAI
   └─ Write files to podcast_dir
3. Verify files exist and contain expected data
4. Verify state updates
```

### Phase 2 Integration Test Flow

```
1. Setup Phase 1 fixtures (_setup_phase2_test_fixtures)
   └─ Create pre-generated scripts and research
2. Initialize PodcastPipeline and PodcastAudioGenerator
3. Call generate_audio_segments_and_manifest()
   ├─ Read script files
   ├─ For each utterance:
   │   ├─ Call ElevenLabs API
   │   ├─ Save MP3 file
   │   └─ Record metadata
   └─ Return manifest dict
4. Save manifest.json (manually in test)
5. Validate all outputs
```

## Output Persistence Mechanism

### Automatic Persistence

The test suite includes automatic output persistence via the `persist_test_output` fixture in `conftest.py`.

**How It Works**:
1. Fixture is `autouse=True` (runs automatically)
2. Checks if test is marked with `@pytest.mark.integration`
3. Checks if `--keep-test-output` pytest flag is set
4. After test passes, copies `tmp_podcast_dir` to:
   ```
   backend/tests/test_output/<test_name>_<timestamp>/
   ```

**Usage**:
```bash
pytest -m integration --keep-test-output backend/tests/test_phase2_manifest_playback.py::test_phase2_manifest_playback_integration_full
```

**What Gets Persisted**:
- All files in `tmp_podcast_dir` are copied
- Includes: podcast.json, research/, script/, audio/, manifest.json
- Preserves directory structure

### Manual Persistence Options

1. **Using PodcastStorage**:
   ```python
   from backend.storage.podcast_storage import PodcastStorage
   
   storage = PodcastStorage(backend_root)
   storage.save_manifest(podcast_dir, manifest)
   ```

2. **Direct file copy**:
   ```python
   import shutil
   shutil.copytree(tmp_podcast_dir, output_dir)
   ```

3. **Inspect during test**:
   - Add breakpoints or print statements
   - Files exist in `tmp_podcast_dir` during test execution

## Running Integration Tests

### Prerequisites

**Phase 1**:
- `PERPLEXITY_API_KEY`
- `OPENAI_API_KEY`

**Phase 2**:
- `ELEVENLABS_API_KEY`
- (Phase 1 outputs are fixtures, no API keys needed for that)

### Commands

```bash
# Run all integration tests
pytest -m integration

# Run Phase 1 only
pytest -m integration backend/tests/test_pipeline_phase1_assets.py::test_generate_research_and_script_assets_integration_full_pipeline

# Run Phase 2 only
pytest -m integration backend/tests/test_phase2_manifest_playback.py::test_phase2_manifest_playback_integration_full

# With output persistence
pytest -m integration --keep-test-output -v
```

## Key Differences: Phase 1 vs Phase 2

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| **Input** | None (fetches from APIs) | Pre-generated scripts |
| **APIs Used** | Perplexity, OpenAI | ElevenLabs |
| **Outputs** | JSON, Markdown | MP3 files, Manifest |
| **Test Fixtures** | None (real API calls) | Pre-generated Phase 1 outputs |
| **Duration** | ~30-60s | ~2-5 minutes (depends on segments) |
| **Cost** | Perplexity + OpenAI | ElevenLabs (per character) |

## Recommendations

### For Phase 2 Integration Tests

1. **Save manifest.json automatically**: The pipeline method should save the manifest to the podcast directory, not just return it.

2. **Full end-to-end test**: Create a test that runs Phase 1 → Phase 2 sequentially:
   ```python
   @pytest.mark.integration
   def test_full_pipeline_phase1_and_2(tmp_podcast_dir, state):
       # Phase 1
       pipeline.generate_research_and_script_assets(tmp_podcast_dir, num_articles=2)
       
       # Phase 2
       manifest = pipeline.generate_audio_segments_and_manifest(tmp_podcast_dir, audio_generator)
       
       # Save manifest
       storage.save_manifest(tmp_podcast_dir, manifest)
   ```

3. **Better output organization**: Consider organizing persisted outputs by phase or date.

4. **Validation improvements**: Add more validation for:
   - MP3 file integrity (using pydub)
   - Manifest schema validation
   - Segment ordering and continuity

## Current Limitations

1. **Manifest not auto-saved**: `generate_audio_segments_and_manifest()` returns manifest but doesn't save it
2. **No end-to-end test**: Phase 1 and Phase 2 are tested separately
3. **Limited MP3 validation**: Only checks file existence and size, not audio quality
4. **No cleanup**: Persisted outputs accumulate in `test_output/` directory

## Next Steps

1. ✅ Document test structure (this document)
2. ⚠️ Improve Phase 2 test to save manifest automatically
3. ⚠️ Create full end-to-end integration test
4. ⚠️ Add cleanup mechanism for old test outputs
5. ⚠️ Add manifest schema validation
