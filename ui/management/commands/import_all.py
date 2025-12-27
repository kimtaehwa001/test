from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "모든 CSV 데이터를 한 번에 import합니다."

    def handle(self, *args, **options):
        commands = [
            "import_color",
            "import_clothes_color",
            "import_season",
            "import_perfume",
            "import_topbottom",
            "import_dress",
            "import_user_info",
            "import_classification",
        ]

        for cmd in commands:
            self.stdout.write(f"\n🚀 실행 중: {cmd}")
            try:
                call_command(cmd)
                self.stdout.write(self.style.SUCCESS(f"✅ {cmd} 완료"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ {cmd} 실패: {e}"))
                break
