"""Runner for Flask app"""

from api import create_app, global_config

app = create_app()


if __name__ == "__main__":
    app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True,
            threaded=True, host=global_config.HOST, port=global_config.PORT)
