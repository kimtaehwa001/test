import csv
import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import Perfume, PerfumeClassification
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'perfume_classification.csv 파일을 읽어 DB에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR) /'perfume_classification.csv'

        # --- 안전한 숫자 변환 함수 ---
        def safe_int(value):
            if pd.isna(value) or value == '': return 0
            try:
                # 1.0 -> 1로 변환, 쉼표 제거
                return int(float(str(value).replace(',', '').strip()))
            except ValueError:
                return 0

        try:
            # 1. CSV 읽기 (한글 윈도우 엑셀 파일은 cp949)
            try:
                df = pd.read_csv(csv_path, encoding='cp949')
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding='utf-8')

            # 컬럼 이름 공백 제거 (실수 방지)
            df.columns = df.columns.str.strip()

            # 빈값(NaN)을 None으로 처리
            df = df.where(pd.notnull(df), None)

            print(f"--------------------------------------------------")
            print(f"[진단] 총 {len(df)}개의 향조 데이터를 읽었습니다.")
            print(f"[진단] 컬럼 목록: {list(df.columns)}")
            print(f"--------------------------------------------------")

            success_count = 0
            skip_count = 0
            fail_count = 0

            for index, row in df.iterrows():
                try:
                    # 1. Perfume ID 가져오기
                    raw_id = row.get('perfume_id')
                    if not raw_id:
                        continue

                    p_id = safe_int(raw_id)

                    # 2. 부모 향수(Perfume) 존재 확인
                    try:
                        perfume_obj = Perfume.objects.get(perfume_id=p_id)
                    except Perfume.DoesNotExist:
                        # 부모 데이터(향수)가 없으면 저장 불가 -> 건너뜀
                        skip_count += 1
                        continue

                    # 3. Fragrance 데이터 가져오기 (한글 텍스트)
                    # 사진에 있는 컬럼명 'fragrance'를 찾음
                    fragrance_val = row.get('fragrance') or row.get('Fragrance')

                    if fragrance_val:
                        fragrance_str = str(fragrance_val).strip()
                    else:
                        fragrance_str = None

                    # 4. DB 저장 (update_or_create)
                    # 이미 있으면 수정, 없으면 생성
                    PerfumeClassification.objects.update_or_create(
                        perfume=perfume_obj,
                        defaults={
                            'fragrance': fragrance_str
                        }
                    )
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    print(f"❌ [실패] ID {p_id} 처리 중 에러: {e}")

                # 진행상황 출력
                if (index + 1) % 500 == 0:
                    print(f"... {index + 1}개 처리 중")

            print(f"\n==================================================")
            print(f"✅ 최종 완료!")
            print(f"   - 성공(DB저장): {success_count}")
            print(f"   - 건너뜀(부모ID 없음): {skip_count}")
            print(f"   - 실패(에러): {fail_count}")
            print(f"==================================================")

        except FileNotFoundError:
            print(f"❌ '{csv_path}' 파일을 찾을 수 없습니다. manage.py 옆에 있는지 확인하세요.")
        except Exception as e:
            print(f"❌ 치명적 오류: {e}")