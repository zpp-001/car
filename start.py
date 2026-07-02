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

    # Step 2: Seed default admin if DB is available and no admin user exists
    _log("Checking for default admin user ...")
    shell_script = (
        "import os, django;"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_system.settings');"
        "django.setup();"
        "from parking.models import User;"
        "admin_username = os.environ.get('ADMIN_USER', 'admin');"
        "admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123');"
        "admin = User.objects.filter(username=admin_username).first();"
        "if not admin:"
        "    User.objects.create_superuser(username=admin_username, password=admin_password, role='admin');"
        "    print('[start.py] Default admin user created.');"
        "elif admin.role != 'admin':"
        "    admin.role = 'admin';"
        "    admin.save(update_fields=['role']);"
        "    print('[start.py] Admin user role fixed to admin.');"
        "else:"
        "    print('[start.py] Admin user already exists, skipping seed.')"
    )
    ret = subprocess.run([python, manage_py, "shell", "-c", shell_script], capture_output=True, text=True)
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

    # Step 4: Start gunicorn
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
