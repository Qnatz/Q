#!/bin/bash

PROJECT_DIR="FlaskSpark-20231027T103000"
VENV_DIR="venv"

echo "Creating root project directory: $PROJECT_DIR"
mkdir "$PROJECT_DIR"

echo "Initializing Python virtual environment inside $PROJECT_DIR/$VENV_DIR"
# Create the virtual environment within a subshell to avoid changing the current directory
(
    cd "$PROJECT_DIR" || {
        echo "Error: Could not enter project directory $PROJECT_DIR"
        exit 1
    }
    
    if command -v python3 &> /dev/null
    then
        python3 -m venv "$VENV_DIR"
    elif command -v python &> /dev/null
    then
        python -m venv "$VENV_DIR"
    else
        echo "Error: Python not found. Please install Python (python3 or python) to create a virtual environment."
        exit 1
    fi
)

if [ $? -eq 0 ]; then
    echo "\nVirtual environment created successfully at $PROJECT_DIR/$VENV_DIR."
    echo "\nNext steps:"
    echo "1. Navigate into your project directory:"
    echo "   cd $PROJECT_DIR"
    echo "2. Activate the virtual environment:"
    echo "   # On macOS/Linux:"
    echo "   source $VENV_DIR/bin/activate"
    echo "   # On Windows (Command Prompt):"
    echo "   $VENV_DIR\\Scripts\\activate.bat"
    echo "   # On Windows (PowerShell):"
    echo "   $VENV_DIR\\Scripts\\Activate.ps1"
    echo "\nProject setup complete. Remember to activate the virtual environment before installing dependencies or running your Flask application."
else
    echo "\nProject setup failed. Please check the error messages above."
fi
