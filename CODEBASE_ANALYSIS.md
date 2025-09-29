# Codebase Analysis Report (Live Implementation)

## 1. High-Level Overview

This document provides a comprehensive analysis of the QAI-Agent codebase. The agent is designed to act as a complete "solution architect," transforming a user's simple idea into a sophisticated, fully-implemented software project through a collaborative, state-of-the-art conversational interface.

*   **Architecture:** The system is a **monolithic agent with a modular design**. A central **Orchestrator** acts as the **manager**, delegating decision-making to a dedicated **Router** module and dispatching tasks to various specialized modules (e.g., Planning, Programming, QA) based on their status and the user's intent.

*   **Key Technologies:** Python, a `UnifiedLLM` abstraction layer, and a `UnifiedMemory` system combining vector search (`ChromaDB`) with structured storage (`TinyDB`).

---

## 2. The Collaborative Ideation Workflow (Implemented)

The agent's primary strength is its ability to co-create a buildable prompt from a vague user idea. This is achieved through an interactive, multi-turn collaboration, which is now fully implemented in the codebase.

**Implementation Details:**

The workflow is managed by a state machine within the **Orchestrator**. When a user's request is classified as `IDEATION`, the agent enters a special conversational mode tracked by the `is_in_ideation_session` flag in the `StateManager`. While this flag is active, all user input is routed directly to the **IdeationModule** to continue the dialogue. Once the conversation is complete, a `pending_build_confirmation` flag is set, and the agent waits for the user's final approval (e.g., "Ok build") before proceeding.

**Example Dialogue:**

*   **User:** "Hello my assistant, am feeling innovative today."
*   **Agent (QAI):** "Hey.. that's some good energy to start with.. so what's on your mind, what can we develop?"
*   **User:** "Am thinking a software that can control my green house water needs..."
*   **Agent (QAI):** "Wow.. that's a great idea... I'm thinking we develop a **RUST based application** that reads from various IoTs.. temp, moisture, camera and fertility to communicate to a **central dashboard**... how is my direction?"
*   **User:** "Yeah .. that's right.. now let's have a panel where I can adjust the water level..."

This dialogue continues until the **IdeationModule** determines the prompt is complete and generates the final buildable prompt and confirmation message.

**User Confirmation:**

*   **Agent (QAI):** "...This prompt is buildable. Should I go ahead and queue it in the build?"
*   **User:** "Ok build."

Only after this explicit confirmation does the agent exit the ideation state and proceed to the main development workflow.

---

## 3. Code Correction & Refactoring Workflow (Refined)

When the agent is launched from within a project directory and the user's request is classified as `CODE_CORRECTION`, the agent follows a methodical workflow grounded in the principles from `AGENT.md`.

*   **Step 1: Context & Goal Setting:** The agent confirms the active project directory and asks the user to describe the bug or refactoring task. This establishes the `<task_context>`.

*   **Step 2: Context Gathering (Read-Only Phase):** Adhering to the `CONTEXT_GATHERING_PROMPT` guidelines, the agent uses read-only tools like `search_file_content` (the equivalent of `grep`) and `read_file` to understand the codebase. The goal is to gather all necessary context upfront to form a complete plan.

*   **Step 3: Propose a Plan & Ask for Confirmation:** In line with its "mentor" role, the agent explains its findings and proposes a specific plan, aiming to "fix root causes, not symptoms." For example: *"I've analyzed the code. The bug is in `src/auth.py`. I plan to modify the `login` function to correctly handle the password hash. Shall I proceed?"* No changes are made without user approval.

*   **Step 4: Implementation (Write Phase):** Upon approval, the agent acts, following the `<coding_standards>`. It uses the `robust_replace` tool (a safer equivalent to `str_replace`) to apply precise changes, maintaining the existing code style.

*   **Step 5: Verification:** As required by the `<mark_task_completed_guidelines>`, the agent must verify the fix. It will ask for a test command (e.g., `npm test` or `pytest`) and run it to ensure the issue is truly resolved before marking the task as complete.

---

## 4. Key Component Deep Dive

*   **The Orchestrator (`core/orchestrator.py`):** The brain of the agent. It now acts as the central **manager**. Its `process_query` method uses the `Router` to get a routing decision and then dispatches the request to the appropriate handler within the `ResponseHandler`. It also manages the `is_in_ideation_session` and `is_in_correction_session` flags, and handles `pending_build_confirmation`. Interactive mode for project selection and conversation has been restored.

*   **The Router (`core/router.py`):** This is a new, critical component. It acts as the **decision-maker**. It uses the `manager_routing_prompt.md`, along with the conversation history and the `module_status` (planner/programmer idle/running/interrupted) from the `StateManager`, to determine the most appropriate `route` for the user's request. It returns both the `route` and a user-facing `message`.

*   **The ResponseHandler (`core/response_handler.py`):** This component now acts as the central **dispatcher**. Its `handle_response` method receives the `route` from the `Orchestrator` and calls the corresponding internal method (e.g., `_handle_ideation`, `_continue_correction_workflow`, `_generate_intelligent_response`) to execute the specific workflow logic.

*   **Specialized Modules (`agent_processes/`):** These are specialized modules within the single, core agent. They are now activated by the `ResponseHandler` based on the routing decision.
    *   **Refactoring:** All agent modules (`CodeAssistModule`, `IdeationModule`, `ManagementModule`, `PlanningModule`, `ProgrammingModule`, `ResearchModule`, `ReviewModule`) have been refactored to use `LLMService` for centralized LLM interactions. This involved updating their `__init__` methods to accept an `LLMService` instance and correcting all `generate` method calls to `self.llm_service.llm.generate()`. Unused imports were also removed from these modules.
    *   **`IdeationModule`:** Fully conversational, managing multi-turn dialogues to refine ideas.
    *   `PlanningModule`, `ProgrammingModule`, etc.: These modules are activated *after* the ideation workflow is complete and the user has given approval.

*   **The StateManager (`core/state_manager.py`):** This class now includes `module_status` (tracking planner/programmer state), `is_in_ideation_session`, `is_in_correction_session`, and `pending_build_confirmation` to manage the agent's overall state and ongoing workflows.

*   **The Tool System (`tools/tool_registry.py`):** This system provides the agent's modules with the capabilities to perform concrete actions, such as planning, coding, and analysis.

*   **LLM & Memory (`qllm/`, `memory/`):** These foundational layers provide the agent with intelligence and context. The `UnifiedMemory` system (`memory/unified_memory.py`) implements the Retrieval-Augmented Generation (RAG) functionality, using `ChromaDB` for vector-based semantic search and an ONNX model for generating embeddings. The `ContextBuilder` (`core/context_builder.py`) now leverages `UnifiedMemory.get_conversation_context` to build richer, more context-aware prompts, incorporating recent conversation, semantic search results, and relevant facts about the user.
---

## 5. Data and State Management

*   **Schemas (`schemas/`):** Located at the root of the project, this directory enforces the structure of the JSON data passed between the agent's internal modules, including the new `code_correction_state` within the `orchestration_schema`.
*   **Persistent State (`data/storage/`):</strong All persistent data, including the agent's memory and any software it generates, is stored in the `data/storage` and `projects` directories.
