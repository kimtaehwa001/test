import os
import random
from urllib.parse import quote

from django.db import transaction
from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

# DRF(Django REST Framework) 관련 임포트
from rest_framework.views import APIView
from rest_framework import viewsets, filters, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer

# 모델 및 시리얼라이저 임포트
from .models import (
    TopBottom, Dress, ClothesColor, PerfumeColor,
    Perfume, PerfumeSeason, PerfumeClassification, UserInfo, Score
)
from .serializers import (
    TopBottomSerializer,
    DressSerializer,
    ClothesColorSerializer,
    PerfumeColorSerializer,
    PerfumeSeasonSerializer,
    PerfumeSerializer,
    PerfumeClassificationSerializer,
    UserInputSerializer
)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserInputSerializer, RecommendationResultSerializer
from ui.models import Score, Perfume, TopBottom, Dress
from .recommend.calculation_v3 import myscore_cal
# from .recommend.calculation_v2 import myscore_cal
from django.db import transaction
from rest_framework.renderers import JSONRenderer
from .recommend.ver2_LLM import get_llm_recommendation

# =============================================================
# 1. 이미지 데이터 조회 API
# =============================================================
import random
from urllib.parse import quote
from django.conf import settings
from django.core.files.storage import default_storage  # S3 연동 스토리지 라이브러리
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer

import random
from urllib.parse import quote
from django.conf import settings
from django.core.files.storage import default_storage  # S3 연동 스토리지 라이브러리
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer


