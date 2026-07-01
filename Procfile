web: gunicorn parking_system.wsgi --bind 0.0.0.0:$PORT --workers 4 --timeout 120
release: python manage.py migrate --noinput
