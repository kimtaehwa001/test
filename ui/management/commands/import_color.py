import csv
import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import PerfumeColor
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'perfume_color.csv 파일을 읽어 PerfumeColor 테이블에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR) /'perfume_color.csv'

        try:
            # 1. CSV 읽기 (핵심 수정: utf-8-sig 사용)
            # utf-8-sig는 엑셀 CSV의 특수문자(BOM)를 자동으로 제거해줍니다.
            try:
                df = pd.read_csv(csv_path, encoding='utf-8-sig')
            except UnicodeDecodeError:
                # 만약 utf-8이 아니면 cp949(한글 윈도우 기본)로 시도
                df = pd.read_csv(csv_path, encoding='cp949')

            # 컬럼 이름 공백 제거
            df.columns = df.columns.str.strip()

            # 빈값 처리
            df = df.where(pd.notnull(df), None)

            print(f"--------------------------------------------------")
            print(f"[진단] 총 {len(df)}개의 색상 데이터를 읽었습니다.")
            print(f"[진단] 컬럼 목록: {list(df.columns)}")  # 이제 깔끔하게 나올 겁니다.
            print(f"--------------------------------------------------")

            success_count = 0
            fail_count = 0

            for index, row in df.iterrows():
                try:
                    # 1. Main Accord 가져오기
                    # 컬럼명이 깨져있을 수도 있으니, 포함 여부로 체크하는 안전장치 추가
                    raw_accord = None
                    for col in df.columns:
                        if 'mainaccord' in col.lower():
                            raw_accord = row[col]
                            break

                    if not raw_accord:
                        fail_count += 1
                        continue

                    accord_str = str(raw_accord).strip()

                    # 2. Color 가져오기 & 포맷팅
                    # 엑셀 데이터: (216, 233, 246) -> 목표: rgb(216, 233, 246)
                    raw_color = row.get('color') or row.get('Color')

                    if not raw_color:
                        color_str = '#CCCCCC'
                    else:
                        color_val = str(raw_color).strip()
                        if not color_val.startswith('rgb'):
                            color_str = f"rgb{color_val}"
                        else:
                            color_str = color_val

                    # 3. DB 저장
                    obj, created = PerfumeColor.objects.update_or_create(
                        mainaccord=accord_str,
                        defaults={'color': color_str}
                    )

                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    print(f"❌ [실패] {accord_str} 처리 중 에러: {e}")

            print(f"\n==================================================")
            print(f"✅ 최종 완료!")
            print(f"   - 성공(업데이트/생성): {success_count}")
            print(f"   - 실패(에러): {fail_count}")
            print(f"==================================================")

        except FileNotFoundError:
            print(f"❌ '{csv_path}' 파일을 찾을 수 없습니다.")
        except Exception as e:
            print(f"❌ 치명적 오류: {e}")