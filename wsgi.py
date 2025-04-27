from app import app
import main  # This will register all the routes

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 