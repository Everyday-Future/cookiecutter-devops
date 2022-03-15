cd /d %~dp0

:loop
set LOAD_DOTENV=True
set SERVER_MODE=host
python -B cli.py
goto loop

PAUSE