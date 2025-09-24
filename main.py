import argparse
import os
import sys
from typing import List, Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import OrchestratorAgent

# Default values from the TypeScript config
DEFAULT_GEMINI_MODEL = "gemini-pro"
DEFAULT_GEMINI_EMBEDDING_MODEL = "embedding-001"

class CliArgs:
    """
    Represents the parsed command-line arguments for the Gemini CLI.
    """
    model: Optional[str]
    llm_mode: Optional[str]
    sandbox: Optional[bool]
    sandbox_image: Optional[str]
    debug: bool
    prompt: Optional[str]
    prompt_interactive: Optional[str]
    all_files: bool
    show_memory_usage: bool
    yolo: bool
    telemetry: Optional[bool]
    telemetry_target: Optional[str]
    telemetry_otlp_endpoint: Optional[str]
    telemetry_log_prompts: Optional[bool]
    telemetry_outfile: Optional[str]
    allowed_mcp_server_names: Optional[List[str]]
    experimental_acp: Optional[bool]
    extensions: Optional[List[str]]
    list_extensions: Optional[bool]
    ide_mode: Optional[bool]
    proxy: Optional[str]
    checkpointing: bool

def parse_arguments() -> CliArgs:
    parser = argparse.ArgumentParser(
        prog='gemini',
        description='Gemini CLI - Launch an interactive CLI, use -p/--prompt for non-interactive mode',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        '-m', '--model',
        type=str,
        help='Model',
        default=os.environ.get('GEMINI_MODEL', DEFAULT_GEMINI_MODEL)
    )
    parser.add_argument(
        '--llm-mode',
        type=str,
        help='LLM mode (online or offline)',
        default=os.environ.get('QAI_LLM_MODE', 'offline')
    )
    parser.add_argument(
        '-p', '--prompt',
        type=str,
        help='Prompt. Appended to input on stdin (if any).'
    )
    parser.add_argument(
        '-i', '--prompt-interactive',
        type=str,
        help='Execute the provided prompt and continue in interactive mode'
    )
    parser.add_argument(
        '-s', '--sandbox',
        action='store_true',
        help='Run in sandbox?'
    )
    parser.add_argument(
        '--sandbox-image',
        type=str,
        help='Sandbox image URI.'
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Run in debug mode?',
        default=False
    )
    parser.add_argument(
        '-a', '--all-files',
        action='store_true',
        help='Include ALL files in context?',
        default=False
    )
    # Deprecated option --all_files
    parser.add_argument(
        '--all_files',
        action='store_true',
        help='(Deprecated) Use --all-files instead. Include ALL files in context?',
        default=False
    )
    parser.add_argument(
        '--show-memory-usage',
        action='store_true',
        help='Show memory usage in status bar',
        default=False
    )
    # Deprecated option --show_memory_usage
    parser.add_argument(
        '--show_memory_usage',
        action='store_true',
        help='(Deprecated) Use --show-memory-usage instead. Show memory usage in status bar',
        default=False
    )
    parser.add_argument(
        '-y', '--yolo',
        action='store_true',
        help='Automatically accept all actions (aka YOLO mode)?',
        default=False
    )
    parser.add_argument(
        '--telemetry',
        action='store_true',
        help='Enable telemetry? This flag specifically controls if telemetry is sent. Other --telemetry-* flags set specific values but do not enable telemetry on their own.'
    )
    parser.add_argument(
        '--telemetry-target',
        type=str,
        choices=['local', 'gcp'],
        help='Set the telemetry target (local or gcp). Overrides settings files.'
    )
    parser.add_argument(
        '--telemetry-otlp-endpoint',
        type=str,
        help='Set the OTLP endpoint for telemetry. Overrides environment variables and settings files.'
    )
    parser.add_argument(
        '--telemetry-log-prompts',
        action='store_true',
        help='Enable or disable logging of user prompts for telemetry. Overrides settings files.'
    )
    parser.add_argument(
        '--telemetry-outfile',
        type=str,
        help='Redirect all telemetry output to the specified file.'
    )
    parser.add_argument(
        '-c', '--checkpointing',
        action='store_true',
        help='Enables checkpointing of file edits',
        default=False
    )
    parser.add_argument(
        '--experimental-acp',
        action='store_true',
        help='Starts the agent in ACP mode'
    )
    parser.add_argument(
        '--allowed-mcp-server-names',
        type=str,
        nargs='*', # 0 or more arguments
        help='Allowed MCP server names'
    )
    parser.add_argument(
        '-e', '--extensions',
        type=str,
        nargs='*', # 0 or more arguments
        help='A list of extensions to use. If not provided, all extensions are used.'
    )
    parser.add_argument(
        '-l', '--list-extensions',
        action='store_true',
        help='List all available extensions and exit.'
    )
    parser.add_argument(
        '--ide-mode',
        action='store_true',
        help='Run in IDE mode?'
    )
    parser.add_argument(
        '--proxy',
        type=str,
        help='Proxy for gemini client, like schema://user:password@host:port'
    )

    # Version and Help are handled by argparse by default, but we can customize.
    # The original uses getCliVersion() for --version, which we'll need to implement later.
    # For now, we'll let argparse handle it.

    args = parser.parse_args()

    # Custom checks from yargs
    if args.prompt and args.prompt_interactive:
        parser.error('Cannot use both --prompt (-p) and --prompt-interactive (-i) together')

    # Handle deprecated options
    if args.all_files:
        print("Warning: --all_files is deprecated. Use --all-files instead.")
        args.all_files = True # Ensure the correct flag is set if deprecated is used
    if args.show_memory_usage:
        print("Warning: --show_memory_usage is deprecated. Use --show-memory-usage instead.")
        args.show_memory_usage = True # Ensure the correct flag is set if deprecated is used

    # Create a CliArgs object from the parsed arguments
    cli_args = CliArgs()
    for arg_name in CliArgs.__annotations__.keys():
        setattr(cli_args, arg_name, getattr(args, arg_name, None))

    return cli_args

if __name__ == '__main__':
    parsed_args = parse_arguments()
    
    try:
        orchestrator = OrchestratorAgent(llm_mode=parsed_args.llm_mode)
        
        if parsed_args.prompt:
            from core.ui import say_user
            say_user(parsed_args.prompt)
            orchestrator.process_query(parsed_args.prompt, "default_user")
        else:
            orchestrator.run()
            
    except Exception as e:
        from core.ui import say_error
        say_error(f"Failed to start orchestrator: {e}")
        sys.exit(1)