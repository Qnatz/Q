import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import platform
from pathlib import Path
import dotenv

# Constants for Qai
SETTINGS_DIRECTORY_NAME = ".qai"
QAI_CONFIG_DIR = ".qai"

USER_HOME_DIR = Path.home()
USER_SETTINGS_DIR = USER_HOME_DIR / SETTINGS_DIRECTORY_NAME
USER_SETTINGS_PATH = USER_SETTINGS_DIR / "settings.json"

class SettingScope(Enum):
    User = 'User'
    Workspace = 'Workspace'
    System = 'System'

@dataclass
class CheckpointingSettings:
    enabled: Optional[bool] = None

@dataclass
class SummarizeToolOutputSettings:
    tokenBudget: Optional[int] = None

@dataclass
class AccessibilitySettings:
    disableLoadingPhrases: Optional[bool] = None
    highContrastMode: Optional[bool] = None
    screenReaderSupport: Optional[bool] = None

@dataclass
class TelemetrySettings:
    enabled: Optional[bool] = None
    target: Optional[str] = None  # 'local' or 'cloud'
    otlpEndpoint: Optional[str] = None
    logPrompts: Optional[bool] = None
    outfile: Optional[str] = None

@dataclass
class BugCommandSettings:
    command: Optional[str] = None
    args: Optional[List[str]] = None

@dataclass
class FileFilteringSettings:
    respectGitIgnore: Optional[bool] = None
    respectQaiIgnore: Optional[bool] = None
    enableRecursiveFileSearch: Optional[bool] = None

@dataclass
class MCPServerConfig:
    url: str
    extensionName: Optional[str] = None

@dataclass
class QaiModelSettings:
    defaultModel: Optional[str] = None
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    contextWindow: Optional[int] = None

@dataclass
class UISettings:
    compactMode: Optional[bool] = None
    fontSize: Optional[int] = None
    showSidebar: Optional[bool] = None
    animationEnabled: Optional[bool] = None

@dataclass
class Settings:
    # Core Qai settings
    theme: Optional[str] = None
    customThemes: Dict[str, Any] = field(default_factory=dict)
    selectedAuthType: Optional[str] = None
    sandbox: Optional[bool] = None
    
    # Model configuration
    model: Optional[QaiModelSettings] = None
    
    # Tools and extensions
    coreTools: Optional[List[str]] = None
    excludeTools: Optional[List[str]] = None
    toolDiscoveryCommand: Optional[str] = None
    toolCallCommand: Optional[str] = None
    mcpServerCommand: Optional[str] = None
    mcpServers: Dict[str, MCPServerConfig] = field(default_factory=dict)
    allowMCPServers: Optional[List[str]] = None
    excludeMCPServers: Optional[List[str]] = None
    
    # UI/UX settings
    showMemoryUsage: Optional[bool] = None
    contextFileName: Optional[str] = None
    accessibility: Optional[AccessibilitySettings] = None
    ui: Optional[UISettings] = None
    preferredEditor: Optional[str] = None
    hideWindowTitle: Optional[bool] = None
    hideTips: Optional[bool] = None
    hideBanner: Optional[bool] = None
    vimMode: Optional[bool] = None
    ideMode: Optional[bool] = None
    
    # Performance and behavior
    telemetry: Optional[TelemetrySettings] = None
    usageStatisticsEnabled: Optional[bool] = None
    bugCommand: Optional[BugCommandSettings] = None
    checkpointing: Optional[CheckpointingSettings] = None
    autoConfigureMaxOldSpaceSize: Optional[bool] = None
    fileFiltering: Optional[FileFilteringSettings] = None
    maxSessionTurns: Optional[int] = None
    summarizeToolOutput: Dict[str, SummarizeToolOutputSettings] = field(default_factory=dict)
    disableAutoUpdate: Optional[bool] = None
    memoryDiscoveryMaxDirs: Optional[int] = None

@dataclass
class SettingsError:
    message: str
    path: str

@dataclass
class SettingsFile:
    settings: Settings
    path: Path

