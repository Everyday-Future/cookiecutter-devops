cd /d %~dp0

set LOAD_DOTENV=True
set SERVER_MODE=host
:loop
venv\Scripts\python -B cli.py
goto loop

PAUSE