class FilterImagesAPI(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        # 1. 파라미터 가져오기
        category_en = request.query_params.get('category')
        item_en = request.query_params.get('item')
        color_en = request.query_params.get('color')

        # 필수 파라미터가 없으면 즉시 null 패딩 응답
        if not (category_en and item_en and color_en):
            return Response({'images': [None, None, None, None]})

        # 2. 영문 -> 한글 매핑 (기존 로직 그대로 유지)
        map_category = {'top': '상의', 'bottom': '하의', 'onepiece': '원피스'}
        map_item = {
            'blouse': '블라우스', 'tshirt': '티셔츠', 'knit': '니트웨어', 'shirt': '셔츠', 'hoodie': '후드티',
            'pants': '팬츠', 'jeans': '청바지', 'skirt': '스커트', 'leggings': '레깅스',
            'dress': '드레스', 'jumpsuit': '점프수트'
        }
        map_color = {
            'white': '화이트', 'black': '블랙', 'grey': '그레이', 'navy': '네이비', 'beige': '베이지',
            'pink': '핑크', 'skyblue': '스카이블루', 'brown': '브라운', 'red': '레드', 'green': '그린',
            'gold': '골드', 'silver': '실버'
        }

        cat_kr = map_category.get(category_en)
        item_kr = map_item.get(item_en)
        color_kr = map_color.get(color_en)

        # 매핑된 결과가 없으면 null 패딩 응답
        if not (cat_kr and item_kr and color_kr):
            return Response({'images': [None, None, None, None]})

        # 3. S3 검색 경로 설정 (중요!)
        # collectstatic은 settings.py의 location 설정(보통 'static') 아래에 저장합니다.
        # 따라서 그 하위 경로인 'ui/clothes/...'부터 적어주면 됩니다.
        s3_folder_path = f"ui/clothes/{cat_kr}/{item_kr}/{color_kr}/"

        valid_images = []

        try:
            # 4. S3에서 파일 목록 가져오기
            # default_storage.listdir은 (폴더리스트, 파일리스트)를 반환합니다.
            _, files = default_storage.listdir(s3_folder_path)

            for file in files:
                # 이미지 확장자 필터링
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    # 브라우저가 인식할 수 있도록 한글 및 파일명을 URL 인코딩
                    encoded_cat = quote(cat_kr)
                    encoded_item = quote(item_kr)
                    encoded_color = quote(color_kr)
                    encoded_file = quote(file)

                    # 최종 S3 URL 생성
                    # 예: https://버킷명.s3.amazonaws.com/static/ui/clothes/상의/블라우스/화이트/1.png
                    url_path = f"{settings.STATIC_URL}ui/clothes/{encoded_cat}/{encoded_item}/{encoded_color}/{encoded_file}"
                    valid_images.append(url_path)

        except Exception as e:
            # S3 경로에 폴더가 없거나 접근 에러가 발생할 경우 터미널에 로그 남김
            print(f"❌ S3 Path Error ({s3_folder_path}): {e}")

        # 5. 무작위 4개 선택 (기존 로직 유지)
        selected_images = random.sample(valid_images, min(len(valid_images), 4)) if valid_images else []

        # 6. 부족한 경우 4개가 될 때까지 null로 채움 (기존 로직 유지)
        while len(selected_images) < 4:
            selected_images.append(None)

        return Response({'images': selected_images})
# =============================================================
# 2. 향수 목록 조회 API (검색 기능 추가됨)
# =============================================================
class PerfumeViewSet(viewsets.ModelViewSet):
    """
    [기능]
    1. 전체 향수 목록 조회
    2. 검색 기능 (?search=Chanel 또는 ?search=No.5)
    """
    queryset = Perfume.objects.all().order_by('perfume_id')
    serializer_class = PerfumeSerializer

    # 검색 필터 장착
    filter_backends = [filters.SearchFilter]
    # 브랜드명과 향수명으로 검색 가능
    search_fields = ['brand', 'perfume_name']


# =============================================================
# 3. 기타 데이터 관리 ViewSets (기본 CRUD)
# =============================================================

class ClothesColorViewSet(viewsets.ModelViewSet):
    queryset = ClothesColor.objects.all()
    serializer_class = ClothesColorSerializer


class PerfumeColorViewSet(viewsets.ModelViewSet):
    queryset = PerfumeColor.objects.all()
    serializer_class = PerfumeColorSerializer


class TopBottomViewSet(viewsets.ModelViewSet):
    queryset = TopBottom.objects.all()
    serializer_class = TopBottomSerializer


class DressViewSet(viewsets.ModelViewSet):
    queryset = Dress.objects.all()
    serializer_class = DressSerializer


class PerfumeSeasonViewSet(viewsets.ModelViewSet):
    queryset = PerfumeSeason.objects.all()
    serializer_class = PerfumeSeasonSerializer


class PerfumeClassificationViewSet(viewsets.ModelViewSet):
    queryset = PerfumeClassification.objects.all()
    serializer_class = PerfumeClassificationSerializer


# ui/api_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .serializers import UserInputSerializer
from ui.models import UserInfo, Score, TopBottom, Dress, ClothesColor
from .recommend.calculation_v2 import myscore_cal  # 추천 엔진 임포트


class UserInputView(APIView):
    """
    [기능]
    1. 사용자가 선택한 [아이템 + 색상] 조합이 실제 DB(TopBottom/Dress)에 존재하는지 엄격하게 검사합니다.
    2. 임의의 기본값(면, 노멀 등)을 생성하지 않으며, 매칭되는 데이터가 없으면 에러를 발생시킵니다.
    3. 모든 데이터가 완벽할 때만 UserInfo를 저장하고 자동으로 myscore_cal을 호출합니다.
    """

    def post(self, request):
        serializer = UserInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            # 영문 입력 -> 국문 DB 값 매핑 테이블
            map_item = {
                'blouse': '블라우스', 'tshirt': '티셔츠', 'knit': '니트웨어', 'shirt': '셔츠', 'sleeveless': '탑',
                'hoodie': '후드티', 'sweatshirt': '맨투맨', 'bratop': '브라탑',
                'pants': '팬츠', 'jeans': '청바지', 'skirt': '스커트', 'long_skirt': '롱스커트', 'leggings': '레깅스',
                'jogger': '트레이닝', 'slacks': '슬랙스',
                'dress': '드레스', 'onepiece': '원피스', 'jumpsuit': '점프수트'
            }
            map_color = {
                'white': '화이트', 'black': '블랙', 'beige': '베이지', 'pink': '핑크',
                'skyblue': '스카이블루', 'grey': '그레이', 'brown': '브라운', 'navy': '네이비',
                'red': '레드', 'yellow': '옐로우', 'blue': '블루', 'lavender': '라벤더',
                'wine': '와인', 'silver': '실버', 'orange': '오렌지', 'khaki': '카키',
                'green': '그린', 'purple': '퍼플', 'mint': '민트', 'gold': '골드',
                'neon': '네온',
            }

            final_season = data['season']
            dislikes_str = ", ".join(data.get('disliked_accords', [])) if data.get('disliked_accords') else None

            user_top_obj = None
            user_bottom_obj = None
            user_dress_obj = None

            with transaction.atomic():
                # --- [A] 투피스(상의+하의) 검사 ---
                if data.get('top') and data.get('bottom'):
                    top_color_kr = map_color.get(data.get('top_color'))
                    bottom_color_kr = map_color.get(data.get('bottom_color'))

                    # 색상 객체 조회 (기본 데이터이므로 get 사용)
                    top_color_obj = ClothesColor.objects.get(color=top_color_kr)
                    bottom_color_obj = ClothesColor.objects.get(color=bottom_color_kr)

                    # [Strict] DB에서 해당 카테고리와 색상을 가진 상의가 있는지 찾기
                    top_cat_kr = map_item.get(data['top'])
                    user_top_obj = TopBottom.objects.filter(
                        top_category=top_cat_kr,
                        top_color=top_color_obj
                    ).first()

                    # [Strict] DB에서 해당 카테고리와 색상을 가진 하의가 있는지 찾기
                    bottom_cat_kr = map_item.get(data['bottom'])
                    user_bottom_obj = TopBottom.objects.filter(
                        bottom_category=bottom_cat_kr,
                        bottom_color=bottom_color_obj
                    ).first()

                    # 데이터가 없으면 에러 발생 (임의 생성 안 함)
                    if not user_top_obj or not user_bottom_obj:
                        missing = []
                        if not user_top_obj: missing.append(f"상의({top_cat_kr}-{top_color_kr})")
                        if not user_bottom_obj: missing.append(f"하의({bottom_cat_kr}-{bottom_color_kr})")
                        raise ValueError(f"❌ [데이터 없음] 선택하신 {', '.join(missing)} 데이터가 의류 DB에 존재하지 않습니다.")

                # --- [B] 원피스 검사 ---
                elif data.get('onepiece'):
                    # 1. 프론트에서 보낸 색상 이름을 한글로 변환 (예: 'pink' -> '핑크')
                    onepiece_color_kr = map_color.get(data.get('onepiece_color'))

                    # 2. ClothesColor 테이블에서 색상 객체 조회
                    try:
                        dress_color_obj = ClothesColor.objects.get(color=onepiece_color_kr)
                    except ClothesColor.DoesNotExist:
                        raise ValueError(f"❌ DB에 '{onepiece_color_kr}' 색상 정보가 없습니다.")

                    # 3. [핵심 수정] 서브스타일 명칭('원피스')을 따지지 않고, 해당 색상의 원피스 데이터를 조회
                    user_dress_obj = Dress.objects.filter(
                        dress_color=dress_color_obj
                    ).first()

                    # 4. 만약 해당 색상의 원피스가 DB에 아예 없다면 에러 발생
                    if not user_dress_obj:
                        raise ValueError(
                            f"❌ [데이터 없음] 현재 DB에 '{onepiece_color_kr}' 색상의 원피스 데이터가 존재하지 않습니다.")

                # --- [C] UserInfo 생성 ---
                new_user_info = UserInfo.objects.create(
                    season=final_season,
                    disliked_accord=dislikes_str,
                    top_id=user_top_obj,
                    bottom_id=user_bottom_obj,
                    dress_id=user_dress_obj,
                    top_img=data.get('top_img'),
                    bottom_img=data.get('bottom_img'),
                    dress_img=data.get('onepiece_img'),
                    top_category=map_item.get(data.get('top')),
                    top_color=map_color.get(data.get('top_color')),
                    bottom_category=map_item.get(data.get('bottom')),
                    bottom_color=map_color.get(data.get('bottom_color')),
                    dress_color=map_color.get(data.get('onepiece_color'))
                )

                # --- [D] 자동 추천 계산 실행 ---
                print(f"🔄 [Strict 자동 추천] 사용자 ID: {new_user_info.user_id}")
                top3_scores = myscore_cal(new_user_info.user_id)

                # 기존 점수 삭제 및 새 점수 저장
                Score.objects.filter(user=new_user_info).delete()
                for s in top3_scores:
                    s.save()

            return Response({
                "message": "코디 저장 및 추천 완료",
                "user_id": new_user_info.user_id,
                "top3": [s.perfume.perfume_name for s in top3_scores]
            }, status=status.HTTP_201_CREATED)

        except ClothesColor.DoesNotExist:
            return Response({"error": "DB에 해당 색상 정보가 없습니다."}, status=400)
        except ValueError as ve:
            return Response({"error": str(ve)}, status=400)  # 데이터 없음 에러 처리
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserOutfitAPIView(APIView):
    """
    사용자가 방금 선택한 코디 이미지 경로만 반환하는 전용 API
    """
    renderer_classes = [JSONRenderer]

    def get(self, request):
        # 가장 최근에 저장된 사용자 정보 가져오기
        last_user = UserInfo.objects.last()

        if not last_user:
            return Response({"error": "데이터가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 이미지 경로 데이터만 구성
        data = {
            "top_img": f"{settings.STATIC_URL}{last_user.top_img}" if last_user.top_img else None,
            "bottom_img": f"{settings.STATIC_URL}{last_user.bottom_img}" if last_user.bottom_img else None,
            "onepiece_img": f"{settings.STATIC_URL}{last_user.onepiece_img}" if last_user.onepiece_img else None,
        }
        return Response(data, status=status.HTTP_200_OK)


class ScoreView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        print(f"DEBUG: ScoreView 호출됨, user_id={user_id}")

        if not user_id:
            return Response(
                {"error": "user_id는 필수입니다."},
                status=400
            )

        try:
            user_id = int(user_id)

            # 1️⃣ 점수 계산 (Top3 Score 객체 반환)
            score_objects = myscore_cal(user_id)
            print("🔥 생성된 Score 객체 수:", len(score_objects))

            if not score_objects:
                return Response(
                    {"error": "생성된 score가 없습니다."},
                    status=400
                )

            print(
                "🏆 저장될 Top3 myscore:",
                [s.myscore for s in score_objects]
            )

            # 2️⃣ DB 저장
            # with transaction.atomic():
            #     deleted_count, _ = Score.objects.filter(
            #         user__id=user_id
            #     ).delete()
            #     print("🧹 삭제된 기존 score 수:", deleted_count)
            #
            #     Score.objects.bulk_create(score_objects)
            #     print("✅ bulk_create 완료 (Top3만 저장)")
            with transaction.atomic():
                deleted_count, _ = Score.objects.filter(user_id=user_id).delete()
                print("🧹 삭제된 기존 score 수:", deleted_count)

                for s in score_objects:
                    s.save()
                    print("💾 저장됨:", s.user_id, s.perfume_id, s.myscore)


            return Response(
                {
                    "message": "추천 완료",
                    "count": len(score_objects),
                    "top3_myscore": [s.myscore for s in score_objects],
                },
                status=200
            )

        except Exception as e:
            import traceback
            traceback.print_exc()

            return Response(
                {"error": str(e)},
                status=500
            )
# 2) 추천 알고리즘 점수 계산 및 score 테이블 저장 api
# class RecommendationView(APIView):
#     renderer_classes = [JSONRenderer]
#
#     def get(self, request):
#         user_id = request.query_params.get("user_id")
#         # ... (중략: user_id 체크 로직) ...
#
#         try:
#             data = get_user_data(user_id)
#
#             # 중요: recommend_perfumes 호출 시 인자 이름을 calculation.py의 정의와 일치시킴
#             results = recommend_perfumes(
#                 user_info=[data],
#                 perfume=data["perfumes"],  # get_user_data에서 만든 리스트
#                 perfume_classification=list(PerfumeClassification.objects.all().values("perfume_id", "fragrance")),
#                 perfume_season=list(
#                     PerfumeSeason.objects.all().values("perfume_id", "spring", "summer", "fall", "winter")),
#                 상의_하의=list(TopBottom.objects.all().values()),
#                 원피스=list(Dress.objects.all().values()),
#                 clothes_color=data["clothes_color"],
#                 perfume_color=data["perfume_color"],
#             )
#
#             print(f"DEBUG: 계산된 결과 개수 = {len(results)}")  # 터미널 확인용
#
#             if not results:
#                 return Response({"message": "추천 결과가 없습니다."}, status=200)
#
#             # 기존 데이터 먼저 삭제
#             Score.objects.all().delete()
#
#             # 결과 저장 (update_or_create 사용)
#             with transaction.atomic():
#                 for res in results:
#                     Score.objects.update_or_create(
#                         perfume_id=res["perfume_id"],  # FK 객체 직접 할당 또는 ID
#                         defaults={
#                             "season_score": res["season_score"],
#                             "color_score": res["color_score"],
#                             "style_score": res["style_score"],
#                             "myscore": res["myscore"]
#                         }
#                     )
#
#             return Response({"results": results}, status=status.HTTP_201_CREATED)
#
#         except Exception as e:
#             import traceback
#             traceback.print_exc()  # 에러가 나면 터미널에 상세 내용을 찍음
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class RecommendationResultAPIView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        # 1. 점수와 상관없이 가장 최근 사용자 정보는 무조건 가져옴
        last_user = UserInfo.objects.last()

        # 2. 점수 결과 가져오기 (고장 났더라도 에러 내지 않음)
        results = Score.objects.all().select_related(
            'perfume', 'perfume__season', 'perfume__mainaccord1', 'perfume__mainaccord2', 'perfume__mainaccord3'
        ).order_by('-myscore')

        # 3. 향수 데이터 시리얼라이징 (결과가 있으면 변환, 없으면 빈 리스트)
        perfumes_data = []
        if results.exists():
            perfume_serializer = RecommendationResultSerializer(results, many=True)
            perfumes_data = perfume_serializer.data

        # 4. 최종 응답 (상태 코드 200으로 고정하여 자바스크립트가 멈추지 않게 함)
        response_data = {
            "user_outfit": {
                "top_img": last_user.top_img if last_user else None,
                "bottom_img": last_user.bottom_img if last_user else None,
                "onepiece_img": last_user.dress_img if last_user else None,
            },
            "perfumes": perfumes_data  # 점수 고장 시 빈 배열 [] 이 감
        }
        return Response(response_data, status=status.HTTP_200_OK)


#향수 이미지 api

# class PerfumeTop3ImageAPI(APIView):
#     renderer_classes = [JSONRenderer]
#
#     def get(self, request):
#         # 1. 가장 최근의 사용자 가져오기
#         last_user = UserInfo.objects.last()
#         if not last_user:
#             return Response({"error": "No user info"}, status=404)
#
#         # 2. [수정] 강제 지정 [0, 1, 2]를 지우고 진짜 DB 쿼리 실행
#         # 해당 유저의 점수 데이터를 가져옴
#         top3_scores = Score.objects.filter(user=last_user).select_related('perfume').order_by('-myscore')[:3]
#
#         results = []
#         for score in top3_scores:
#             pid = score.perfume.perfume_id
#             results.append({
#                 "perfume_id": pid,
#                 "image_url": f"/static/ui/perfume_images/{pid}.jpg",
#                 "perfume_name": score.perfume.perfume_name,
#                 "brand": score.perfume.brand,
#                 "myscore": score.myscore,
#                 "gender": score.perfume.gender
#             })
#
#         return Response(results, status=200)

class PerfumeTop3ImageAPI(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        # 1. 테스트를 위해 특정 유저(예: 5번)로 고정하거나, 마지막 유저를 선택
        # target_user = UserInfo.objects.get(user_id=5) # 수동 데이터를 넣은 번호로 고정할 때
        target_user = UserInfo.objects.last()  # 가장 최근 유저를 타겟팅할 때

        if not target_user:
            return Response({"error": "유저 정보가 없습니다."}, status=404)

        # 2. Score 테이블에서 해당 유저의 Top 3 가져오기
        # select_related를 사용하여 성능을 최적화합니다.
        top3_scores = Score.objects.filter(user=target_user).select_related(
            'perfume', 'perfume__mainaccord1', 'perfume__mainaccord2', 'perfume__mainaccord3'
        ).order_by('-myscore')[:3]

        results = []
        for score in top3_scores:
            p = score.perfume

            # 어코드(향조) 리스트 생성
            accords = []
            if p.mainaccord1: accords.append(p.mainaccord1.mainaccord)
            if p.mainaccord2: accords.append(p.mainaccord2.mainaccord)
            if p.mainaccord3: accords.append(p.mainaccord3.mainaccord)

            results.append({
                "perfume_id": p.perfume_id,
                "perfume_name": p.perfume_name,
                "brand": p.brand,
                "gender": p.gender if p.gender else "Unisex",
                "accords": accords,
                "myscore": score.myscore,
                "image_url": f"{settings.STATIC_URL}ui/perfume_images/{p.perfume_id}.jpg"
            })

        return Response(results, status=200)


class RecommendationSummaryAPIView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):

        target_user_id = UserInfo.objects.last().user_id

        try:
            # 2. 강제로 지정한 ID를 LLM 함수에 전달
            summary_text = get_llm_recommendation(target_user_id)
            return Response({"summary": summary_text}, status=200)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"summary": "분석 중 오류가 발생했습니다."}, status=500)
