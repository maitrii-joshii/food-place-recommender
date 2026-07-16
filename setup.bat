@echo off
echo Initializing git...
git init

echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies...
pip install datasets pandas groq python-dotenv rich tabulate
pip install pytest pytest-cov flake8 black pre-commit

echo Pinning dependencies to requirements.txt...
pip freeze > requirements.txt

echo Configuring pre-commit hooks...
pre-commit install

echo Done!
