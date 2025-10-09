# FlaskSpark-20231027T103000

## Description
FlaskSpark-20231027T103000 is a simple Flask web application designed to demonstrate a basic Flask setup. It serves a single page displaying a greeting message, showcasing a minimal but functional Flask project structure.

## Setup Instructions

Follow these steps to get the application up and running on your local machine.

### Prerequisites
*   Python 3.x
*   pip (Python package installer)

### Steps
1.  **Navigate to the project directory**:
    ```bash
    cd FlaskSpark-20231027T103000
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment**:
    *   **On macOS/Linux**:
        ```bash
        source venv/bin/activate
        ```
    *   **On Windows**:
        ```bash
        venv\Scripts\activate
        ```

4.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    Alternatively, you can run the `setup_project.sh` script to automate virtual environment creation and dependency installation:
    ```bash
    ./setup_project.sh
    ```

## How to Run the Application

1.  **Ensure your virtual environment is active** (as per step 3 in Setup Instructions).

2.  **Run the Flask application**:
    ```bash
    flask run
    ```
    *Note: The `.flaskenv` file configures `FLASK_APP=app.py` and `FLASK_DEBUG=1`, so Flask will automatically detect your application and run in debug mode.*

3.  **Access the application**:
    Open your web browser and navigate to the address provided in your terminal, typically:
    ```
    http://127.0.0.1:5000
    ```
    You should see the greeting message served by the `index.html` template.