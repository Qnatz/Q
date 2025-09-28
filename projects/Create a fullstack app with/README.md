# Full-Stack Application

This is a full-stack application with a Node.js backend and a React frontend.

## Table of Contents

*   [Prerequisites](#prerequisites)
*   [Setup Instructions](#setup-instructions)
    *   [Backend](#backend)
    *   [Frontend](#frontend)
*   [Running the Application](#running-the-application)
    *   [Backend](#backend-1)
    *   [Frontend](#frontend-1)
*   [Usage](#usage)

## Prerequisites

Before you begin, ensure you have the following installed on your system:

*   [Node.js](https://nodejs.org/en/) (which includes npm)

## Setup Instructions

Follow these steps to get the application up and running on your local machine.

### Backend

1.  Navigate to the `backend` directory from the project root:
    ```bash
    cd backend
    ```
2.  Install the necessary Node.js dependencies:
    ```bash
    npm install
    ```

### Frontend

1.  Navigate to the `frontend` directory from the project root:
    ```bash
    cd frontend
    ```
2.  Install the necessary React dependencies:
    ```bash
    npm install
    ```

## Running the Application

You need to run both the backend and frontend servers concurrently. Open two separate terminal windows for this.

### Backend

1.  In your first terminal, navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Start the backend server:
    ```bash
    npm start
    ```
    The backend server will typically run on `http://localhost:5000`.

### Frontend

1.  In your second terminal, navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```
2.  Start the frontend development server:
    ```bash
    npm start
    ```
    The frontend application will typically open in your browser at `http://localhost:3000`. If it doesn't open automatically, navigate to this URL in your web browser.

## Usage

Once both the backend and frontend servers are running, you can interact with the application by opening `http://localhost:3000` in your web browser. The frontend will communicate with the backend to fetch or send data as implemented.