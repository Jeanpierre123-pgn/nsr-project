import csv

from django.core.management.base import BaseCommand, CommandError

from core.models import Location


class Command(BaseCommand):
    help = "Import official Rwanda administrative locations from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")

    def handle(self, *args, **options):
        path = options["csv_path"]
        try:
            source = open(path, newline="", encoding="utf-8-sig")
        except OSError as error:
            raise CommandError(str(error)) from error

        required = {"name", "level"}
        created = updated = 0
        with source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or not required.issubset({field.strip().lower() for field in reader.fieldnames}):
                raise CommandError("CSV must include name and level columns; optional columns are code and parent_code.")
            rows = list(reader)
        pending = {str(row.get("code", "")).strip(): row for row in rows if str(row.get("code", "")).strip()}
        for row in rows:
            level = str(row.get("level", "")).strip().lower()
            if level not in Location.Level.values:
                raise CommandError(f"Unsupported location level: {level}")
            parent_code = str(row.get("parent_code", "")).strip()
            parent = Location.objects.filter(code=parent_code).first() if parent_code else None
            if parent_code and parent is None:
                continue
            location, was_created = Location.objects.update_or_create(
                level=level,
                parent=parent,
                name=str(row.get("name", "")).strip(),
                defaults={"code": str(row.get("code", "")).strip()},
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(f"Imported locations: {created} created, {updated} updated."))
