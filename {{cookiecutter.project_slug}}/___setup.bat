cd /d %~dp0
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python secret_builder.py local
PAUSE
