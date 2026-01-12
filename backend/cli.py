#!/usr/bin/env python3
"""
Command-line interface for EarlyBird podcast generation.
"""
import argparse
import sys
import json
from pathlib import Path

from backend.config import Config
from backend.core.podcast_service import PodcastService
from backend.utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging(Config.LOG_LEVEL)
logger = get_logger(__name__)


def generate_podcast():
    """Generate a new podcast (full pipeline: scripts + audio)"""
    logger.info("Starting full podcast generation from CLI...")
    
    service = PodcastService()
    podcast_dir = service.create_podcast_dir()
    
    result = service.generate_podcast(
        podcast_dir=podcast_dir,
        num_articles=3,
        categories=["Technology", None, "Squash (Sport)"] 
    )
    
    print(f"\n✓ Podcast generation complete!")
    print(f"  Podcast ID: {result['podcast_id']}")
    print(f"  Output directory: {podcast_dir}")
    print(f"  Stories: {len(result.get('stories', []))}")
    
    if Config.GENERATE_AUDIO:
        print(f"  Audio generation: ENABLED (segments generated)")
    else:
        print(f"  Audio generation: DISABLED (scripts only - set GENERATE_AUDIO=true in .env to enable)")
    
    print(f"\n  Check outputs in: {podcast_dir}")


def generate_script(podcast_id: str = None, num_articles: int = None, categories: list = None):
    """
    Generate script assets (Phase 1) for a podcast.
    
    Args:
        podcast_id: Optional podcast ID. If provided, regenerates scripts for existing podcast.
                   If None, creates a new podcast.
        num_articles: Number of articles (defaults to 3 for new, or reads from existing)
        categories: Categories list (defaults if not provided)
    """
    import json
    
    service = PodcastService()
    
    if podcast_id:
        logger.info(f"Regenerating scripts for existing podcast: {podcast_id}")
        podcast_dir = service.get_podcast_dir_by_id(podcast_id)
        
        # Try to read existing podcast.json to get story count
        podcast_json_path = podcast_dir / "podcast.json"
        if podcast_json_path.exists() and num_articles is None:
            try:
                existing_data = json.loads(podcast_json_path.read_text(encoding="utf-8"))
                num_articles = len(existing_data.get("stories", []))
                logger.info(f"Found {num_articles} existing stories, will regenerate same count")
            except Exception as e:
                logger.warning(f"Could not read existing podcast.json: {e}")
                num_articles = num_articles or 3
        else:
            num_articles = num_articles or 3
    else:
        logger.info("Creating new podcast and generating scripts...")
        podcast_dir = service.create_podcast_dir()
        num_articles = num_articles or 3
    
    result = service.generate_script_assets(
        podcast_dir=podcast_dir,
        num_articles=num_articles,
        categories=categories or ["Technology", None, "Squash (Sport)"],
    )
    
    print(f"\n✓ Script generation complete!")
    print(f"  Podcast ID: {result['podcast_id']}")
    print(f"  Output directory: {podcast_dir}")
    print(f"  Stories: {len(result.get('stories', []))}")
    print(f"\n  To generate audio, run:")
    print(f"    python -m backend.cli generate-audio {result['podcast_id']}")


def generate_audio(podcast_id: str):
    """
    Generate audio assets (Phase 2) for an existing podcast.
    
    Args:
        podcast_id: Podcast ID to generate audio for
    """
    if not podcast_id:
        print("Error: podcast_id is required")
        sys.exit(1)
    
    service = PodcastService()
    
    try:
        podcast_dir = service.get_podcast_dir_by_id(podcast_id)
    except FileNotFoundError as e:
        logger.error(str(e))
        print(f"Error: {e}")
        print(f"\n  Available podcasts in: {Config.PODCAST_DIR}")
        sys.exit(1)
    
    manifest = service.generate_audio_assets(podcast_dir)
    
    print(f"\n✓ Audio generation complete!")
    print(f"  Podcast ID: {podcast_id}")
    print(f"  Output directory: {podcast_dir}")
    print(f"  Segments generated: {len(manifest.get('segments', []))}")
    print(f"\n  Check outputs in: {podcast_dir / 'audio' / 'pregen'}")


