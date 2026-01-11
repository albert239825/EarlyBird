"""
WebSocket handlers for real-time communication.
"""
from flask_socketio import emit
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


def setup_websocket_handlers(socketio, state):
    """
    Set up WebSocket event handlers.
    
    Args:
        socketio: Flask-SocketIO instance
        state: PodcastState instance
    """
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info('Client connected')
        if state._emit_function and state.socketio:
            state._emit_function(state.socketio, {"message": "Connected to server"})


def emit_data(socketio, new_data):
    """
    Emit data to connected clients.
    
    Args:
        socketio: Flask-SocketIO instance
        new_data: Data to emit
    """
    socketio.emit('my_response', {'data': new_data})


def create_emit_articles_function(state):
    """
    Create a function to emit article updates.
    
    Args:
        state: PodcastState instance
        
    Returns:
        Function that emits article updates
    """
    def emit_new_data():
        if not state.articles:
            return
            
        article_data = state.articles
        new_data = [{**article} for article in article_data]
        for article in new_data:
            article["article_data"] = article["article_data"].to_dict()
        
        if state._emit_function and state.socketio:
            state._emit_function(state.socketio, {
                "message": "new_article_info",
                "data": new_data
            })
    
    return emit_new_data
