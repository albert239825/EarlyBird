# Quick Reference: Integration Tests & Output Persistence

## Quick Start

### Run Phase 2 Integration Test with Output Persistence

```bash
# Set environment variables
export ELEVENLABS_API_KEY="your_key_here"

# Run test with --keep-test-output flag
pytest -m integration --keep-test-output backend/tests/test_phase2_manifest_playback.py::test_phase2_manifest_playback_integration_full -v
```

**Output Location**: `backend/tests/test_output/test_phase2_manifest_playback_integration_full_<timestamp>/`

### Run Phase 1 Integration Test

```bash
export PERPLEXITY_API_KEY="your_key"
export OPENAI_API_KEY="your_key"

pytest -m integration --keep-test-output backend/tests/test_pipeline_phase1_assets.py::test_generate_research_and_script_assets_integration_full_pipeline -v
```

## Test Structure

### Phase 1
- **Input**: None (fetches from APIs)
- **Output**: `podcast.json`, `research/*.md`, `script/*.json`
- **APIs**: Perplexity, OpenAI

### Phase 2
- **Input**: Pre-generated Phase 1 outputs (fixtures)
- **Output**: `audio/pregen/*.mp3`, `manifest.json`
- **APIs**: ElevenLabs

## Output Persistence

**Automatic** (recommended):
- Use `--keep-test-output` flag
- Test must be marked `@pytest.mark.integration`
- Test must pass
- Outputs saved to `backend/tests/test_output/`

**Manual**:
```python
import shutil
shutil.copytree(tmp_podcast_dir, "my_output_dir")
```

## Key Files

- `test_pipeline_phase1_assets.py` - Phase 1 tests
- `test_phase2_manifest_playback.py` - Phase 2 tests
- `conftest.py` - Test fixtures and persistence logic

## Common Issues

**Tests skipped**: Use `-m integration` flag

**No outputs persisted**: 
- Check `--keep-test-output` flag is used
- Verify test passed
- Check test is marked `@pytest.mark.integration`

**API errors**: Ensure API keys are set in environment
