from pathlib import Path
from importlib.resources import files
import os
import sys

APP_NAME = "citation-linker"

def ensure_defaults():
    """ sets the defaults if not present """
    # Ensure user config directory exists
    print(" ENSURE DEFAULTS FUNC ")
    config_dir = user_config_dir()
    print("config_dir", config_dir)
    
    # Ensure default input/output directories exist
    for is_input in (True, False):
        dir_path = Path(default_dir(is_input)).expanduser().resolve()
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    # Ensure user config file exists
    user_config = config_dir / "user.config"
    if not user_config.exists():
        user_config.write_text(default_config_path().read_text(encoding='utf-8'), encoding='utf-8')
    print ("user config: ", user_config)
    print("=========================")


def user_config_dir():
    """
    Returns the per-user configuration directory for this app.

    Linux:   ~/.config/citation-linker/
    Windows: %APPDATA%\\citation-linker\\
    macOS:   ~/Library/Application Support/citation-linker/
    """
    if sys.platform.startswith("win"):
        base = Path(os.environ["APPDATA"])
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"

    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def active_config_file():
    """
    This file stores ONE line: the full path to the active config file.
    """
    return user_config_dir() / ".active_config_path"

def active_dir(input):
    if input:
        return user_config_dir() / ".active_input_dir"
    else:
        return user_config_dir() / ".active_output_dir"

def default_dir(input):
    """
    Returns the default input/output directory path.
    Uses subdirectories within the app config folder for cross-platform compatibility.
    """
    config_base = user_config_dir()
    if input:
        return str(config_base / "input")
    else:
        return str(config_base / "output")

def default_config_path():
    """
    Returns the path to the read-only default config packaged
    with the application.
    """
    return files("citation_linker.data").joinpath("default.config")

def show_active_paths():
    active_file = active_config_file()
    active_in = active_dir(True)
    active_out = active_dir(False)

    paths = {
                 "config": active_file,
                 "input" : active_in,
                 "output" : active_out
             }

    return {key: value for key, value in paths.items() if value and value.exists()}


def resolve_config_path(cli_config=None):
    """
    Determines which config file to use.

    Priority:
    1. --config CLI argument (persisted)
    2. Previously saved active config
    3. Default config (copied to user space on first run)
    """
    active_file = active_config_file()

    # moznost dodan path z --path
    if cli_config:
        config_path = Path(cli_config).expanduser().resolve()
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        active_file.write_text(str(config_path), encoding='utf-8')
        return config_path

    # aktiven path, ki je bil ze dodeljen
    if active_file.exists():
        saved_path = Path(active_file.read_text(encoding='utf-8').strip())
        if saved_path.exists():
            return saved_path

    # default path iz paketa
    user_config = user_config_dir() / "user.config"
    if not user_config.exists():
        user_config.write_text(default_config_path().read_text(encoding='utf-8'), encoding='utf-8')
    active_file.write_text(str(user_config), encoding='utf-8')
    return user_config


def resolve_dir_paths(dirs=None):

    active_in = active_dir(True)
    active_out = active_dir(False)
    input = ""
    output = ""

    if dirs and (dirs["input"] or dirs["output"]):
        dir_paths = {}
        if dirs["input"]:
            input = Path(dirs["input"]).expanduser().resolve()
        if dirs["output"]:
            output = Path(dirs["output"]).expanduser().resolve()
        if input and input.exists():
            active_dir(True).write_text(str(input), encoding='utf-8')
            dir_paths["input"] = input
        if output and output.exists():
            active_dir(False).write_text(str(output), encoding='utf-8')
            dir_paths["output"] = output
        else:
            raise FileNotFoundError(f"path for input and/or output dirs don't exist, in: {input}, out: {output}")
        return dir_paths

    active_dirs = {}
    if active_in.exists():
        saved_path = Path(active_in.read_text(encoding='utf-8').strip())
        if saved_path.exists():
            active_dirs["input"] = saved_path
    if active_out.exists():
        saved_path = Path(active_out.read_text(encoding='utf-8').strip())
        if saved_path.exists():
            active_dirs["output"] = saved_path
    if active_dirs:
        return active_dirs

    default_in = Path(default_dir(True)).expanduser().resolve()
    default_out = Path(default_dir(False)).expanduser().resolve()

    if not default_in.exists():
        default_in.mkdir(parents=True, exist_ok=True)
    active_dir(True).write_text(str(default_in), encoding='utf-8')
        
    if not default_out.exists():
        default_out.mkdir(parents=True, exist_ok=True)
    active_dir(False).write_text(str(default_out), encoding='utf-8')
    return {
            "input" : default_in,
            "output" : default_out
            }

