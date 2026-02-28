import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"

def get_env_file_path() -> Path:
    """Get the path to the main .env file, allowing for environment variable overrides."""
    override = os.getenv("JOB_ALERT_ENV_FILE")
    if override:
        return Path(override).expanduser()
    return ROOT_DIR / ".env"

def get_search_config_path() -> Path:
    """Get the path to the job search configuration file."""
    override = os.getenv("JOB_ALERT_SEARCH_CONFIG_FILE")
    if override:
        return Path(override).expanduser()
    return CONFIG_DIR / "job_search_config.env"

def get_candidate_profile_path() -> Path:
    """Get the path to the candidate profile Markdown file."""
    override = os.getenv("JOB_ALERT_CANDIDATE_PROFILE_FILE")
    if override:
        return Path(override).expanduser()
    return CONFIG_DIR / "candidate_profile.md"

def get_past_suggestions_path() -> Path:
    """Get the path to the JSON file storing past job suggestions."""
    override = os.getenv("JOB_ALERT_PAST_SUGGESTIONS_FILE")
    if override:
        return Path(override).expanduser()
    return DATA_DIR / "past_job_suggestions.json"

def get_reports_dir() -> Path:
    """Get the directory path where generated job reports should be saved."""
    override = os.getenv("JOB_ALERT_REPORTS_DIR")
    if override:
        return Path(override).expanduser()
    return ROOT_DIR / "reports"

def load_project_environment() -> None:
    """Load environment variables from project configuration files."""
    env_path = get_env_file_path()
    if env_path.exists():
        load_dotenv(env_path)

    search_config_path = get_search_config_path()
    if search_config_path.exists():
        load_dotenv(search_config_path)
    else:
        print(
            f"[warn] Search config not found at {search_config_path}. Using built-in defaults."
        )
