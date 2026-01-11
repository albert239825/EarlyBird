import sys 
import os
import threading
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import logging
from podcast import PodcastRunner
from backend.podcast.agents.pipeline import NewsPodcastPipeline
from backend.podcast.agents.pipeline import NewsPodcastPipeline
from typing import Dict, Any
import json
from flask_socketio import SocketIO, emit

from backend.podcast.AppData import AppData

from podcast.global_instances import rl_model, graph
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

def emit_data(socketio, new_data) :
    " EMIT NEW DATA TO CLIENT "
    socketio.emit('my_response', {'data': new_data})



AppData.data["emit_function"] = emit_data
AppData.data["socketio"] = socketio

def emit_new_data():
    article_data = AppData.data["Articles"]
    
    # make deep copy, and replace each article["article_data"] with its to_dict()
    new_data = [
        {
            **article,
        }
        for article in article_data
    ]

    for article in new_data:
        article["article_data"] = article["article_data"].to_dict()
    
    # emit new data to client
    emit_data(AppData.data["socketio"], {
        "message": "new_article_info",
        "data": new_data
    })

AppData.data["emit_articles"] = emit_new_data

def continously_emit(socketio):
    """ Continuously emit data to the client every 5 seconds """
    while True:
        pass

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    AppData.data["emit_function"](
            AppData.data["socketio"]
            , {"message:": "Connected to server"}
        )


@app.route("/", methods=["GET"])
def build():
    """Health check endpoint."""
    return jsonify({"message": "Podcast generation service is running"})

runner  = PodcastRunner()
@app.route("/generate", methods=["POST"])  # Ensure it's POST method
def generate():
    """Handles user request, generates a podcast, and returns the file URL."""
    try:
        # data = request.get_json()
        # if not data:
        #     return jsonify({"error": "Invalid JSON data"}), 400
        # data = request.get_json()
        # if not data:
        #     return jsonify({"error": "Invalid JSON data"}), 400

        # interests = data.get("interests", "")
        # logger.info(f"Received interests: {interests}")  # Log interests to see them
        # interests = data.get("interests", "")
        # logger.info(f"Received interests: {interests}")  # Log interests to see them

        # if not interests:
        #     logger.error(f"Missing interests: {interests}")
        #     return jsonify({"error": "Missing interests"}), 400

        # run PodcastRunner on a new thread
        thread = threading.Thread(target=runner.run)
        thread.daemon = True  # Allow the thread to exit when the main program exits
        thread.start()

        return jsonify({"message": "Podcast generation started"}), 200

        # logger.info("Running the podcast runner")
        # result = runner.run()
        # logger.info(f"PodcastRunner result: {result}")  # Log the full result to inspect it
        
        # if result is None or not isinstance(result, Dict):
            # logger.error(f"Invalid response from podcast runner: {result}")
            # return jsonify({"error": "Invalid response from podcast runner"}), 500

        # audio_path = result.get("audio_path")
        # podcast_dir = result.get("podcast_dir")
        # transcript_path = result.get("transcript_path")
        
        # for audio_path_instance in audio_path:
            # if audio_path_instance is None or not os.path.exists(audio_path_instance):
                # logger.error(f"Audio file not found at path: {audio_path_instance}")
                # return jsonify({"error": "Podcast generation failed"}), 500

    except Exception as e:
        logger.exception(f"Error in /generate route: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

    try:
        if audio_path:  # Ensure audio_path is not None
            filenames = os.path.basename(podcast_dir)
            return jsonify({"file_urls": filenames, "podcast_dir": podcast_dir, "transcript_path": transcript_path}), 200
            filenames = os.path.basename(podcast_dir)
            return jsonify({"file_urls": filenames, "podcast_dir": podcast_dir, "transcript_path": transcript_path}), 200
        else:
            logger.error("Audio path is not set.")
            return jsonify({"error": "Internal server error"}), 500
    except Exception as e:
        logger.exception(f"Error serving file {filenames}: {str(e)}")
        logger.exception(f"Error serving file {filenames}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/generate_next", methods=["POST"])  # Ensure it's POST method
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
        podcast_audio_path = os.path.join(podcast_dir, filename, f"interaction_{num}.mp3")
        logger.info(f"Podcast audio path: {podcast_audio_path}")
        if not os.path.exists(podcast_audio_path):
            logger.error(f"Audio file not found: {podcast_audio_path}")
            return jsonify({"error": "File not found"}), 404

        # Serve the file
        return send_from_directory(os.path.dirname(podcast_audio_path), os.path.basename(podcast_audio_path), as_attachment=True)
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

@app.route("/api/graph_init", methods=["GET"])
def graph_init():
    e = graph.generate_init_nodes()
    print('embedding', e)
    graph.update_interest_scores()

    nodes = []
    categories = []
    for i in range(len(graph.nodes)):
        nodes.append({'id': i, 'position': graph.nodes[i].embedding_3d, 'label': '', 'interest_score': 0})
        if graph.nodes[i].section not in categories:
            categories.append(graph.nodes[i].section)
            nodes[i]['label'] = graph.nodes[i].section

    print('nodes', nodes)
    # Return JSON in a format convenient for your frontend
    return jsonify({"nodes": nodes, "edges": []})

@app.route("/api/graph_update/<x>/<y>/<z>", methods=["GET"])
def graph_update(x, y, z):
    graph.update_rl_model(float(x), float(y), float(z))
    print('updated rl')
    graph.update_interest_scores()
    print('updated interest scores')
    print(graph.nodes)

    nodes = []
    categories = []
    for i in range(len(graph.nodes)):
        nodes.append({'id': i, 'position': graph.nodes[i].embedding_3d, 'label': '', 'interest_score': graph.nodes[i].interest_score})
        if graph.nodes[i].section not in categories:
            categories.append(graph.nodes[i].section)
            nodes[i]['label'] = graph.nodes[i].section
    
    print('nodes', nodes)
    print('finished updating')
    # Return JSON in a format convenient for your frontend
    return jsonify({"nodes": nodes, "edges": []})


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
