"""Startup entrypoint - runs migrate, then starts gunicorn."""
import os
import sys
import subprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "parking_system.settings")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    manage_py = os.path.join(BASE_DIR, "manage.py")

    # Step 1: Run migrations
    ret = subprocess.run(
        [sys.executable, manage_py, "migrate", "--noinput"],
    )
    if ret.returncode != 0:
        sys.exit(ret.returncode)

    # Step 2: Start gunicorn (replaces the current process)
    port = os.environ.get("PORT", "8000")
    os.execvp("gunicorn", [
        "gunicorn",
        "parking_system.wsgi:application",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "4",
        "--timeout", "120",
    ])
