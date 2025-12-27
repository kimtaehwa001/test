import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import ClothesColor
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'clothes_color.csv 파일을 읽어 ClothesColor 테이블에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR) /'clothes_color.csv'

        try:
            # 1. CSV 읽기 (한글 윈도우 엑셀 호환)
            try:
                # 엑셀 CSV 특유의 BOM 문자 제거를 위해 utf-8-sig 시도
                df = pd.read_csv(csv_path, encoding='utf-8-sig')
            except UnicodeDecodeError:
                # 실패하면 cp949 시도
                df = pd.read_csv(csv_path, encoding='cp949')

            # 컬럼 이름 공백 제거 (' color ' -> 'color')
            df.columns = df.columns.str.strip()

            # 빈값(NaN) 처리
            df = df.where(pd.notnull(df), None)

            print(f"--------------------------------------------------")
            print(f"[진단] 총 {len(df)}개의 색상 데이터를 읽었습니다.")
            print(f"[진단] 컬럼 목록: {list(df.columns)}")
            print(f"--------------------------------------------------")

            success_count = 0
            fail_count = 0

            for index, row in df.iterrows():
                try:
                    # 1. Color 이름 가져오기 (PK)
                    raw_color = row.get('color')
                    if not raw_color:
                        print(f"⚠️ [건너뜀] {index + 2}번째 줄: 색상 이름(color)이 없습니다.")
                        fail_count += 1
                        continue

                    color_name = str(raw_color).strip()



                    raw_rgb = row.get('rgb_tuple')

                    if not raw_rgb:
                        final_rgb = '(204, 204, 204)'  # 값이 없으면 기본 회색
                    else:
                        # 엑셀 값 그대로 공백만 제거해서 저장
                        final_rgb = str(raw_rgb).strip()

                    # 3. DB 저장
                    obj, created = ClothesColor.objects.update_or_create(
                        color=color_name,
                        defaults={'rgb_tuple': final_rgb}
                    )


                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    print(f"❌ [실패] {color_name} 저장 중 에러: {e}")

            print(f"\n==================================================")
            print(f"✅ 최종 완료!")
            print(f"   - 성공: {success_count}건")
            print(f"   - 실패: {fail_count}건")
            print(f"==================================================")

        except FileNotFoundError:
            print(f"❌ '{csv_path}' 파일을 찾을 수 없습니다. manage.py 옆에 있는지 확인하세요.")
        except Exception as e:
            print(f"❌ 치명적 오류: {e}")