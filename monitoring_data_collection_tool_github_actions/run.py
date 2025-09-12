import subprocess
import os
import datetime
import sys
import smtplib
import mimetypes
import socket
import io
import zipfile
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

# Paths
PYTHON_EXECUTABLE = sys.executable
ROOT_DIR = "."
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
LOG_FILE = os.path.join(ROOT_DIR, "documentation/logs", "workflow_log.txt")
DEFAULT_OUTPUT_DIR = os.path.join(ROOT_DIR, "outputs")
DOC_OUTPUT_PATH = os.path.join(ROOT_DIR, "documentation", "output_dir.txt")

try:
    if os.path.isfile(DOC_OUTPUT_PATH):
        with open(DOC_OUTPUT_PATH, "r", encoding="utf-8") as f:
            custom_output_dir = f.read().strip()
            OUTPUT_DIR = custom_output_dir if custom_output_dir else DEFAULT_OUTPUT_DIR
    else:
        OUTPUT_DIR = DEFAULT_OUTPUT_DIR
except Exception:
    OUTPUT_DIR = DEFAULT_OUTPUT_DIR


def log(message: str) -> None:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {message}"
    print(full_msg)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n")


def run_script(script_path: str, output_dir: str) -> None:
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
        log(f"Stdout:\n{(e.stdout or '').strip()}")
        log(f"Stderr:\n{(e.stderr or '').strip()}")
    except Exception as e:
        log(f"ERROR: {script_path} - {str(e)}")


def discover_csvs(output_dir: str) -> list[Path]:
    p = Path(output_dir)
    if not p.exists():
        return []
    return sorted(p.glob("*.csv"))


def total_size(paths: list[Path]) -> int:
    return sum(f.stat().st_size for f in paths if f.exists())


def build_zip_in_memory(files: list[Path], zip_name: str = "outputs.zip") -> tuple[str, bytes]:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.name)
    mem.seek(0)
    return zip_name, mem.read()


def attach_file(msg: EmailMessage, file_path: Path) -> None:
    ctype, encoding = mimetypes.guess_type(file_path.name)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with open(file_path, "rb") as fp:
        msg.add_attachment(
            fp.read(),
            maintype=maintype,
            subtype=subtype,
            filename=file_path.name,
        )


def send_email_with_outputs(output_dir: str) -> None:
    # 🔑 CHANGE THESE:
    SMTP_HOST = "smtp.office365.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "your.email@domain.com"      # <-- your email
    SMTP_PASSWORD = "your-password-here"         # <-- your password / app password
    FROM_ADDR = SMTP_USERNAME         
    TO_ADDRS = ["recipient@domain.com"]          # <-- who gets it

    SUBJECT_PREFIX = "[ODP Outputs]"
    BODY_TEXT = "Automated export attached.\n\nThis email was sent by the workflow script."
    ZIP_THRESHOLD_MB = 15.0
    MAX_ATTACHMENTS = 15

    csv_files = discover_csvs(output_dir)
    if not csv_files:
        log(f"No CSV files found to email in: {output_dir}")
        return

    total_bytes = total_size(csv_files)
    must_zip = total_bytes > ZIP_THRESHOLD_MB * 1024 * 1024 or len(csv_files) > MAX_ATTACHMENTS

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    host = socket.gethostname()
    subject = f"{SUBJECT_PREFIX} {today_str}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_ADDR
    msg["To"] = ", ".join(TO_ADDRS)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    body = f"{BODY_TEXT}\n\nMachine: {host}\nOutput directory: {os.path.abspath(output_dir)}"
    msg.set_content(body)

    if must_zip:
        zip_name, zip_bytes = build_zip_in_memory(csv_files, f"outputs_{today_str}.zip")
        msg.add_attachment(zip_bytes, maintype="application", subtype="zip", filename=zip_name)
        log(
            f"Attaching ZIP '{zip_name}' with {len(csv_files)} files "
            f"(~{total_bytes/1_048_576:.2f} MB) due to size/count threshold."
        )
    else:
        for f in csv_files:
            attach_file(msg, f)
        log(f"Attaching {len(csv_files)} CSV file(s) (~{total_bytes/1_048_576:.2f} MB).")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg, from_addr=FROM_ADDR, to_addrs=TO_ADDRS)
        log(f"Email sent to: {', '.join(TO_ADDRS)}")
    except Exception as e:
        log(f"Failed to send email: {e}")
        raise


def main() -> None:
    log("Starting workflow...")

    if not os.path.exists(SCRIPTS_DIR):
        log(f"Scripts directory not found: {SCRIPTS_DIR}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    py_files = sorted(f for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py") and not f.startswith("_"))

    if not py_files:
        log("No Python scripts found in scripts directory.")
        return

    for py_file in py_files:
        full_path = os.path.join(SCRIPTS_DIR, py_file)
        log(f"Running: {py_file}")
        run_script(full_path, OUTPUT_DIR)

    log("All scripts complete. Emailing outputs...")
    send_email_with_outputs(OUTPUT_DIR)
    log("Workflow complete.")


if __name__ == "__main__":
    main()
