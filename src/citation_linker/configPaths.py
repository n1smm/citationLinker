from pathlib import Path
from importlib.resources import files
import os
import sys

APP_NAME = "citation-linker"

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
    if input:
        return "./input"
    else:
        return "./output"

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

    return {
            "config": active_file,
            "input" : active_in,
            "output" : active_out
            }


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
        active_file.write_text(str(config_path))
        return config_path

    # aktiven path, ki je bil ze dodeljen
    if active_file.exists():
        saved_path = Path(active_file.read_text().strip())
        if saved_path.exists():
            return saved_path

    # default path iz paketa
    user_config = user_config_dir() / "user.config"
    if not user_config.exists():
        user_config.write_text(default_config_path().read_text())
    active_file.write_text(str(user_config))
    return user_config


def resolve_dir_paths(dirs):

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
            active_dir(True).write_text(str(input))
            dir_paths["input"] = input
        if output and output.exists():
            active_dir(False).write_text(str(output))
            dir_paths["output"] = output
        else:
            raise FileNotFoundError(f"path for input and/or output dirs don't exist, in: {input}, out: {output}")
        return dir_paths

    active_dirs = {}
    if active_in.exists():
        saved_path = Path(active_in.read_text().strip())
        if saved_path.exists():
            active_dirs["input"] = saved_path
    if active_out.exists():
        saved_path = Path(active_out.read_text().strip())
        if saved_path.exists():
            active_dirs["output"] = saved_path
    if active_dirs:
        return active_dirs

    default_in = Path(default_dir(True)).expanduser().resolve()
    default_out = Path(default_dir(False)).expanduser().resolve()

    if not default_in.exists():
        default_in.mkdir(parents=True, exist_ok=True)
    if not default_out.exists():
        default_out.mkdir(parents=True, exist_ok=True)
    return {
            "input" : default_in,
            "output" : default_out
            }

