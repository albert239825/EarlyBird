"""
Middleware and error handlers for the Flask app.
"""
from flask import jsonify
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


def setup_error_handlers(app):
    """
    Set up error handlers for the Flask app.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(Exception)
    def handle_error(error):
        """Global error handler for all exceptions."""
        logger.error(f"Unhandled error: {str(error)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {str(error)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
