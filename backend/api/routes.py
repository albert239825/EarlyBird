"""
HTTP routes for the podcast API.
"""
from flask import request, send_from_directory, jsonify
from backend.core.podcast_service import PodcastService
from backend.core.pipeline import PodcastPipeline
from backend.storage.podcast_storage import PodcastStorage
from backend.config import Config
from backend.utils.logging_config import get_logger
import threading
import whisper
import os
import json
from pathlib import Path
from typing import Any, List, Optional

logger = get_logger(__name__)


def setup_routes(app, service: PodcastService):
    """
    Set up HTTP routes for the Flask app.
    
    Args:
        app: Flask application instance
        service: PodcastService instance
    """
    
    @app.route("/", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({"message": "Podcast generation service is running"})

    @app.route("/generate", methods=["POST"])
    def generate():
        """Start podcast generation."""
        try:
            payload = request.get_json(silent=True) or {}
            num_articles = int(payload.get("num_articles", 2))
            categories = payload.get("categories", None)

            # Validate categories input: must be list of len == num_articles; elements are str or None
            parsed_categories: Optional[List[Optional[str]]] = None
            if categories is not None:
                if not isinstance(categories, list):
                    return jsonify({"error": "`categories` must be a list or null"}), 400
                if len(categories) != num_articles:
                    return jsonify({"error": "`categories` length must equal `num_articles`"}), 400
                parsed_categories = []
                for idx, c in enumerate(categories):
                    if c is None:
                        parsed_categories.append(None)
                    elif isinstance(c, str):
                        parsed_categories.append(c)
                    else:
                        return jsonify({"error": f"`categories[{idx}]` must be a string or null"}), 400

            podcast_dir = service.create_podcast_dir()
            podcast_id = podcast_dir.name

            thread = threading.Thread(
                target=service.generate_podcast,
                args=(podcast_dir, num_articles, parsed_categories),
            )
            thread.daemon = True
            thread.start()
            return jsonify({"podcast_id": podcast_id}), 200
        except Exception as e:
            logger.exception(f"Error in /generate route: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/generate_next", methods=["POST"])
    def generate_next():
        """Generate next part of podcast script."""
        try:
            next_id = request.json.get("next_id")
            logger.info(f"Generating next part for article: {next_id}")

            thread = threading.Thread(target=service.generate_next_part, args=(next_id,))
            thread.daemon = True
            thread.start()

            return jsonify({"message": "Podcast generation started"}), 200

        except Exception as e:
            logger.exception(f"Error in /generate_next route: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/generate_answer", methods=["POST"])
    def generate_answer():
        """Answer user question about an article."""
        try:
            index = request.json.get("index")
            question = request.json.get("question")

            response = service.answer_question(index, question)

            return {"message": response}, 200

        except Exception as e:
            logger.exception(f"Error in /generate_answer route: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/download/<filename>/<num>", methods=["GET"])
    def download(filename, num="1"):
        """Serve generated MP3 file."""
        try:
            podcast_dir = Config.PODCAST_DIR
            if not podcast_dir.exists():
                logger.error(f"Podcast directory not found: {podcast_dir}")
                return jsonify({"error": "Podcast directory not found"}), 500
            
            podcast_audio_path = podcast_dir / filename / f"interaction_{num}.mp3"
            logger.info(f"Podcast audio path: {podcast_audio_path}")
            
            if not podcast_audio_path.exists():
                logger.error(f"Audio file not found: {podcast_audio_path}")
                return jsonify({"error": "File not found"}), 404

            return send_from_directory(
                str(podcast_audio_path.parent), 
                podcast_audio_path.name, 
                as_attachment=True
            )
        
        except Exception as e:
            logger.error(f"Error serving file {filename}: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/get/transcripts", methods=["GET"])
    def get_all_transcript_files():
        """Return list of all transcript files and metadata."""
        try:
            metadata_file_path = Config.PODCAST_DIR / "podcast_metadata.json"
            
            if not metadata_file_path.exists():
                logger.error(f"Metadata file not found: {metadata_file_path}")
                return jsonify({"error": "Metadata file not found"}), 404
            
            with open(metadata_file_path, 'r') as f:
                metadata = json.load(f)
                return jsonify({"metadata": metadata}), 200
        except Exception as e:
            logger.error(f"Error retrieving transcripts: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/podcasts/<podcast_id>/manifest", methods=["GET"])
    def get_manifest(podcast_id):
        """Get podcast manifest."""
        try:
            storage = PodcastStorage(Config.BACKEND_ROOT)
            podcast_dir = storage.get_podcast_dir(podcast_id)
            
            if not podcast_dir.exists():
                logger.error(f"Podcast directory not found: {podcast_dir}")
                return jsonify({"error": "Podcast not found"}), 404
            
            manifest = storage.load_manifest(podcast_dir)
            return jsonify(manifest), 200
        except FileNotFoundError as e:
            logger.error(f"Manifest not found: {str(e)}")
            return jsonify({"error": "Manifest not found"}), 404
        except Exception as e:
            logger.exception(f"Error retrieving manifest: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/podcasts/<podcast_id>/segments/<segment_id>", methods=["GET"])
    def get_segment(podcast_id, segment_id):
        """Serve audio segment MP3 file."""
        try:
            storage = PodcastStorage(Config.BACKEND_ROOT)
            podcast_dir = storage.get_podcast_dir(podcast_id)
            
            if not podcast_dir.exists():
                logger.error(f"Podcast directory not found: {podcast_dir}")
                return jsonify({"error": "Podcast not found"}), 404
            
            # Load manifest to find segment
            manifest = storage.load_manifest(podcast_dir)
            segment_info = None
            for seg in manifest.get("segments", []):
                if seg.get("segment_id") == segment_id:
                    segment_info = seg
                    break
            
            if not segment_info:
                logger.error(f"Segment not found: {segment_id}")
                return jsonify({"error": "Segment not found"}), 404
            
            # Determine file path based on source
            if segment_info.get("source") == "pregen":
                segment_path = podcast_dir / "audio" / "pregen" / f"{segment_id}.mp3"
            elif segment_info.get("source") == "dynamic":
                segment_path = podcast_dir / "audio" / "dynamic" / f"{segment_id}.mp3"
            else:
                logger.error(f"Unknown segment source: {segment_info.get('source')}")
                return jsonify({"error": "Invalid segment source"}), 500
            
            if not segment_path.exists():
                logger.error(f"Audio file not found: {segment_path}")
                return jsonify({"error": "Audio file not found"}), 404
            
            return send_from_directory(
                str(segment_path.parent),
                segment_path.name,
                mimetype="audio/mpeg"
            )
        except FileNotFoundError as e:
            logger.error(f"Segment file not found: {str(e)}")
            return jsonify({"error": "Segment not found"}), 404
        except Exception as e:
            logger.exception(f"Error serving segment: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/interrupt", methods=["POST"])
    def handle_interrupt():
        """Transcribe audio and generate expert response."""
        try:
            if 'audio' not in request.files:
                logger.error("No audio file part in the request")
                return jsonify({"error": "No audio file part in the request"}), 400
            
            audio_file = request.files['audio']
            file_path = request.form.get('file_path')
            
            if audio_file.filename == '':
                logger.error("No selected file")
                return jsonify({"error": "No selected file"}), 400
            
            # Save audio temporarily
            temp_audio_path = Config.PODCAST_DIR / "temp_audio.wav"
            audio_file.save(str(temp_audio_path))
            
            # Transcribe with Whisper
            model = whisper.load_model("base")
            result = model.transcribe(str(temp_audio_path))
            transcription = result["text"]
            logger.info(f"Transcription: {transcription}")
            logger.info(f"File path: {file_path}")
            
            # Generate expert response
            pipeline = PodcastPipeline(
                perplexity_api_key=Config.PERPLEXITY_API_KEY,
                openai_api_key=Config.OPENAI_API_KEY,
                mistral_api_key=Config.MISTRAL_API_KEY,
                state=service.state
            )
            interrupt_path = pipeline.user_ask_expert(
                question=transcription, 
                filepath=file_path,
                backend_root=Config.BACKEND_ROOT
            )
            logger.info(f"Expert response: {interrupt_path}")
            
            # Clean up
            temp_audio_path.unlink()
            
            return jsonify({"response": interrupt_path}), 200
        except Exception as e:
            logger.error(f"Error processing audio file: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500
