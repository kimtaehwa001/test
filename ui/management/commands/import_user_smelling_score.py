
import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import UserSmellingMyScore
from django.conf import settings
from pathlib import Path


class Command(BaseCommand):
    help = 'user_smelling_myscore.csv 데이터를 읽어 DB에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR) / 'user_smelling_myscore.csv'

        def safe_int(v):
            if pd.isna(v) or str(v).strip() == '':
                return None
            try:
                return int(float(v))
            except:
                return None

        def safe_float(v):
            if pd.isna(v) or str(v).strip() == '':
                return None
            try:
                return float(v)
            except:
                return None

        try:
            try:
                df = pd.read_csv(csv_path, encoding='utf-8-sig')
            except:
                df = pd.read_csv(csv_path, encoding='cp949')

            print(f"총 {len(df)}개의 행을 처리합니다.")

            success = 0
            fail = 0

            for idx, row in df.iterrows():
                try:
                    UserSmellingMyScore.objects.update_or_create(
                        perfume_id=safe_int(row.get('perfume_id')),
                        user_id=safe_int(row.get('user_id')),
                        defaults={
                            'color_score': safe_float(row.get('color_score')),
                            'season_score': safe_float(row.get('season_score')),
                            'style_score': safe_float(row.get('style_score')),
                            'myscore': safe_float(row.get('myscore')),
                        }
                    )
                    success += 1

                except Exception as e:
                    fail += 1
                    print(f"❌ {idx + 1}행 오류: {e}")

                if (idx + 1) % 1000 == 0:
                    print(f"... {idx + 1}개 완료")

            print(f"\n작업 완료! 성공: {success}, 실패: {fail}")

        except Exception as e:
            print(f"🔥 치명적 오류: {e}")
