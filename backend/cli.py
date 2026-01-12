#!/usr/bin/env python3
"""
Command-line interface for EarlyBird podcast generation.
"""
import argparse
import sys
from pathlib import Path

from backend.config import Config
from backend.core.podcast_service import PodcastService
from backend.utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging(Config.LOG_LEVEL)
logger = get_logger(__name__)


def generate_podcast():
    """Generate a new podcast"""
    logger.info("Starting podcast generation from CLI...")
    
    service = PodcastService()
    podcast_dir = service.create_podcast_dir()
    
    result = service.generate_podcast(
        podcast_dir=podcast_dir,
        num_articles=2,
        categories=["Technology", None, "Squash (Sport)"] 
    )
    
    print(f"\n✓ Podcast generation complete!")
    print(f"  Podcast ID: {result['podcast_id']}")
    print(f"  Output directory: {podcast_dir}")
    print(f"  Stories: {len(result.get('stories', []))}")
    print(f"\n  Check outputs in: {podcast_dir}")


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
  # Generate a new podcast
  python -m backend.cli generate
  
  # Generate audio from existing transcript
  python -m backend.cli from-transcript path/to/transcript.txt
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    subparsers.add_parser(
        'generate',
        help='Generate a new podcast'
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
