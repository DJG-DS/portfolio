import subprocess
import os
import datetime
import sys
from pathlib import Path

from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential

# -------------------------------------------------------------------
# Paths (resolved relative to this file)
# -------------------------------------------------------------------
PYTHON_EXECUTABLE = sys.executable
ROOT_DIR = Path(__file__).resolve().parent  # monitoring_data_collection_tool_github_actions/
SCRIPTS_DIR = ROOT_DIR / "scripts"
LOG_FILE = ROOT_DIR / "documentation" / "logs" / "workflow_log.txt"

DOC_OUTPUT_PATH = ROOT_DIR / "documentation" / "output_dir.txt"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "outputs"

# -------------------------------------------------------------------
# SharePoint / Entra app-only auth (set these via GitHub Secrets)
# -------------------------------------------------------------------
SP_CLIENT_ID = os.environ.get("SP_CLIENT_ID", "")
SP_CLIENT_SECRET = os.environ.get("SP_CLIENT_SECRET", "")
SP_SITE_URL = os.environ.get("SP_SITE_URL", "")  # e.g. https://mhclg.sharepoint.com/sites/DigitalPlanning


def _resolve_output_dir() -> str:
    """Get OUTPUT_DIR from documentation/output_dir.txt if present, else default."""
    try:
        if DOC_OUTPUT_PATH.is_file():
            with open(DOC_OUTPUT_PATH, "r", encoding="utf-8") as f:
                custom_output_dir = f.read().strip()
                return custom_output_dir if custom_output_dir else str(DEFAULT_OUTPUT_DIR)
        return str(DEFAULT_OUTPUT_DIR)
    except Exception as e:
        print(f"Warning: Failed to read output_dir.txt. Using default. Error: {e}")
        return str(DEFAULT_OUTPUT_DIR)


OUTPUT_DIR = _resolve_output_dir()


def log(message: str) -> None:
    """Logs a timestamped message to both the console and a log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {message}"
    print(full_msg)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n")


def run_script(script_path: str, output_dir: str) -> None:
    """Executes a Python script with an output directory argument and logs the result."""
    try:
        subprocess.run(
            [PYTHON_EXECUTABLE, script_path, "--output-dir", output_dir],
            capture_output=True,
            text=True,
            check=True,
        )
        log(f"SUCCESS: {script_path}")
    except subprocess.CalledProcessError as e:
        log(f"FAIL: {script_path}")
        if e.stdout:
            log(f"Stdout:\n{e.stdout.strip()}")
        if e.stderr:
            log(f"Stderr:\n{e.stderr.strip()}")
    except Exception as e:
        log(f"ERROR: {script_path} - {str(e)}")


def _get_sharepoint_ctx() -> ClientContext:
    """Returns a SharePoint ClientContext using Entra ID client credentials."""
    if not (SP_CLIENT_ID and SP_CLIENT_SECRET and SP_SITE_URL):
        raise Exception(
            "Missing one or more required env vars: SP_CLIENT_ID, SP_CLIENT_SECRET, SP_SITE_URL"
        )
    cred = ClientCredential(SP_CLIENT_ID, SP_CLIENT_SECRET)
    return ClientContext(SP_SITE_URL).with_credentials(cred)


def upload_all_outputs_to_sharepoint(output_dir: str) -> None:
    """
    Uploads all CSV files from output_dir to SharePoint using app-only auth.

    Actions:
      1) Auth with client credentials (no interactive/MFA required).
      2) Ensure base folder path exists:
         'Shared Documents/20. Data Management/Reporting/Data files'
      3) Ensure archive path exists:
         '.../Data files/old files/{YYYY-MM-DD}'
      4) Upload each CSV to both base and archive folders.
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    parent_rel = "Shared Documents/20. Data Management/Reporting/Data files"
    archive_parent_rel = f"{parent_rel}/old files"
    dated_rel = f"{archive_parent_rel}/{today_str}"

    ctx = _get_sharepoint_ctx()

    try:
        base_folder = ctx.web.ensure_folder_path(parent_rel).execute_query().value
        ctx.web.ensure_folder_path(archive_parent_rel).execute_query()
        archive_folder = ctx.web.ensure_folder_path(dated_rel).execute_query().value
        log(f"Archive folder ready: {dated_rel}")
    except Exception as e:
        raise Exception(
            f"Cannot access or create required folders.\n"
            f"Base: {parent_rel}\nArchive: {dated_rel}\nError: {e}"
        )

    files = [p for p in Path(output_dir).glob("*.csv")]
    if not files:
        log(f"No CSV files found in '{output_dir}'. Nothing to upload.")
        return

    for p in files:
        file_name = p.name
        log(f"Uploading '{file_name}' to base and archive...")
        try:
            data = p.read_bytes()
            base_folder.upload_file(file_name, data).execute_query()
            archive_folder.upload_file(file_name, data).execute_query()
            log(f"Uploaded: {file_name}")
        except Exception as e:
            log(f"Failed to upload '{file_name}': {e}")

    log(f"All files uploaded to base and archived in 'old files/{today_str}'.")


def main() -> None:
    """
    Executes the full data processing workflow:
      - Run each script in ./scripts (excluding those starting with '_')
      - Upload outputs (CSVs) to SharePoint
    """
    log("Starting workflow...")

    if not SCRIPTS_DIR.exists():
        log(f"Scripts directory not found, skipping script execution: {SCRIPTS_DIR}")
    else:
        py_files = sorted(
            f.name for f in SCRIPTS_DIR.iterdir()
            if f.is_file() and f.name.endswith(".py") and not f.name.startswith("_")
        )
        if not py_files:
            log("No Python scripts found in scripts directory.")
        else:
            for py_file in py_files:
                full_path = str(SCRIPTS_DIR / py_file)
                log(f"Running: {py_file}")
                run_script(full_path, OUTPUT_DIR)

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    log("Uploading outputs to SharePoint...")
    upload_all_outputs_to_sharepoint(OUTPUT_DIR)
    log("Workflow complete.")


if __name__ == "__main__":
    main()
