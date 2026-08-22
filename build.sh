#!/usr/bin/env bash
# Script build yang dijalankan Render setiap kali deploy.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
