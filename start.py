"""Startup entrypoint - runs migrations, collects staticfiles, then starts gunicorn."""
import os
import sys
import subprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "parking_system.settings")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _log(msg):
    print(f"[start.py] {msg}", flush=True)

if __name__ == "__main__":
    manage_py = os.path.join(BASE_DIR, "manage.py")
    python = sys.executable

    # Step 1: Run migrations
    _log("Running database migrations ...")
    ret = subprocess.run([python, manage_py, "migrate", "--noinput"])
    if ret.returncode != 0:
        _log(f"Migration failed (code={ret.returncode}), skipping -- gunicorn will still start.")
    else:
        _log("Migrations complete.")

    # Step 2: Seed default admin if DB is available and no users exist
    _log("Checking for default admin user ...")
    ret = subprocess.run([
        python, manage_py, "shell", "-c",
        "import os, django; "
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_system.settings'); "
        "django.setup(); "
        "from parking.models import User; "
        "from django.contrib.auth.hashers import make_password; "
        "if not User.objects.exists(): "
        "    User.objects.create_superuser("
        "        username=os.environ.get('ADMIN_USER', 'admin'), "
        "        password=os.environ.get('ADMIN_PASSWORD', 'admin123'), "
        "        role='admin', "
        "    ); "
        "    print('[start.py] Default admin user created.'); "
        "else: "
        "    print('[start.py] Users already exist, skipping seed.')"
    ], capture_output=True, text=True)
    if ret.returncode == 0:
        for line in ret.stdout.strip().splitlines():
            if "[start.py]" in line:
                _log(line.replace("[start.py] ", ""))
    else:
        _log("Seed admin skipped (DB may be unavailable): " + ret.stderr.strip()[:120])

    # Step 3: Collect static files
    _log("Collecting static files ...")
    ret = subprocess.run([python, manage_py, "collectstatic", "--noinput"])
    if ret.returncode != 0:
        _log(f"collectstatic failed (code={ret.returncode}), skipping -- gunicorn will still start.")
    else:
        _log("Static files collected.")

    # Step 3: Start gunicorn
    port = os.environ.get("PORT", "8000")
    _log(f"Starting gunicorn on 0.0.0.0:{port} ...")
    os.execvp("gunicorn", [
        "gunicorn",
        "parking_system.wsgi:application",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "4",
        "--timeout", "120",
        "--access-logfile", "-",
        "--error-logfile", "-",
    ])
