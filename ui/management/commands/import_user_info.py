import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import UserInfo, TopBottom, Dress
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'user_info.csv 파일을 읽어 UserInfo 테이블에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR)/'user_info.csv'

        # --- 안전한 정수 변환 함수 ---
        def safe_int(value):
            if pd.isna(value) or value == '': return None
            try:
                # 100026.0 -> 100026 변환
                return int(float(str(value).replace(',', '').strip()))
            except ValueError:
                return None

        try:
            # 1. CSV 읽기
            try:
                df = pd.read_csv(csv_path, encoding='cp949')
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding='utf-8')

            # 컬럼 공백 제거
            df.columns = df.columns.str.strip()

            # 빈값(NaN) 처리
            df = df.where(pd.notnull(df), None)

            print(f"--------------------------------------------------")
            print(f"[진단] 총 {len(df)}개의 사용자 데이터를 읽었습니다.")
            print(f"[진단] 컬럼 목록: {list(df.columns)}")
            print(f"--------------------------------------------------")

            success_count = 0
            fail_count = 0

            for index, row in df.iterrows():
                try:
                    # 1. 사용자 ID (PK)
                    raw_user_id = row.get('사용자_식별자') or row.get('user_id')
                    user_id = safe_int(raw_user_id)

                    if not user_id:
                        # PK가 없으면 저장 불가
                        continue

                    # 2. 참조 객체 찾기 (FK 연결)

                    # (A) 상의 연결
                    raw_top = row.get('상의_식별자') or row.get('top_id')
                    top_id = safe_int(raw_top)
                    top_obj = None
                    if top_id:
                        try:
                            top_obj = TopBottom.objects.get(id=top_id)
                        except TopBottom.DoesNotExist:
                            print(f"⚠️ [경고] 상의 ID {top_id}가 TopBottom 테이블에 없습니다. (User: {user_id})")

                    # (B) 하의 연결
                    raw_bottom = row.get('하의_식별자') or row.get('bottom_id')
                    bottom_id = safe_int(raw_bottom)
                    bottom_obj = None
                    if bottom_id:
                        try:
                            bottom_obj = TopBottom.objects.get(id=bottom_id)
                        except TopBottom.DoesNotExist:
                            print(f"⚠️ [경고] 하의 ID {bottom_id}가 TopBottom 테이블에 없습니다. (User: {user_id})")

                    # (C) 원피스 연결
                    raw_dress = row.get('원피스_식별자') or row.get('dress_id')
                    dress_id = safe_int(raw_dress)
                    dress_obj = None
                    if dress_id:
                        try:
                            dress_obj = Dress.objects.get(id=dress_id)
                        except Dress.DoesNotExist:
                            print(f"⚠️ [경고] 원피스 ID {dress_id}가 Dress 테이블에 없습니다. (User: {user_id})")

                    # 3. 기타 정보
                    season_val = row.get('계절') or row.get('season')
                    accord_val = row.get('비선호_향조') or row.get('disliked_accord')

                    # 4. DB 저장 (update_or_create)
                    UserInfo.objects.update_or_create(
                        user_id=user_id,
                        defaults={
                            'top_id': top_obj,
                            'bottom_id': bottom_obj,
                            'dress_id': dress_obj,
                            'season': str(season_val).strip() if season_val else None,
                            'disliked_accord': str(accord_val).strip() if accord_val else None,
                        }
                    )
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    print(f"❌ [실패] User ID {user_id} 처리 중 에러: {e}")

                if (index + 1) % 100 == 0:
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