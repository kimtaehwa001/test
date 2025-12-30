
import pandas as pd
from django.core.management.base import BaseCommand
from ui.models import UserSmellingInput, TopBottom, Dress, Perfume
from django.conf import settings
from pathlib import Path


class Command(BaseCommand):
    help = 'user_smelling_input.csv 데이터를 읽어 user_smelling_input 테이블에 저장합니다.'

    def handle(self, *args, **kwargs):
        csv_path = Path(settings.BASE_DIR) / 'user_smelling_input.csv'

        # --- [안전한 데이터 변환 함수들] ---
        def safe_int(value):
            if pd.isna(value) or str(value).strip() == '':
                return None
            try:
                return int(float(value))
            except:
                return None

        def safe_str(value):
            if pd.isna(value) or str(value).strip() == '':
                return None
            return str(value).strip()

        try:
            # 1. CSV 읽기
            try:
                df = pd.read_csv(csv_path, encoding='utf-8-sig')
            except:
                df = pd.read_csv(csv_path, encoding='cp949')

            print(f"총 {len(df)}개의 행을 처리합니다.")

            success_count = 0
            fail_count = 0

            for index, row in df.iterrows():
                try:
                    # --- 외래키 객체 조회 (실제 DB에 해당 ID가 있는지 확인) ---

                    # 1. 상의/하의 (TopBottom 모델)
                    t_id = safe_int(row.get('상의_식별자'))
                    top_obj = TopBottom.objects.filter(id=t_id).first() if t_id else None

                    b_id = safe_int(row.get('하의_식별자'))
                    bottom_obj = TopBottom.objects.filter(id=b_id).first() if b_id else None

                    # 2. 원피스 (Dress 모델)
                    d_id = safe_int(row.get('원피스_식별자'))
                    dress_obj = Dress.objects.filter(id=d_id).first() if d_id else None

                    # 3. 향수 (Perfume 모델)
                    p_id = safe_int(row.get('perfume_id'))
                    perfume_obj = Perfume.objects.filter(perfume_id=p_id).first() if p_id else None

                    # --- DB 저장 ---
                    # rate_id를 기준으로 중복 방지 (update_or_create)
                    UserSmellingInput.objects.update_or_create(
                        rate_id=safe_int(row.get('rate_id')),
                        defaults={
                            'smelling_user_id': safe_int(row.get('smelling_user_id')),

                            # 상의 정보
                            'top_id': top_obj,  # ForeignKey 객체 할당
                            'top_color': safe_str(row.get('상의_색상')),
                            'top_category': safe_str(row.get('상의_카테고리')),
                            'top_img': safe_str(row.get('상의_이미지_경로')),

                            # 하의 정보
                            'bottom_id': bottom_obj,  # ForeignKey 객체 할당
                            'bottom_color': safe_str(row.get('하의_색상')),
                            'bottom_category': safe_str(row.get('하의_카테고리')),
                            'bottom_img': safe_str(row.get('하의_이미지_경로')),

                            # 원피스 정보
                            'dress_id': dress_obj,  # ForeignKey 객체 할당
                            'dress_color': safe_str(row.get('원피스_색상')),
                            'dress_img': safe_str(row.get('원피스_이미지_경로')),

                            # 공통/향수 정보
                            'season': safe_str(row.get('계절')),
                            'perfume_id': perfume_obj,  # ForeignKey 객체 할당
                            'brand': safe_str(row.get('Brand')),
                            'perfume_img_url': safe_str(row.get('perfume_img_url')),
                            'smelling_rate': safe_int(row.get('smelling_rate')),
                        }
                    )
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    print(f"❌ {index + 1}행 처리 중 오류: {e}")

                if (index + 1) % 100 == 0:
                    print(f"... {index + 1}개 완료")

            print(f"\n작업 완료! 성공: {success_count}, 실패: {fail_count}")

        except Exception as e:
            print(f"🔥 치명적 오류: {e}")
