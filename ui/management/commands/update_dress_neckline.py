# ui/management/commands/update_dress_neckline.py

import csv
import os
from django.core.management.base import BaseCommand
from ui.models import Dress
from django.conf import settings


class Command(BaseCommand):
    help = '원피스.csv 파일을 읽어 원피스_넥라인 데이터를 업데이트합니다.'

    def handle(self, *args, **options):
        # CSV 파일 경로 (manage.py와 같은 위치에 있을 경우)
        csv_file_path = os.path.join(settings.BASE_DIR, '원피스.csv')

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'파일을 찾을 수 없습니다: {csv_file_path}'))
            return

        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            updated_count = 0

            for row in reader:
                try:
                    # CSV의 '식별자' 컬럼을 기준으로 DB에서 해당 데이터를 찾습니다.
                    # 만약 CSV의 식별자 컬럼명이 다르면 수정하세요.
                    dress_id = row.get('식별자')
                    neckline_value = row.get('원피스_넥라인')

                    if dress_id and neckline_value:
                        # DB에서 해당 ID를 가진 원피스 조회
                        dress = Dress.objects.get(pk=dress_id)
                        dress.dress_neckline = neckline_value
                        dress.save()
                        updated_count += 1
                except Dress.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"ID {dress_id}번 원피스가 DB에 없습니다. 건너뜁니다."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"오류 발생 (ID {dress_id}): {e}"))

        self.stdout.write(self.style.SUCCESS(f'성공적으로 {updated_count}개의 넥라인 데이터를 업데이트했습니다!'))