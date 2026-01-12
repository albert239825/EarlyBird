"""
HTTP routes for the podcast API.
"""
from flask import request, send_from_directory, jsonify
from backend.core.podcast_service import PodcastService
from backend.storage.podcast_storage import PodcastStorage
from backend.config import Config
from backend.utils.logging_config import get_logger
import threading
import os
import json
from pathlib import Path
from typing import Any, List, Optional
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except Exception:
    PYDUB_AVAILABLE = False

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

            # Write request metadata early so progress polling knows expected story count
            # even before podcast.json exists.
            try:
                (podcast_dir / "request.json").write_text(
                    json.dumps(
                        {
                            "podcast_id": podcast_id,
                            "num_articles": num_articles,
                            "categories": parsed_categories,
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
            except Exception as e:
                logger.warning(f"Could not write request.json for {podcast_id}: {e}")

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

    # @app.route("/generate_next", methods=["POST"])
    # def generate_next():
    #     """Generate next part of podcast script."""
    #     try:
    #         next_id = request.json.get("next_id")
    #         logger.info(f"Generating next part for article: {next_id}")

    #         thread = threading.Thread(target=service.generate_next_part, args=(next_id,))
    #         thread.daemon = True
    #         thread.start()

    #         return jsonify({"message": "Podcast generation started"}), 200

    #     except Exception as e:
    #         logger.exception(f"Error in /generate_next route: {str(e)}")
    #         return jsonify({"error": "Internal server error"}), 500

    # @app.route("/generate_answer", methods=["POST"])
    # def generate_answer():
    #     """Answer user question about an article."""
    #     try:
    #         index = request.json.get("index")
    #         question = request.json.get("question")

    #         response = service.answer_question(index, question)

    #         return {"message": response}, 200

    #     except Exception as e:
    #         logger.exception(f"Error in /generate_answer route: {str(e)}")
    #         return jsonify({"error": "Internal server error"}), 500

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

    @app.route("/podcasts/<podcast_id>/status", methods=["GET"])
    def get_status(podcast_id):
        """Get podcast generation status and progress."""
        try:
            storage = PodcastStorage(Config.BACKEND_ROOT)
            podcast_dir = storage.get_podcast_dir(podcast_id)

            if not podcast_dir.exists():
                return jsonify({"error": "Podcast not found"}), 404

            request_json_path = podcast_dir / "request.json"
            podcast_json_path = podcast_dir / "podcast.json"
            manifest_path = podcast_dir / "manifest.json"
            research_dir = podcast_dir / "research"
            script_dir = podcast_dir / "script"
            audio_pregen_dir = podcast_dir / "audio" / "pregen"
            audio_dynamic_dir = podcast_dir / "audio" / "dynamic"

            total_stories = 0
            if request_json_path.exists():
                try:
                    req = json.loads(request_json_path.read_text(encoding="utf-8"))
                    total_stories = int(req.get("num_articles") or 0)
                except Exception as e:
                    logger.warning(f"Could not read request.json for {podcast_id}: {e}")

            artifacts = {"titles": [], "research": {}, "scripts": {}}

            # Titles (podcast.json)
            if podcast_json_path.exists():
                try:
                    podcast_data = json.loads(podcast_json_path.read_text(encoding="utf-8"))
                    stories = podcast_data.get("stories", []) or []
                    total_stories = total_stories or len(stories)
                    artifacts["titles"] = [
                        {"story_index": s.get("story_index"), "title": s.get("title")}
                        for s in stories
                        if isinstance(s, dict)
                    ]
                except Exception as e:
                    logger.warning(f"Could not read podcast.json for {podcast_id}: {e}")

            # Research previews
            research_count = 0
            if research_dir.exists():
                for research_file in sorted(research_dir.glob("story_*.md")):
                    try:
                        story_index = int(research_file.stem.split("_")[1])
                        content = research_file.read_text(encoding="utf-8")
                        core_summary = ""
                        if "## Core_summary" in content:
                            core_summary = (
                                content.split("## Core_summary", 1)[1].split("##", 1)[0].strip()
                            )
                        artifacts["research"][str(story_index)] = core_summary[:800]
                        research_count = max(research_count, story_index + 1)
                    except Exception as e:
                        logger.warning(f"Could not read research file {research_file}: {e}")

            # Script previews
            script_count = 0
            if script_dir.exists():
                for script_file in sorted(script_dir.glob("story_*.json")):
                    try:
                        story_index = int(script_file.stem.split("_")[1])
                        script_data = json.loads(script_file.read_text(encoding="utf-8"))
                        utterances = script_data.get("utterances", []) or []
                        artifacts["scripts"][str(story_index)] = [
                            {"speaker": u.get("speaker"), "text": u.get("text")}
                            for u in utterances[:3]
                            if isinstance(u, dict)
                        ]
                        script_count = max(script_count, story_index + 1)
                    except Exception as e:
                        logger.warning(f"Could not read script file {script_file}: {e}")

            # Audio progress (very approximate)
            audio_files = 0
            if audio_pregen_dir.exists():
                audio_files += len(list(audio_pregen_dir.glob("*.mp3")))
            if audio_dynamic_dir.exists():
                audio_files += len(list(audio_dynamic_dir.glob("*.mp3")))

            intro_exists = script_dir.exists() and (script_dir / "intro.json").exists()
            outro_exists = script_dir.exists() and (script_dir / "outro.json").exists()

            status = "not_started"
            progress = 0

            if manifest_path.exists():
                status = "complete"
                progress = 100
            elif audio_files > 0 and intro_exists and outro_exists and total_stories and script_count >= total_stories:
                status = "generating_audio"
                # crude heuristic: start at 75% once audio begins; creep toward 95%
                progress = min(95, 75 + int(min(1.0, audio_files / max(1, total_stories * 8)) * 20))
            elif script_count > 0 or intro_exists or outro_exists:
                status = "scripting"
                if total_stories:
                    progress = 33 + int(min(1.0, script_count / max(1, total_stories)) * 42)  # 33..75
                else:
                    progress = 33
            elif research_count > 0:
                status = "researching"
                if total_stories:
                    progress = int(min(1.0, research_count / max(1, total_stories)) * 33)  # 0..33
                else:
                    progress = 10
            elif request_json_path.exists():
                status = "researching"
                progress = 1

            current_story_index = -1
            if status in ("researching", "scripting", "generating_audio"):
                current_story_index = max(research_count, script_count) - 1

            stories_complete = research_count

            return jsonify(
                {
                    "status": status,
                    "progress": progress,
                    "current_story_index": current_story_index,
                    "stories_complete": stories_complete,
                    "total_stories": total_stories,
                    "artifacts": artifacts,
                }
            ), 200
        except Exception as e:
            logger.exception(f"Error retrieving status: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/podcasts/<podcast_id>/podcast.json", methods=["GET"])
    def get_podcast_json(podcast_id):
        """Get podcast.json with story titles."""
        try:
            storage = PodcastStorage(Config.BACKEND_ROOT)
            podcast_dir = storage.get_podcast_dir(podcast_id)
            if not podcast_dir.exists():
                return jsonify({"error": "Podcast not found"}), 404

            podcast_json_path = podcast_dir / "podcast.json"
            if not podcast_json_path.exists():
                return jsonify({"error": "Podcast data not found"}), 404

            return jsonify(json.loads(podcast_json_path.read_text(encoding="utf-8"))), 200
        except Exception as e:
            logger.exception(f"Error retrieving podcast.json: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/podcasts/<podcast_id>/research/<int:story_index>", methods=["GET"])
    def get_research(podcast_id, story_index):
        """Get research markdown for a story."""
        try:
            storage = PodcastStorage(Config.BACKEND_ROOT)
            podcast_dir = storage.get_podcast_dir(podcast_id)
            if not podcast_dir.exists():
                return jsonify({"error": "Podcast not found"}), 404

            research_path = podcast_dir / "research" / f"story_{story_index}.md"
            if not research_path.exists():
                return jsonify({"error": "Research not found"}), 404

            return jsonify({"story_index": story_index, "content": research_path.read_text(encoding="utf-8")}), 200
        except Exception as e:
            logger.exception(f"Error retrieving research: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/podcasts/<podcast_id>/script/<int:story_index>", methods=["GET"])
    def get_script(podcast_id, story_index):
        """Get script JSON for a story."""
        try:
            storage = PodcastStorage(Config.BACKEND_ROOT)
            podcast_dir = storage.get_podcast_dir(podcast_id)
            if not podcast_dir.exists():
                return jsonify({"error": "Podcast not found"}), 404

            script_path = podcast_dir / "script" / f"story_{story_index}.json"
            if not script_path.exists():
                return jsonify({"error": "Script not found"}), 404

            return jsonify(json.loads(script_path.read_text(encoding="utf-8"))), 200
        except Exception as e:
            logger.exception(f"Error retrieving script: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/podcasts/<podcast_id>/download", methods=["GET"])
    def download_full_podcast(podcast_id):
        """Concatenate all segments into a single MP3 for download (best-effort)."""
        if not PYDUB_AVAILABLE:
            return jsonify({"error": "pydub not available for audio concatenation"}), 500

        try:
            storage = PodcastStorage(Config.BACKEND_ROOT)
            podcast_dir = storage.get_podcast_dir(podcast_id)
            if not podcast_dir.exists():
                return jsonify({"error": "Podcast not found"}), 404

            manifest = storage.load_manifest(podcast_dir)
            segments = manifest.get("segments", []) or []
            if not segments:
                return jsonify({"error": "No segments found"}), 404

            combined = AudioSegment.empty()
            for seg in segments:
                segment_id = seg.get("segment_id")
                source = seg.get("source", "pregen")
                if not segment_id:
                    continue
                if source == "dynamic":
                    segment_path = podcast_dir / "audio" / "dynamic" / f"{segment_id}.mp3"
                else:
                    segment_path = podcast_dir / "audio" / "pregen" / f"{segment_id}.mp3"
                if segment_path.exists():
                    combined += AudioSegment.from_mp3(str(segment_path))

            if len(combined) == 0:
                return jsonify({"error": "No valid segments found"}), 404

            out_path = podcast_dir / "full_podcast.mp3"
            combined.export(str(out_path), format="mp3")
            return send_from_directory(
                str(out_path.parent),
                out_path.name,
                as_attachment=True,
                download_name=f"podcast_{podcast_id}.mp3",
            )
        except FileNotFoundError:
            return jsonify({"error": "Podcast not found"}), 404
        except Exception as e:
            logger.exception(f"Error creating full podcast: {str(e)}")
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

    # @app.route("/interrupt", methods=["POST"])
    # def handle_interrupt():
    #     """Transcribe audio and generate expert response."""
    #     try:
    #         if 'audio' not in request.files:
    #             logger.error("No audio file part in the request")
    #             return jsonify({"error": "No audio file part in the request"}), 400
            
    #         audio_file = request.files['audio']
    #         file_path = request.form.get('file_path')
            
    #         if audio_file.filename == '':
    #             logger.error("No selected file")
    #             return jsonify({"error": "No selected file"}), 400
            
    #         # Save audio temporarily
    #         temp_audio_path = Config.PODCAST_DIR / "temp_audio.wav"
    #         audio_file.save(str(temp_audio_path))
            
    #         # Transcribe with Whisper
    #         model = whisper.load_model("base")
    #         result = model.transcribe(str(temp_audio_path))
    #         transcription = result["text"]
    #         logger.info(f"Transcription: {transcription}")
    #         logger.info(f"File path: {file_path}")
            
    #         # Generate expert response
    #         pipeline = PodcastPipeline(
    #             perplexity_api_key=Config.PERPLEXITY_API_KEY,
    #             openai_api_key=Config.OPENAI_API_KEY,
    #             mistral_api_key=Config.MISTRAL_API_KEY,
    #             state=service.state
    #         )
    #         interrupt_path = pipeline.user_ask_expert(
    #             question=transcription, 
    #             filepath=file_path,
    #             backend_root=Config.BACKEND_ROOT
    #         )
    #         logger.info(f"Expert response: {interrupt_path}")
            
    #         # Clean up
    #         temp_audio_path.unlink()
            
    #         return jsonify({"response": interrupt_path}), 200
    #     except Exception as e:
    #         logger.error(f"Error processing audio file: {str(e)}")
    #         return jsonify({"error": "Internal server error"}), 500
