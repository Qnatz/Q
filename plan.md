# Qai Optimization and Feature Porting Plan

This document outlines a plan for optimizing the Python `Qai` application and porting features, best practices, and tools from the TypeScript packages in the `Q/packages` directory.

## New Features to Port

### 1. IDE Context Awareness via a Local Server (High Priority)

*   **Description:** The `vscode-ide-companion` extension provides real-time IDE context (open files, selections) to the CLI via a local server.
*   **Action:**
    1.  Implement a "sidecar" server in the Python CLI using a lightweight framework like `FastAPI` or `http.server`.
    2.  The server will listen for updates from the VS Code extension.
    3.  Update the `ContextBuilder` to fetch context from this sidecar server.
    4.  Modify the TypeScript extension to send its data to the new Python server endpoint.

### 2. React-based Terminal UI

*   **Description:** The TypeScript CLI uses a React-based approach for a more dynamic and component-driven terminal interface.
*   **Action:** For a more advanced, app-like terminal experience, migrate the UI from `rich` to `Textual`. `Textual` provides a reactive, component-based model similar to React.

### 3. Advanced Code Assistance

*   **Description:** The TypeScript `core` package has an advanced `code_assist` feature that goes beyond simple chat.
*   **Action:** Create a new `CodeAssistAgent` in the Python application to handle complex refactoring, code translation, and interactive assistance.

### 4. Git Integration

*   **Description:** The TypeScript code has a dedicated service for Git operations.
*   **Action:** Create a `GitService` in the Python application using the `GitPython` library to allow agents to interact with the user's repository.

### 5. Agent Loop Detection

*   **Description:** A service to detect and prevent agents from getting stuck in infinite loops.
*   **Action:** Implement a similar utility in Python to monitor agent behavior and prevent runaway processes. This is a crucial feature for robustness.

## Best Practices to Adopt

### 1. Service-Oriented Architecture

*   **Description:** The TypeScript code is structured around small, focused services.
*   **Action:** Continue to refactor the Python codebase into smaller, more focused services (e.g., `FileService`, `GitService`, `ShellService`) to improve modularity and testability.

### 2. Rigorous and Structured Testing

*   **Description:** The TypeScript packages have comprehensive tests for nearly every module.
*   **Action:** Use `pytest` to create a comprehensive test suite with a clear structure, mirroring the `*.test.ts` files found in the TypeScript packages.

### 3. Prompt Registry

*   **Description:** The TypeScript code uses a "prompt registry" to manage and version prompts.
*   **Action:** Evolve the `PromptManager` into a more formal "prompt registry" for better organization, versioning, and retrieval of prompts.

### 4. Structured Telemetry

*   **Description:** The TypeScript code has a sophisticated, well-structured telemetry system.
*   **Action:** Use the structured approach in `packages/core/src/telemetry` as a blueprint to enhance the telemetry and metrics collection in the Python application.

## Tools to Use

### 1. Testing Framework

*   **Tool:** `pytest`
*   **Action:** If not already in use, adopt `pytest` as the standard testing framework.

### 2. Linting and Formatting

*   **Tools:** `ruff` and `black`
*   **Action:** Use `ruff` for high-performance linting and `black` for consistent code formatting.

### 3. Advanced Terminal UI

*   **Tool:** `Textual`
*   **Action:** For a more sophisticated and reactive terminal UI, migrate from `rich` to `Textual`.