class LoadedSettings:
    def __init__(
        self,
        system: SettingsFile,
        user: SettingsFile,
        workspace: SettingsFile,
        errors: List[SettingsError],
    ):
        self.system = system
        self.user = user
        self.workspace = workspace
        self.errors = errors
        self._merged = self._compute_merged_settings()

    @property
    def merged(self) -> Settings:
        return self._merged

    def _compute_merged_settings(self) -> Settings:
        # Merging logic: workspace overrides user, user overrides system
        # For dicts (customThemes, mcpServers), merge recursively
        merged_settings = Settings()

        # Start with system settings
        for key, value in self.system.settings.__dict__.items():
            if value is not None:
                setattr(merged_settings, key, value)

        # Apply user settings, overriding system
        for key, value in self.user.settings.__dict__.items():
            if value is not None:
                if key in ['customThemes', 'mcpServers', 'summarizeToolOutput'] and isinstance(value, dict):
                    current_val = getattr(merged_settings, key, {})
                    setattr(merged_settings, key, {**current_val, **value})
                else:
                    setattr(merged_settings, key, value)

        # Apply workspace settings, overriding user
        for key, value in self.workspace.settings.__dict__.items():
            if value is not None:
                if key in ['customThemes', 'mcpServers', 'summarizeToolOutput'] and isinstance(value, dict):
                    current_val = getattr(merged_settings, key, {})
                    setattr(merged_settings, key, {**current_val, **value})
                else:
                    setattr(merged_settings, key, value)

        return merged_settings

    def for_scope(self, scope: SettingScope) -> SettingsFile:
        if scope == SettingScope.User:
            return self.user
        elif scope == SettingScope.Workspace:
            return self.workspace
        elif scope == SettingScope.System:
            return self.system
        else:
            raise ValueError(f"Invalid scope: {scope}")

    def set_value(self, scope: SettingScope, key: str, value: Any) -> None:
        settings_file = self.for_scope(scope)
        setattr(settings_file.settings, key, value)
        self._merged = self._compute_merged_settings()
        save_settings(settings_file)

def get_system_settings_path() -> Path:
    if os.environ.get("QAI_CLI_SYSTEM_SETTINGS_PATH"):
        return Path(os.environ["QAI_CLI_SYSTEM_SETTINGS_PATH"])

    os_platform = platform.system()
    if os_platform == 'Darwin':  # macOS
        return Path('/Library/Application Support/QaiCli/settings.json')
    elif os_platform == 'Windows':
        return Path('C:\\ProgramData\\qai-cli\\settings.json')
    else:  # Linux and others
        return Path('/etc/qai-cli/settings.json')

def resolve_env_vars_in_string(value: str) -> str:
    import re
    env_var_regex = re.compile(r'\$(?:(\w+)|{([^}]+)})')
    def replace_match(match):
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, match.group(0))
    return env_var_regex.sub(replace_match, value)

