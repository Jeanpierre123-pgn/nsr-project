from urllib.parse import urlencode
from urllib.request import urlopen
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Location


NISR_VILLAGE_LAYER = (
    "https://gis-server.statistics.gov.rw/server/rest/services/Hosted/"
    "Village_Boundary_2022/FeatureServer/3/query"
)
FIELDS = (
    "province,province_id,district,district_id,sector,sector_id,"
    "cell,cell_id,village,village_id"
)


class Command(BaseCommand):
    help = "Import Rwanda province-to-village locations from the official NISR 2022 open layer."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=NISR_VILLAGE_LAYER)
        parser.add_argument("--batch-size", type=int, default=2000)

    def handle(self, *args, **options):
        offset = 0
        batch_size = min(max(options["batch_size"], 100), 2000)
        records = []

        while True:
            params = urlencode({
                "where": "1=1",
                "outFields": FIELDS,
                "returnGeometry": "false",
                "resultOffset": offset,
                "resultRecordCount": batch_size,
                "orderByFields": "village_id",
                "f": "json",
            })
            try:
                with urlopen(f"{options['url']}?{params}", timeout=60) as response:
                    payload = json.load(response)
            except Exception as error:
                raise CommandError(f"Could not download NISR locations: {error}") from error
            if payload.get("error"):
                raise CommandError(str(payload["error"]))

            features = payload.get("features", [])
            if not features:
                break
            records.extend(feature.get("attributes", {}) for feature in features)
            if len(features) < batch_size:
                break
            offset += len(features)

        levels = [
            (Location.Level.PROVINCE, "province", "province_id", None),
            (Location.Level.DISTRICT, "district", "district_id", "province_id"),
            (Location.Level.SECTOR, "sector", "sector_id", "district_id"),
            (Location.Level.CELL, "cell", "cell_id", "sector_id"),
            (Location.Level.VILLAGE, "village", "village_id", "cell_id"),
        ]
        created = updated = 0
        with transaction.atomic():
            for level, name_field, code_field, parent_code_field in levels:
                nodes = {}
                for attributes in records:
                    code = str(attributes.get(code_field) or "").strip()
                    name = str(attributes.get(name_field) or "").strip()
                    if code and name:
                        nodes[code] = {
                            "name": name,
                            "parent_code": str(attributes.get(parent_code_field) or "").strip() if parent_code_field else "",
                        }
                codes = list(nodes)
                existing = {
                    item.code: item
                    for item in Location.objects.filter(level=level, code__in=codes)
                }
                missing = [
                    Location(level=level, code=code, name=data["name"])
                    for code, data in nodes.items() if code not in existing
                ]
                Location.objects.bulk_create(missing, batch_size=1000)
                created += len(missing)
                existing.update({
                    item.code: item
                    for item in Location.objects.filter(level=level, code__in=codes)
                })
                parent_lookup = {
                    item.code: item
                    for item in Location.objects.filter(
                        level={
                            Location.Level.DISTRICT: Location.Level.PROVINCE,
                            Location.Level.SECTOR: Location.Level.DISTRICT,
                            Location.Level.CELL: Location.Level.SECTOR,
                            Location.Level.VILLAGE: Location.Level.CELL,
                        }.get(level, ""),
                        code__in=[data["parent_code"] for data in nodes.values() if data["parent_code"]],
                    )
                } if parent_code_field else {}
                changed = []
                for code, data in nodes.items():
                    item = existing[code]
                    parent = parent_lookup.get(data["parent_code"]) if parent_code_field else None
                    if item.name != data["name"] or item.parent_id != (parent.pk if parent else None):
                        item.name = data["name"]
                        item.parent = parent
                        changed.append(item)
                if changed:
                    Location.objects.bulk_update(changed, ["name", "parent"], batch_size=1000)
                    updated += len(changed)

        self.stdout.write(self.style.SUCCESS(
            f"Imported NISR hierarchy: {created:,} created, {updated:,} updated from {len(records):,} village records."
        ))
