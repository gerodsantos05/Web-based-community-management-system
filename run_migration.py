#!/usr/bin/env python
import os
import sys
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HappynessProject.settings')
sys.path.insert(0, str(BASE_DIR))

django.setup()

from django.core.management import call_command
call_command('migrate', interactive=False)
print("Migration completed successfully!")
