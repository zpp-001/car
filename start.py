import os
import sys
import subprocess
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "parking_system.settings")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _log(msg):
    print(f"[start.py] {msg}", flush=True)

if __name__ == "__main__":
    manage_py = os.path.join(BASE_DIR, "manage.py")
    python = sys.executable
    ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
    ADMIN_PWD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Step 1: Run migrations
    _log("Running database migrations ...")
    ret = subprocess.run([python, manage_py, "migrate", "--noinput"])
    if ret.returncode != 0:
        _log(f"Migration failed (code={ret.returncode}), skipping -- gunicorn will still start.")
    else:
        _log("Migrations complete.")

    # 等待数据库就绪，规避刚迁移完的连接延迟
    time.sleep(2)

    # Step 2: 改用Django原生命令创建管理员，不写shell导入模型
    _log("Checking for default admin user ...")
    # 先查询是否存在同名用户
    check_cmd = [
        python, manage_py, "shell", "-c",
        "import django;django.setup();from parking.models import User;print(User.objects.filter(username='{}').exists())".format(ADMIN_USER)
    ]
    check_ret = subprocess.run(check_cmd, capture_output=True, text=True)
    user_exists = check_ret.stdout.strip() == "True"

    if not user_exists:
        # 无交互创建超级用户，指定密码环境变量
        env = os.environ.copy()
        env["DJANGO_SUPERUSER_PASSWORD"] = ADMIN_PWD
        create_cmd = [
            python, manage_py, "createsuperuser",
            "--username", ADMIN_USER,
            "--email", "admin@parking.local",
            "--noinput"
        ]
        create_ret = subprocess.run(create_cmd, env=env, capture_output=True, text=True)
        if create_ret.returncode == 0:
            _log("Default admin user created.")
        else:
            _log(f"Failed to create admin: {create_ret.stderr[:150]}")
    else:
        # 用户已存在，校验角色是否为管理员
        role_check_cmd = [
            python, manage_py, "shell", "-c",
            "import django;django.setup();from parking.models import User;u=User.objects.get(username='{}');print(u.role)".format(ADMIN_USER)
        ]
        role_ret = subprocess.run(role_check_cmd, capture_output=True, text=True)
        current_role = role_ret.stdout.strip()
        if current_role != "admin":
            fix_role_cmd = [
                python, manage_py, "shell", "-c",
                "import django;django.setup();from parking.models import User;u=User.objects.get(username='{}');u.role='admin';u.save()".format(ADMIN_USER)
            ]
            subprocess.run(fix_role_cmd)
            _log("Admin user role fixed to admin.")
        else:
            _log("Admin user already exists, skipping seed.")

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
