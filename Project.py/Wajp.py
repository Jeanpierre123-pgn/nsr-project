#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agroconnect.settings")
    from django.core.management import execute_from_command_line

    args = sys.argv[1:] or ["runserver", "127.0.0.1:8000"]
    execute_from_command_line(["Wajp.py", *args])


if __name__ == "__main__":
    main()