def resolve_env_vars_in_object(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj

    if isinstance(obj, str):
        return resolve_env_vars_in_string(obj)

    if isinstance(obj, list):
        return [resolve_env_vars_in_object(item) for item in obj]

    if isinstance(obj, dict):
        new_obj = {}
        for key, value in obj.items():
            new_obj[key] = resolve_env_vars_in_object(value)
        return new_obj

    return obj

def find_env_file(start_dir: Path) -> Optional[Path]:
    current_dir = start_dir.resolve()
    while True:
        # prefer qai-specific .env under QAI_DIR
        qai_env_path = current_dir / QAI_CONFIG_DIR / ".env"
        if qai_env_path.exists():
            return qai_env_path
        env_path = current_dir / ".env"
        if env_path.exists():
            return env_path

        parent_dir = current_dir.parent
        if parent_dir == current_dir:
            # check .env under home as fallback
            home_qai_env_path = USER_HOME_DIR / QAI_CONFIG_DIR / ".env"
            if home_qai_env_path.exists():
                return home_qai_env_path
            home_env_path = USER_HOME_DIR / ".env"
            if home_env_path.exists():
                return home_env_path
            return None
        current_dir = parent_dir

def set_up_cloud_shell_environment(env_filepath: Optional[Path]):
    if env_filepath and env_filepath.exists():
        env_content = env_filepath.read_text()
        parsed_env = dotenv.dotenv_values(stream=env_content)
        if parsed_env.get("QAI_CLOUD_PROJECT"):
            os.environ["QAI_CLOUD_PROJECT"] = parsed_env["QAI_CLOUD_PROJECT"]
        else:
            os.environ["QAI_CLOUD_PROJECT"] = 'qai-cloud'
    else:
        os.environ["QAI_CLOUD_PROJECT"] = 'qai-cloud'

def load_environment():
    env_filepath = find_env_file(Path.cwd())

    if os.environ.get("CLOUD_SHELL") == 'true':
        set_up_cloud_shell_environment(env_filepath)

    if env_filepath:
        dotenv.load_dotenv(dotenv_path=env_filepath, override=True)

def load_settings(workspace_dir: Path) -> LoadedSettings:
    load_environment()
    system_settings: Settings = Settings()
    user_settings: Settings = Settings()
    workspace_settings: Settings = Settings()
    settings_errors: List[SettingsError] = []

    system_settings_path = get_system_settings_path()
    # Load system settings
    try:
        if system_settings_path.exists():
            system_content = system_settings_path.read_text(encoding='utf-8')
            parsed_system_settings = json.loads(system_content)
            system_settings = Settings(**resolve_env_vars_in_object(parsed_system_settings))
    except Exception as e:
        settings_errors.append(SettingsError(message=str(e), path=str(system_settings_path)))

    # Load user settings
    try:
        if USER_SETTINGS_PATH.exists():
            user_content = USER_SETTINGS_PATH.read_text(encoding='utf-8')
            parsed_user_settings = json.loads(user_content)
            user_settings = Settings(**resolve_env_vars_in_object(parsed_user_settings))
            # Support legacy theme names
            if user_settings.theme == 'VS':
                user_settings.theme = "DefaultLight"
            elif user_settings.theme == 'VS2015':
                user_settings.theme = "DefaultDark"
    except Exception as e:
        settings_errors.append(SettingsError(message=str(e), path=str(USER_SETTINGS_PATH)))

    workspace_settings_path = workspace_dir / SETTINGS_DIRECTORY_NAME / "settings.json"

    # Load workspace settings
    try:
        if workspace_settings_path.exists():
            project_content = workspace_settings_path.read_text(encoding='utf-8')
            parsed_workspace_settings = json.loads(project_content)
            workspace_settings = Settings(**resolve_env_vars_in_object(parsed_workspace_settings))
            if workspace_settings.theme == 'VS':
                workspace_settings.theme = "DefaultLight"
            elif workspace_settings.theme == 'VS2015':
                workspace_settings.theme = "DefaultDark"
    except Exception as e:
        settings_errors.append(SettingsError(message=str(e), path=str(workspace_settings_path)))

    return LoadedSettings(
        system=SettingsFile(path=system_settings_path, settings=system_settings),
        user=SettingsFile(path=USER_SETTINGS_PATH, settings=user_settings),
        workspace=SettingsFile(path=workspace_settings_path, settings=workspace_settings),
        errors=settings_errors,
    )

def save_settings(settings_file: SettingsFile):
    try:
        # Ensure the directory exists
        dir_path = settings_file.path.parent
        dir_path.mkdir(parents=True, exist_ok=True)

        with open(settings_file.path, 'w', encoding='utf-8') as f:
            # Convert dataclass to dict for JSON serialization
            settings_dict = settings_file.settings.__dict__
            # Handle nested dataclasses if any, by converting them to dicts
            serializable_settings = json.loads(json.dumps(settings_dict, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o)))
            json.dump(serializable_settings, f, indent=2)
    except Exception as e:
        print(f"Error saving settings file: {e}")
