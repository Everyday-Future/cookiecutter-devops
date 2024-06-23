"""Runner for Flask app"""

from config import Config
from api import create_app

app = create_app()


if __name__ == "__main__":
    app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True,
            threaded=True, host=Config.HOST, port=Config.PORT)
