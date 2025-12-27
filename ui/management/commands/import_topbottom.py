import csv
import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import TopBottom, ClothesColor
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = '상의_하의.csv 파일을 읽어 TopBottom 테이블에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR)/'상의_하의.csv'

        try:
            # 1. CSV 읽기 (인코딩 자동 감지)
            try:
                df = pd.read_csv(csv_path, encoding='cp949')
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding='utf-8')

            # 컬럼 이름 공백 제거
            df.columns = df.columns.str.strip()
            # 빈값(NaN)을 None으로 변경
            df = df.where(pd.notnull(df), None)

            print(f"--------------------------------------------------")
            print(f"[진단] 총 {len(df)}개의 상의_하의 데이터를 읽었습니다.")
            print(f"[진단] 컬럼 목록: {list(df.columns)}")
            print(f"--------------------------------------------------")

            success_count = 0
            fail_count = 0

            for index, row in df.iterrows():
                try:
                    # 1. 식별자(ID) 확인
                    raw_id = row.get('식별자')
                    if not raw_id:
                        continue

                    # 2. 색상 처리 (FK 연결을 위해 객체 가져오기)
                    # 상의 색상
                    top_color_name = row.get('상의_색상')
                    top_color_obj = None
                    if top_color_name:
                        # 색상이 DB에 없으면 자동 생성 (RGB는 비워둠)
                        top_color_obj, _ = ClothesColor.objects.get_or_create(
                            color=str(top_color_name).strip()
                        )

                    # 하의 색상
                    bottom_color_name = row.get('하의_색상')
                    bottom_color_obj = None
                    if bottom_color_name:
                        bottom_color_obj, _ = ClothesColor.objects.get_or_create(
                            color=str(bottom_color_name).strip()
                        )

                    # 3. DB 저장 (update_or_create)
                    TopBottom.objects.update_or_create(
                        id=int(float(str(raw_id).replace(',', ''))),  # 식별자 (PK)
                        defaults={
                            'style': row.get('스타일'),
                            'sub_style': row.get('서브스타일'),

                            # 상의 정보
                            'top_color': top_color_obj,  # FK 객체 연결
                            'top_category': row.get('상의_카테고리'),
                            'top_sleeve_length': row.get('상의_소매기장'),  # 컬럼명 확인 필요 (CSV에 '상의_소매'로 되어있을 수도 있음)
                            'top_material': row.get('상의_소재'),
                            'top_print': row.get('상의_프린트'),
                            'top_neckline': row.get('상의_넥라인'),
                            'top_fit': row.get('상의_핏'),

                            # 하의 정보
                            'bottom_length': row.get('하의_기장'),
                            'bottom_color': bottom_color_obj,  # FK 객체 연결
                            'bottom_category': row.get('하의_카테고리'),
                            'bottom_material': row.get('하의_소재'),
                            'bottom_fit': row.get('하의_핏'),

                        }
                    )
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    print(f"❌ [실패] ID {raw_id} 처리 중 에러: {e}")

                # 진행상황 출력
                if (index + 1) % 500 == 0:
                    print(f"... {index + 1}개 처리 중")

            print(f"\n==================================================")
            print(f"✅ 최종 완료!")
            print(f"   - 성공(DB저장): {success_count}")
            print(f"   - 실패(에러): {fail_count}")
            print(f"==================================================")

        except FileNotFoundError:
            print(f"❌ '{csv_path}' 파일을 찾을 수 없습니다.")
        except Exception as e:
            print(f"❌ 치명적 오류: {e}")