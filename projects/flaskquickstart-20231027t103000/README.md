# FlaskQuickstart-20231027T103000

A simple Flask application quickstart project, demonstrating basic setup and deployment.

## Project Structure

```
FlaskQuickstart-20231027T103000/
├── app.py
├── requirements.txt
└── templates/
    └── index.html
```

## Getting Started

Follow these instructions to set up and run the Flask application on your local machine.

### Prerequisites

Make sure you have Python 3.7+ installed on your system.

You can download Python from [python.org](https://www.python.org/downloads/).

### 1. Clone the Repository (if applicable)

If you received this project as a repository, first clone it:

```bash
git clone <repository-url>
cd FlaskQuickstart-20231027T103000
```

If you have the project files locally, navigate into the project directory:

```bash
cd FlaskQuickstart-20231027T103000
```

### 2. Set Up a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies. This isolates the project's dependencies from your system's Python packages.

**Create the virtual environment:**

```bash
python3 -m venv venv
```

**Activate the virtual environment:**

*   **On macOS/Linux:**
    ```bash
    source venv/bin/activate
    ```

*   **On Windows (Command Prompt):**
    ```bash
    venv\Scripts\activate.bat
    ```

*   **On Windows (PowerShell):**
    ```bash
    .\venv\Scripts\Activate.ps1
    ```

You should see `(venv)` prepended to your terminal prompt, indicating that the virtual environment is active.

### 3. Install Dependencies

Once the virtual environment is active, install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

### 4. Run the Flask Application

With dependencies installed and the virtual environment active, you can now run the Flask application.

**Set Flask environment variables:**

*   **On macOS/Linux:**
    ```bash
    export FLASK_APP=app.py
    export FLASK_ENV=development
    ```

*   **On Windows (Command Prompt):**
    ```bash
    set FLASK_APP=app.py
    set FLASK_ENV=development
    ```

*   **On Windows (PowerShell):**
    ```bash
    $env:FLASK_APP="app.py"
    $env:FLASK_ENV="development"
    ```

**Start the Flask development server:**

```bash
flask run
```

### 5. Access the Application

After running `flask run`, the application will typically be available at:

[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

Open this URL in your web browser to view the application.

### Deactivating the Virtual Environment

When you're done working on the project, you can deactivate the virtual environment by simply running:

```bash
deactivate
```
