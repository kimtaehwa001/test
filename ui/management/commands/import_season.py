import csv
import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import Perfume, PerfumeSeason
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'perfume.csv 파일을 읽어 PerfumeSeason 테이블에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR)/'perfume_seasons.csv'

        # --- [1] 안전한 숫자 변환 함수 ---
        def safe_float(value):
            if pd.isna(value) or value == '' or value is None:
                return 0.0
            try:
                # 문자열로 바꾸고, 쉼표 제거, 공백 제거
                clean_str = str(value).replace(',', '.').strip()
                return float(clean_str)
            except ValueError:
                return 0.0

        def safe_int(value):
            return int(safe_float(value))

        try:
            # 1. CSV 읽기
            try:
                df = pd.read_csv(csv_path, encoding='cp949')
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding='utf-8')

            # 컬럼 이름 공백 제거
            df.columns = df.columns.str.strip()

            print(f"--------------------------------------------------")
            print(f"[진단] 총 {len(df)}개의 계절 데이터를 읽었습니다.")
            print(f"[진단] 컬럼 목록: {list(df.columns)}")
            print(f"--------------------------------------------------")

            success_count = 0
            fail_count = 0
            skip_count = 0

            for index, row in df.iterrows():
                try:
                    # 1. Perfume ID 확인
                    raw_id = row.get('perfume_id')
                    if pd.isna(raw_id):
                        continue

                    p_id = safe_int(raw_id)

                    # 2. 부모 테이블(Perfume)에 해당 ID가 있는지 확인
                    try:
                        perfume_instance = Perfume.objects.get(perfume_id=p_id)
                    except Perfume.DoesNotExist:
                        # 향수 정보가 먼저 등록되지 않았으면 저장 불가
                        # print(f"⚠️ [건너뜀] 향수 ID {p_id}가 Perfume 테이블에 없습니다.")
                        skip_count += 1
                        continue

                    # 3. 계절 점수 데이터 정제
                    # 대소문자 구분 없이 가져오기 시도
                    spring_val = row.get('spring') or row.get('Spring')
                    summer_val = row.get('summer') or row.get('Summer')
                    fall_val = row.get('fall') or row.get('Fall')
                    winter_val = row.get('winter') or row.get('Winter')

                    # 4. DB 저장 (update_or_create)
                    PerfumeSeason.objects.update_or_create(
                        perfume=perfume_instance,
                        defaults={
                            'spring': safe_float(spring_val),
                            'summer': safe_float(summer_val),
                            'fall': safe_float(fall_val),
                            'winter': safe_float(winter_val),
                        }
                    )
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    print(f"❌ [실패] ID {p_id} 처리 중 에러: {e}")

                if (index + 1) % 500 == 0:
                    print(f"... {index + 1}개 처리 중")

            print(f"\n==================================================")
            print(f"✅ 최종 완료!")
            print(f"   - CSV 전체 행: {len(df)}")
            print(f"   - 성공(DB저장): {success_count}")
            print(f"   - 실패(에러): {fail_count}")
            print(f"   - 건너뜀(향수ID 없음): {skip_count}")
            print(f"==================================================")

            if skip_count > 0:
                print(f"💡 [참고] {skip_count}개의 데이터는 'Perfume' 테이블에 해당 ID가 없어서 건너뛰었습니다.")
                print(f"   (먼저 import_perfume.py를 실행해서 향수 데이터를 모두 넣어야 합니다.)")

        except FileNotFoundError:
            print(f"❌ '{csv_path}' 파일을 찾을 수 없습니다.")
        except Exception as e:
            print(f"❌ 치명적 오류: {e}")