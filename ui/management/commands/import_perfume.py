import csv
import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import Perfume, PerfumeColor
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'perfume.csv 파일을 읽어 Perfume 테이블에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR)/'perfume.csv'

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
            # 1. CSV 읽기 (cp949, 실패 시 utf-8 시도)
            try:
                df = pd.read_csv(csv_path, encoding='cp949')
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding='utf-8')

            # 컬럼 이름 공백 제거
            df.columns = df.columns.str.strip()

            print(f"--------------------------------------------------")
            print(f"[진단] 총 {len(df)}개의 행을 읽었습니다.")
            print(f"[진단] 컬럼 목록: {list(df.columns)}")
            print(f"--------------------------------------------------")

            success_count = 0
            fail_count = 0

            # 중복 ID 체크용 세트
            processed_ids = set()

            for index, row in df.iterrows():
                try:
                    # -----------------------------------------------------------
                    # 2. 데이터 정제
                    # -----------------------------------------------------------

                    # (1) ID 처리
                    raw_id = row.get('perfume_id')
                    if pd.isna(raw_id) or raw_id == '':
                        print(f"⚠️ [건너뜀] {index + 2}번째 줄: perfume_id가 없습니다.")
                        fail_count += 1
                        continue

                    p_id = safe_int(raw_id)

                    # 중복 ID 경고
                    if p_id in processed_ids:
                        # print(f"ℹ️ [중복] ID {p_id}가 중복되어 덮어씁니다.")
                        pass
                    processed_ids.add(p_id)

                    # (2) 숫자 데이터 처리 (안전 함수 사용)
                    r_val_raw = row.get('RatingValue') or row.get('rating_value')
                    r_cnt_raw = row.get('RatingCount') or row.get('rating_count')
                    year_raw = row.get('Year') or row.get('year')

                    r_val = safe_float(r_val_raw)
                    r_cnt = safe_int(r_cnt_raw)
                    p_year = safe_int(year_raw)
                    if p_year == 0: p_year = None

                    # -----------------------------------------------------------
                    # 3. 어코드(색상) 연결
                    # -----------------------------------------------------------
                    accords = {}
                    for i in range(1, 6):
                        col_key = f'mainaccord{i}'
                        # 대소문자 매칭 시도
                        if col_key not in row:
                            for c in df.columns:
                                if c.lower() == col_key:
                                    col_key = c
                                    break

                        accord_text = row.get(col_key)

                        if pd.notna(accord_text) and str(accord_text).strip() != '':
                            accord_obj, _ = PerfumeColor.objects.get_or_create(
                                mainaccord=str(accord_text).strip(),
                                defaults={'color': '#CCCCCC'}
                            )
                            accords[f'accord{i}'] = accord_obj
                        else:
                            accords[f'accord{i}'] = None

                    # -----------------------------------------------------------
                    # 4. DB 저장
                    # -----------------------------------------------------------
                    Perfume.objects.update_or_create(
                        perfume_id=p_id,
                        defaults={
                            'url': str(row.get('url', '')).strip(),
                            'perfume_name': str(row.get('Perfume') or row.get('perfume') or '').strip(),
                            'brand': str(row.get('Brand') or row.get('brand') or '').strip(),
                            'country': str(row.get('Country') or row.get('country') or '').strip(),
                            'gender': str(row.get('Gender') or row.get('gender') or '').strip(),

                            'rating_value': r_val,
                            'rating_count': r_cnt,
                            'year': p_year,

                            'top': str(row.get('Top', '')).strip(),
                            'middle': str(row.get('Middle', '')).strip(),
                            'base': str(row.get('Base', '')).strip(),

                            'mainaccord1': accords['accord1'],
                            'mainaccord2': accords['accord2'],
                            'mainaccord3': accords['accord3'],
                            'mainaccord4': accords['accord4'],
                            'mainaccord5': accords['accord5'],
                        }
                    )
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    print(f"❌ [실패] ID {p_id} 저장 중 에러: {e}")

                if (index + 1) % 500 == 0:
                    print(f"... {index + 1}개 처리 중")

            print(f"\n==================================================")
            print(f"✅ 최종 완료!")
            print(f"   - CSV 전체 행: {len(df)}")
            print(f"   - 성공(DB저장): {success_count}")
            print(f"   - 실패(건너뜀): {fail_count}")
            print(f"   - 실제 DB에 저장된 ID 개수: {len(processed_ids)}")
            print(f"==================================================")

            if len(df) != len(processed_ids):
                print(f"💡 [참고] CSV 행 개수({len(df)})와 저장된 ID 개수({len(processed_ids)})가 다릅니다.")
                print(f"   이유: CSV 파일 안에 똑같은 perfume_id가 중복되어 들어있기 때문입니다.")
                print(f"   (Django는 중복된 ID가 나오면 에러를 내지 않고 덮어씁니다.)")

        except Exception as e:
            print(f"❌ 치명적 오류: {e}")