def generate_from_transcript(transcript_path: str):
    """
    Generate audio from an existing transcript file.
    
    Args:
        transcript_path: Path to the transcript file
    """
    transcript_path = Path(transcript_path)
    
    if not transcript_path.exists():
        logger.error(f"Transcript file not found: {transcript_path}")
        print(f"Error: Transcript file not found: {transcript_path}")
        sys.exit(1)
    
    logger.info(f"Generating audio from transcript: {transcript_path}")
    
    service = PodcastService()
    result = service.generate_from_transcript(str(transcript_path))
    
    print(f"\n✓ Podcast generation from transcript complete!")
    print(f"  Output directory: {result['podcast_dir']}")
    print(f"  Original transcript: {result['transcript_path']}")
    print(f"  Generated audio: {result['audio_path']}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="EarlyBird - AI-powered podcast generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a new podcast (full pipeline: scripts + audio)
  python -m backend.cli generate
  
  # Generate scripts only (Phase 1)
  python -m backend.cli generate-script
  
  # Generate scripts for existing podcast
  python -m backend.cli generate-script podcast_20260112_100034_2d5ffbab
  
  # Generate audio for existing podcast (Phase 2)
  python -m backend.cli generate-audio podcast_20260112_100034_2d5ffbab
  
  # Generate audio from existing transcript
  python -m backend.cli from-transcript path/to/transcript.txt
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command (full pipeline)
    subparsers.add_parser(
        'generate',
        help='Generate a new podcast (scripts + audio)'
    )
    
    # Generate script command
    script_parser = subparsers.add_parser(
        'generate-script',
        help='Generate script assets (Phase 1) for a podcast'
    )
    script_parser.add_argument(
        'podcast_id',
        nargs='?',
        type=str,
        default=None,
        help='Optional podcast ID. If provided, regenerates scripts for existing podcast. If omitted, creates new podcast.'
    )
    script_parser.add_argument(
        '--num-articles',
        type=int,
        default=3,
        help='Number of articles (default: 3)'
    )
    script_parser.add_argument(
        '--categories',
        type=str,
        default=None,
        help='Categories as JSON list (use null for random). Example: --categories \'["Technology", null, "Science"]\''
    )
    
    # Generate audio command
    audio_parser = subparsers.add_parser(
        'generate-audio',
        help='Generate audio assets (Phase 2) for an existing podcast'
    )
    audio_parser.add_argument(
        'podcast_id',
        type=str,
        help='Podcast ID to generate audio for'
    )
    
    # From-transcript command
    from_transcript_parser = subparsers.add_parser(
        'from-transcript',
        help='Generate audio from an existing transcript'
    )
    from_transcript_parser.add_argument(
        'transcript_path',
        type=str,
        help='Path to the transcript file'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'generate':
            generate_podcast()
        elif args.command == 'generate-script':
            # Parse categories from JSON string
            categories = None
            if args.categories:
                try:
                    parsed = json.loads(args.categories)
                    if not isinstance(parsed, list):
                        print("Error: --categories must be a JSON list")
                        sys.exit(1)
                    # Convert null/None JSON values to Python None
                    categories = [None if c is None or (isinstance(c, str) and c.lower() == 'null') else str(c) for c in parsed]
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON in --categories: {e}")
                    print("  Example: --categories '[\"Technology\", null, \"Science\"]'")
                    sys.exit(1)
            generate_script(
                podcast_id=args.podcast_id,
                num_articles=args.num_articles,
                categories=categories
            )
        elif args.command == 'generate-audio':
            generate_audio(args.podcast_id)
        elif args.command == 'from-transcript':
            generate_from_transcript(args.transcript_path)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
