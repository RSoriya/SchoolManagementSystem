#!/bin/sh
set -e
python manage.py backup_database --verify
