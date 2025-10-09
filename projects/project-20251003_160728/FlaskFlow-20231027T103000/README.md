# FlaskFlow-20231027T103000

A simple Flask application demonstrating basic project setup and execution.

## Table of Contents
*   [Prerequisites](#prerequisites)
*   [Project Setup](#project-setup)
*   [Running the Application](#running-the-application)

## Prerequisites

Before you begin, ensure you have the following installed:
*   Python 3.x
*   pip (Python package installer, usually comes with Python)

## Project Setup

Follow these steps to set up the project:

1.  **Navigate into the project directory:**
    ```bash
    cd FlaskFlow-20231027T103000
    ```

2.  **Create a Python virtual environment:**
    It's good practice to use a virtual environment to manage project dependencies.
    ```bash
    python3 -m venv venv
    ```

3.  **Activate the virtual environment:**
    *   **On macOS and Linux:**
        ```bash
        source venv/bin/activate
        ```
    *   **On Windows:**
        ```bash
        .\venv\Scripts\activate
        ```

4.  **Install project dependencies:**
    The project includes an `install_dependencies.py` script that will install all required packages listed in `requirements.txt`.
    ```bash
    python3 install_dependencies.py
    ```
    This command will use pip to install Flask and any other specified dependencies.

## Running the Application

Once the project is set up and dependencies are installed, you can run the Flask application:

1.  **Ensure your virtual environment is activated** (as described in step 3 of [Project Setup](#project-setup)).

2.  **Execute the `run.sh` script:**
    This script is designed to start the Flask development server.
    ```bash
    bash run.sh
    ```

3.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:5000` (or the address shown in your terminal after the server starts).
    You should see a "Hello, FlaskFlow!" message.

To stop the application, press `Ctrl+C` in the terminal where it's running.
