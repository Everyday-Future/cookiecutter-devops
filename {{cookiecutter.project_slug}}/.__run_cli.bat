cd /d %~dp0

pip install -r requirements.txt
set LOAD_DOTENV=True
set SERVER_MODE=host
:loop
python -B cli.py
goto loop

PAUSE
