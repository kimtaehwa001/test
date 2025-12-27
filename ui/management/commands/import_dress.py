import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import Dress, ClothesColor
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = '원피스.csv 파일을 읽어 Dress 테이블에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR)/'원피스.csv'

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
            print(f"[진단] 총 {len(df)}개의 원피스 데이터를 읽었습니다.")
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
                    color_name = row.get('원피스_색상')
                    color_obj = None

                    if color_name:
                        # 색상이 DB에 없으면 자동 생성 (안전을 위해)
                        color_obj, _ = ClothesColor.objects.get_or_create(
                            color=str(color_name).strip()
                        )

                    # 3. DB 저장 (update_or_create)
                    Dress.objects.update_or_create(
                        id=int(float(str(raw_id).replace(',', ''))),  # PK
                        defaults={
                            'style': row.get('스타일'),
                            'sub_style': row.get('서브스타일'),
                            'dress_length': row.get('원피스_기장'),
                            'dress_sleeve_length': row.get('원피스_소매기장'),
                            'dress_color': color_obj,  # FK
                            'dress_material': row.get('원피스_소재'),
                            'dress_print': row.get('원피스_프린트'),
                            'dress_neckline': row.get("원피스_넥라인"),
                            'dress_fit': row.get('원피스_핏'),
                            'dress_detail': row.get('원피스_디테일'),
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