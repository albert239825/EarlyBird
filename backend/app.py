"""
Flask application entry point.
Main application initialization and configuration.
"""
import sys
import os
from pathlib import Path

# Add project root to Python path so imports work regardless of how script is run
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from backend.config import Config
from backend.core.podcast_service import PodcastService
from backend.core.state_manager import PodcastState
from backend.api.routes import setup_routes
from backend.api.websocket import setup_websocket_handlers, emit_data, create_emit_articles_function
from backend.api.middleware import setup_error_handlers
from backend.utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging(Config.LOG_LEVEL)
logger = get_logger(__name__)

# Ensure required directories exist
Config.ensure_directories()

# Create Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": Config.CORS_ALLOWED_ORIGINS}})

# Configure app
app.config['PODCAST_DIR'] = str(Config.PODCAST_DIR)
app.config['DEBUG'] = Config.DEBUG

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins=Config.CORS_ALLOWED_ORIGINS)

# Initialize state management
state = PodcastState(socketio=socketio)
state.set_emit_function(emit_data)
state.set_emit_articles_function(create_emit_articles_function(state))

# Initialize podcast service
service = PodcastService(state=state)

# Set up routes, websocket handlers, and error handlers
setup_routes(app, service)
setup_websocket_handlers(socketio, state)
setup_error_handlers(app)

logger.info("EarlyBird Podcast Service initialized successfully")


def main():
    """Run the Flask application"""
    logger.info(f"Starting server on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    socketio.run(
        app,
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.DEBUG
    )


if __name__ == "__main__":
    main()
