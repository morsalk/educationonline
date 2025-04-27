from app import create_app
from main import register_routes, register_error_handlers, notification_processor

# Create the app
app = create_app()

# Register routes and error handlers
register_routes(app)
register_error_handlers(app)

# Register context processor
app.context_processor(notification_processor)

if __name__ == '__main__':
    try:
        app.run(host='127.0.0.1', port=5000, debug=True)
    except Exception as e:
        print(f"Error starting the application: {e}")
        raise 