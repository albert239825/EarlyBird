import sys 
import os
import threading
# Add project root to Python path for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import logging
from backend.podcast.podcast import PodcastRunner
from backend.podcast.agents.pipeline import NewsPodcastPipeline
import json
from flask_socketio import SocketIO, emit

from backend.podcast.AppData import data as app_data
import whisper

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# App configuration
class Config:
    PODCAST_DIR = os.getenv('PODCAST_DIR', 'finished_podcasts/')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 8000))

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*")

def emit_data(socketio, new_data):
    socketio.emit('my_response', {'data': new_data})

app_data["emit_function"] = emit_data
app_data["socketio"] = socketio

def emit_new_data():
    article_data = app_data["Articles"]
    new_data = [{**article} for article in article_data]
    for article in new_data:
        article["article_data"] = article["article_data"].to_dict()
    emit_data(app_data["socketio"], {
        "message": "new_article_info",
        "data": new_data
    })

app_data["emit_articles"] = emit_new_data

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    app_data["emit_function"](
        app_data["socketio"],
        {"message": "Connected to server"}
    )

@app.route("/", methods=["GET"])
def build():
    """Health check endpoint."""
    return jsonify({"message": "Podcast generation service is running"})

runner = PodcastRunner()

@app.route("/generate", methods=["POST"])
def generate():
    """Handles user request, generates a podcast."""
    try:
        thread = threading.Thread(target=runner.run)
        thread.daemon = True
        thread.start()
        return jsonify({"message": "Podcast generation started"}), 200
    except Exception as e:
        logger.exception(f"Error in /generate route: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/generate_next", methods=["POST"])
def generate_next():
    """Handles user request, generates a podcast, and returns the file URL."""
    try:
        next_id = request.json.get("next_id")
        print(f"next_id: {next_id}")

        thread = threading.Thread(target=runner.run_next, args=(next_id,))
        thread.daemon = True  # Allow the thread to exit when the main program exits
        thread.start()

        return jsonify({"message": "Podcast generation started"}), 200

    except Exception as e:
        logger.exception(f"Error in /generate route: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/generate_answer", methods=["POST"])  # Ensure it's POST method
def generate_answer():
    """Handles user request, generates a podcast, and returns the file URL."""
    try:
        index = request.json.get("index")
        question = request.json.get("question")

        response = runner.answer_question(index, question)

        return {"message": response}, 200

    except Exception as e:
        logger.exception(f"Error in /generate route: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/download/<filename>/<num>", methods=["GET"])
@app.route("/download/<filename>/<num>", methods=["GET"])
def download(filename, num = 1):
    """Serves the generated MP3 file from the podcast directory."""
    try:
        # Using configured podcast directory
        podcast_dir = app.config['PODCAST_DIR']
        if not os.path.exists(podcast_dir):
            logger.error(f"Podcast directory not found: {podcast_dir}")
            return jsonify({"error": "Podcast directory not found"}), 500
        
        
        # Build the full path to the MP3 file
        podcast_audio_path = os.path.join(podcast_dir, filename, f"interaction_{num}.mp3")
        logger.info(f"Podcast audio path: {podcast_audio_path}")
        if not os.path.exists(podcast_audio_path):
            logger.error(f"Audio file not found: {podcast_audio_path}")
            return jsonify({"error": "File not found"}), 404

        # Serve the file
        return send_from_directory(os.path.dirname(podcast_audio_path), os.path.basename(podcast_audio_path), as_attachment=True)
    
    except Exception as e:
        logger.error(f"Error serving file {filename}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/get/transcripts", methods=["GET"])
def get_all_transcript_files():
    """Returns a list of all transcript files and their metadata."""
    try:
        podcast_dir = app.config['PODCAST_DIR']
        metadata_file_path = os.path.join(podcast_dir, "podcast_metadata.json")
        
        if not os.path.exists(metadata_file_path):
            logger.error(f"Metadata file not found: {metadata_file_path}")
            return jsonify({"error": "Metadata file not found"}), 404
        
        with open(metadata_file_path, 'r') as f:
            metadata = json.load(f)
            return jsonify({"metadata": metadata}), 200
    except Exception as e:
        logger.error(f"Error retrieving transcripts: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/interrupt", methods=["POST"])
def get_response():
    """Transcribes the audio blob and returns an expert response."""
    try:
        if 'audio' not in request.files:
            logger.error("No audio file part in the request")
            return jsonify({"error": "No audio file part in the request"}), 400
        
        audio_file = request.files['audio']
        file_path = request.form.get('file_path')
        if audio_file.filename == '':
            logger.error("No selected file")
            return jsonify({"error": "No selected file"}), 400
        
        # Save the audio file temporarily
        temp_audio_path = os.path.join(app.config['PODCAST_DIR'], "temp_audio.wav")
        audio_file.save(temp_audio_path)
        
        # Use Whisper to transcribe the audio file
        model = whisper.load_model("base")
        result = model.transcribe(temp_audio_path)
        transcription = result["text"]
        logger.info(f"Transcription: {transcription}")
        logger.info(f"File path: {file_path}")
        # Call the response function to generate an expert response
        pipeline = NewsPodcastPipeline()
        interrupt_path = pipeline.user_ask_expert(question=transcription, filepath=file_path)
        logger.info(f"Expert response: {interrupt_path}")
        
        # Clean up the temporary audio file
        os.remove(temp_audio_path)
        
        return jsonify({"response": interrupt_path}), 200
    except Exception as e:
        logger.error(f"Error processing audio file: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def generate_expert_response(transcription: str) -> str:
    """Generates an expert response based on the transcription."""
    # Placeholder function - replace with actual implementation
    return f"Expert response to: {transcription}"

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler for all exceptions."""
    logger.error(f"Unhandled error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    socketio.run(app,
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=True
    )
