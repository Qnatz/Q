# FlaskSimpleApp-20231027T103000

A simple Flask application demonstrating basic web server functionality. This project provides a minimal setup for a Flask web application, serving a single HTML page.

## Project Structure

```
FlaskSimpleApp-20231027T103000/
├── app.py
├── requirements.txt
├── README.md
└── templates/
    └── index.html
```

## Installation

Follow these steps to set up and install the project dependencies:

1.  **Navigate to the project directory:**
    Open your terminal or command prompt and change to the project's root directory:
    ```bash
    cd FlaskSimpleApp-20231027T103000
    ```

2.  **Create a virtual environment (recommended):**
    It's good practice to use a virtual environment to manage project dependencies separately.
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        venv\Scripts\activate
        ```

4.  **Install project dependencies:**
    With the virtual environment activated, install the required packages using `pip`:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Once the dependencies are installed, you can run the Flask application:

1.  **Run the Flask application:**
    From the project's root directory (with the virtual environment activated), execute the `app.py` file:
    ```bash
    python app.py
    ```

2.  **Access the application:**
    After running the application, you will see output in your terminal indicating that the Flask server is running. Open your web browser and navigate to the address provided (typically `http://127.0.0.1:5000/`).