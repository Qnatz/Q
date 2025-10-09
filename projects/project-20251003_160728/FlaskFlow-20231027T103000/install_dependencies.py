import subprocess
import sys
import os

# Define the path to requirements.txt
REQUIREMENTS_FILE = "requirements.txt"

def install_packages():
    print(f"Installing Python packages from {REQUIREMENTS_FILE} into the active virtual environment...")
    try:
        # Check if requirements.txt exists
        if not os.path.exists(REQUIREMENTS_FILE):
            print(f"Error: {REQUIREMENTS_FILE} not found in the current directory.")
            sys.exit(1)

        # Run pip install using the current Python environment's pip
        # The 'check=True' argument will raise a CalledProcessError if the command returns a non-zero exit code.
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE], check=True)
        print("All packages installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'pip' command not found. Ensure Python and pip are installed and in your PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_packages()
