
from django.core.management.base import BaseCommand
from ui.models import Weight
from django.db import transaction

class Command(BaseCommand):
    help = 'Weight 테이블에 초기 가중치 데이터(1, 1, 1)를 삽입합니다.'

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # SQL의 INSERT INTO와 동일하지만, 이미 존재할 경우 업데이트하는 안전한 방식
                obj, created = Weight.objects.update_or_create(
                    weight_id=1,
                    defaults={
                        'style_weight': 1.0,
                        'color_weight': 1.0,
                        'season_weight': 1.0
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS('✅ 성공: 가중치 데이터가 새롭게 생성되었습니다. (ID: 1, 값: 1, 1, 1)'))
                else:
                    self.stdout.write(self.style.WARNING('⚠️ 알림: ID 1번 데이터가 이미 존재하여 값만 (1, 1, 1)로 업데이트했습니다.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 오류 발생: {e}'))
