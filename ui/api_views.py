import os
import random
from urllib.parse import quote
import unicodedata
from django.contrib.staticfiles.storage import staticfiles_storage

from django.db import transaction
from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe
from django.shortcuts import get_object_or_404
from django.db.models import Q

# DRF(Django REST Framework) 관련 임포트
from rest_framework.views import APIView
from rest_framework import viewsets, filters, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer

# 모델 및 시리얼라이저 임포트
from .models import (
    TopBottom, Dress, ClothesColor, PerfumeColor,
    Perfume, PerfumeSeason, PerfumeClassification, UserInfo, Score, UserSmellingInput
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
# from .recommend.calculation_v2 import myscore_cal #ver2


# from .recommend.calculation_v3 import myscore_cal #ver3 style score 수정
from .recommend.calculation_v4 import myscore_cal  # ver4
from .recommend.weight_cal import find_best_weights  # 가중치 update

from django.db import transaction
from rest_framework.renderers import JSONRenderer

# LLM 관련
from .recommend.for_me_LLM import get_llm_recommendation
from .recommend.for_someone_LLM import get_someone_recommendation
from .recommend.gift_message_LLM import get_someone_gift_message


# =============================================================
# 1. 이미지 데이터 조회 API
# =============================================================
# class FilterImagesAPI(APIView):
#     renderer_classes = [JSONRenderer]
#
#     def get(self, request):
#         category_en = request.query_params.get('category')
#         item_en = request.query_params.get('item')
#         color_en = request.query_params.get('color')
#
#         if not (category_en and item_en and color_en):
#             return Response({'images': [None, None, None, None]})
#
#         # 영한 매핑
#         map_category = {'top': '상의', 'bottom': '하의', 'onepiece': '원피스'}
#         map_item = {
#             'blouse': '블라우스', 'tshirt': '티셔츠', 'knit': '니트웨어', 'shirt': '셔츠', 'hoodie': '후드티',
#             'pants': '팬츠', 'jeans': '청바지', 'skirt': '스커트', 'leggings': '레깅스',
#             'dress': '드레스', 'jumpsuit': '점프수트'
#         }
#         map_color = {
#             'white': '화이트', 'black': '블랙', 'grey': '그레이', 'navy': '네이비', 'beige': '베이지',
#             'pink': '핑크', 'skyblue': '스카이블루', 'brown': '브라운', 'red': '레드', 'green': '그린',
#             'gold': '골드', 'silver': '실버'
#         }
#
#         # 한글 자모 분리 방지를 위해 NFC 정규화 적용
#         cat_kr = unicodedata.normalize('NFC', map_category.get(category_en, ''))
#         item_kr = unicodedata.normalize('NFC', map_item.get(item_en, ''))
#         color_kr = unicodedata.normalize('NFC', map_color.get(color_en, ''))
#
#         if not (cat_kr and item_kr and color_kr):
#             return Response({'images': [None, None, None, None]})
#
#         # S3 내부 경로 (static 폴더 내부의 경로만 적음)
#         s3_folder_path = f"ui/clothes/{cat_kr}/{item_kr}/{color_kr}/"
#         valid_images = []
#
#         try:
#             print(f"🔍 S3 static 검색 시도 : {s3_folder_path}")
#
#             # [핵심 수정] staticfiles_storage를 사용해야 S3의 'static/' 폴더 안을 뒤집니다.
#             _, files = staticfiles_storage.listdir(s3_folder_path)
#
#             print(f"✅ S3에서 찾은 파일 개수 : {len(files)}")
#
#             for file in files:
#                 if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
#                     encoded_cat = quote(cat_kr)
#                     encoded_item = quote(item_kr)
#                     encoded_color = quote(color_kr)
#                     encoded_file = quote(file)
#
#                     url_path = f"{settings.STATIC_URL}ui/clothes/{encoded_cat}/{encoded_item}/{encoded_color}/{encoded_file}"
#                     valid_images.append(url_path)
#         except Exception as e:
#             print(f"❌ S3 Path Error: {e}")
#
#         selected_images = random.sample(valid_images, min(len(valid_images), 4)) if valid_images else []
#         while len(selected_images) < 4:
#             selected_images.append(None)
#
#         return Response({'images': selected_images})

_S3_FOLDER_CACHE = {}


class FilterImagesAPI(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        category_en = request.query_params.get('category')
        item_en = request.query_params.get('item')
        color_en = request.query_params.get('color')

        if not (category_en and item_en and color_en):
            return Response({'images': [None, None, None, None]})

        # 영한 매핑 (기존과 동일)
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

        # 한글 정규화 (기존과 동일)
        cat_kr = unicodedata.normalize('NFC', map_category.get(category_en, ''))
        item_kr = unicodedata.normalize('NFC', map_item.get(item_en, ''))
        color_kr = unicodedata.normalize('NFC', map_color.get(color_en, ''))

        if not (cat_kr and item_kr and color_kr):
            return Response({'images': [None, None, None, None]})

        s3_folder_path = f"ui/clothes/{cat_kr}/{item_kr}/{color_kr}/"

        # --- [최적화 시작] ---
        # 이미 메모리에 저장된 목록이 있는지 확인
        if s3_folder_path in _S3_FOLDER_CACHE:
            files = _S3_FOLDER_CACHE[s3_folder_path]
            print(f"📦 [Cache] S3 통신 없이 메모리에서 불러옴: {s3_folder_path}")
        else:
            try:
                print(f"🌐 [Network] S3 목록 조회 시도 (최초 1회): {s3_folder_path}")
                _, files = staticfiles_storage.listdir(s3_folder_path)
                # 찾은 파일 목록을 메모리에 저장
                _S3_FOLDER_CACHE[s3_folder_path] = files
                print(f"✅ S3에서 찾은 파일 개수 : {len(files)}")
            except Exception as e:
                print(f"❌ S3 Path Error: {e}")
                files = []
        # --- [최적화 끝] ---

        valid_images = []
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                encoded_cat = quote(cat_kr)
                encoded_item = quote(item_kr)
                encoded_color = quote(color_kr)
                encoded_file = quote(file)

                url_path = f"{settings.STATIC_URL}ui/clothes/{encoded_cat}/{encoded_item}/{encoded_color}/{encoded_file}"
                valid_images.append(url_path)

        # 4개 랜덤 선택 (기존과 동일)
        selected_images = random.sample(valid_images, min(len(valid_images), 4)) if valid_images else []
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


class UserInputView(APIView):
    """
    [기능]
    1. 사용자가 선택한 [아이템 + 색상] 조합이 실제 DB(TopBottom/Dress)에 존재하는지 엄격하게 검사합니다.
    2. [추가] 선물 대상(recipient)과 상황(situation)은 DB 필드가 없으므로 세션(Session)에 임시 저장합니다.
    3. 임의의 기본값(면, 노멀 등)을 생성하지 않으며, 매칭되는 데이터가 없으면 에러를 발생시킵니다.
    4. 모든 데이터가 완벽할 때만 UserInfo를 저장하고 자동으로 myscore_cal을 호출합니다.
    """

    def post(self, request):
        serializer = UserInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            # --- [추가] 선물 관련 정보 세션 저장 (DB 저장 X) ---
            # 프론트에서 넘어온 한글 텍스트("연인", "생일" 등)를 세션에 저장하여 LLM에서 사용
            request.session['recipient'] = data.get('recipient')
            request.session['situation'] = data.get('situation')
            request.session.modified = True  # 세션 변경사항 강제 적용

            # 영문 입력 -> 국문 DB 값 매핑 테이블 (기존 기능 유지)
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
                # --- [A] 투피스(상의+하의) 검사 (기존 로직 유지) ---
                if data.get('top') and data.get('bottom'):
                    top_color_kr = map_color.get(data.get('top_color'))
                    bottom_color_kr = map_color.get(data.get('bottom_color'))

                    # 색상 객체 조회
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

                    # 데이터가 없으면 에러 발생
                    if not user_top_obj or not user_bottom_obj:
                        missing = []
                        if not user_top_obj: missing.append(f"상의({top_cat_kr}-{top_color_kr})")
                        if not user_bottom_obj: missing.append(f"하의({bottom_cat_kr}-{bottom_color_kr})")
                        raise ValueError(f"❌ [데이터 없음] 선택하신 {', '.join(missing)} 데이터가 의류 DB에 존재하지 않습니다.")

                # --- [B] 원피스 검사 (기존 로직 유지) ---
                elif data.get('onepiece'):
                    onepiece_color_kr = map_color.get(data.get('onepiece_color'))

                    try:
                        dress_color_obj = ClothesColor.objects.get(color=onepiece_color_kr)
                    except ClothesColor.DoesNotExist:
                        raise ValueError(f" DB에 '{onepiece_color_kr}' 색상 정보가 없습니다.")

                    # 해당 색상의 원피스 데이터 조회
                    user_dress_obj = Dress.objects.filter(
                        dress_color=dress_color_obj
                    ).first()

                    if not user_dress_obj:
                        raise ValueError(f" [데이터 없음] 현재 DB에 '{onepiece_color_kr}' 색상의 원피스 데이터가 존재하지 않습니다.")

                # --- [C] UserInfo 생성 (기존 필드 유지, recipient/situation은 넣지 않음) ---
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

                # --- [D] 자동 추천 계산 및 Score 저장 (기존 로직 유지) ---
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
            return Response({"error": str(ve)}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserOutfitAPIView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        last_user = UserInfo.objects.last()
        if not last_user:
            return Response({"error": "데이터가 없습니다."}, status=404)

        # 주소가 이미 전체 URL(http로 시작)인지 체크해서 처리합니다.
        def get_full_url(path):
            if not path: return None
            if path.startswith('http'): return path
            return f"{settings.STATIC_URL}{path}"

        data = {
            "top_img": get_full_url(last_user.top_img),
            "bottom_img": get_full_url(last_user.bottom_img),
            "onepiece_img": get_full_url(last_user.dress_img),
        }
        return Response(data, status=200)

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
            print(" 생성된 Score 객체 수:", len(score_objects))

            if not score_objects:
                return Response(
                    {"error": "생성된 score가 없습니다."},
                    status=400
                )

            print(
                " 저장될 Top3 myscore:",
                [s.myscore for s in score_objects]
            )

            with transaction.atomic():
                deleted_count, _ = Score.objects.filter(user_id=user_id).delete()
                print(" 삭제된 기존 score 수:", deleted_count)

                for s in score_objects:
                    s.save()
                    print(" 저장됨:", s.user_id, s.perfume_id, s.myscore)

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
        last_user = UserInfo.objects.last()
        results = Score.objects.filter(user=last_user).select_related(
            'perfume', 'perfume__season'
        ).order_by('-myscore')

        perfumes_data = []
        if results.exists():
            perfume_serializer = RecommendationResultSerializer(results, many=True)
            perfumes_data = perfume_serializer.data

        # 주소 중복 방지 로직 적용
        def get_full_url(path):
            if not path: return None
            if path.startswith('http'): return path
            return f"{settings.STATIC_URL}{path}"

        response_data = {
            "user_outfit": {
                "top_img": get_full_url(last_user.top_img) if last_user else None,
                "bottom_img": get_full_url(last_user.bottom_img) if last_user else None,
                "onepiece_img": get_full_url(last_user.dress_img) if last_user else None,
            },
            "perfumes": perfumes_data
        }
        return Response(response_data, status=200)


# 향수 이미지 api

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
        target_user = UserInfo.objects.last()
        if not target_user:
            return Response({"error": "유저 정보가 없습니다."}, status=404)

        top3_scores = Score.objects.filter(user=target_user).select_related(
            'perfume', 'perfume__mainaccord1', 'perfume__mainaccord2', 'perfume__mainaccord3'
        ).order_by('-myscore')[:3]

        results = []
        for score in top3_scores:
            p = score.perfume
            accords = [a.mainaccord for a in [p.mainaccord1, p.mainaccord2, p.mainaccord3] if a]

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


class MyNoteStyleAPIView(APIView):
    """
    MyNote 4-1
    - 코디 + 계절 선택
    - 옷 정보까지 session에 저장
    """

    def post(self, request):
        style_type = request.data.get("style_type")
        season = request.data.get("season")

        if not style_type or not season:
            return Response(
                {"error": "style_type과 season은 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 옷 정보도 같이 저장
        request.session["my_note_style"] = {
            "style_type": style_type,
            "season": season,

            # 투피스
            "top": request.data.get("top"),
            "bottom": request.data.get("bottom"),

            # 원피스
            "dress": request.data.get("dress"),
        }

        request.session.modified = True

        return Response(
            {"message": "스타일 저장 완료"},
            status=status.HTTP_200_OK
        )


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class MyNotePerfumeCartAPIView(APIView):
    """
    MyNote 4-2 향수 장바구니 (session)
    - GET    : 장바구니 목록
    - POST   : 추가 or 점수 수정
    - DELETE : 삭제
    """

    SESSION_KEY = "my_note_cart"

    def get(self, request):
        cart = request.session.get(self.SESSION_KEY, [])
        return Response({"data": cart}, status=status.HTTP_200_OK)

    def post(self, request):
        perfume_id = request.data.get("perfume_id")
        brand = request.data.get("brand")
        perfume_img_url = request.data.get("perfume_img_url")
        smelling_rate = request.data.get("smelling_rate")

        if not perfume_id or smelling_rate is None:
            return Response(
                {"error": "perfume_id와 smelling_rate는 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart = request.session.get(self.SESSION_KEY, [])

        # 이미 있으면 점수 업데이트
        for item in cart:
            if item["perfume_id"] == perfume_id:
                item["smelling_rate"] = smelling_rate
                request.session[self.SESSION_KEY] = cart
                request.session.modified = True
                return Response({"data": cart}, status=status.HTTP_200_OK)

        # 새로 추가
        cart.append({
            "perfume_id": perfume_id,
            "perfume_name": request.data.get("perfume_name"),  # ⭐ 추가
            "brand": brand,
            "perfume_img_url": perfume_img_url,
            "smelling_rate": smelling_rate
        })

        request.session[self.SESSION_KEY] = cart
        request.session.modified = True

        return Response({"data": cart}, status=status.HTTP_200_OK)

    def delete(self, request):
        perfume_id = request.data.get("perfume_id")

        cart = request.session.get(self.SESSION_KEY, [])
        cart = [p for p in cart if p["perfume_id"] != perfume_id]

        request.session[self.SESSION_KEY] = cart
        request.session.modified = True

        return Response({"data": cart}, status=status.HTTP_200_OK)


class MyNotePerfumeSearchAPIView(APIView):
    """
    4-2 향수 검색 API
    - name / brand 기준 검색
    """

    def get(self, request):
        raw_query = request.GET.get("q", "").strip()
        query = raw_query.replace(" ", "").replace("-", "")

        if not query:
            return Response([], status=200)

        perfumes = Perfume.objects.filter(
            Q(perfume_name__icontains=raw_query) |
            Q(brand__icontains=raw_query) |
            Q(brand__icontains=query)
        )[:20]

        result = []
        for p in perfumes:
            result.append({
                "perfume_id": p.perfume_id,
                "name": p.perfume_name,
                "brand": p.brand,
                # 이미지: 기존 api_views 방식 그대로
                "perfume_img_url": f"{settings.STATIC_URL}ui/perfume_images/{p.perfume_id}.jpg"
            })

        return Response(result, status=200)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import UserSmellingInput


class MyNotePerfumeCompleteAPIView(APIView):
    def _get_next_smelling_user_id(self):
        last = UserSmellingInput.objects.order_by("-smelling_user_id").first()
        return last.smelling_user_id + 1 if last and last.smelling_user_id else 1

    def post(self, request):
        print("🔥 my_note_style =", request.session.get("my_note_style"))
        perfumes = request.session.get("my_note_cart", [])
        style = request.session.get("my_note_style")

        if not perfumes:
            return Response(
                {"error": "최소 한 개의 향수를 저장해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not style:
            return Response(
                {"error": "스타일 정보가 없습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        smelling_user_id = self._get_next_smelling_user_id()

        for p in perfumes:
            obj = UserSmellingInput(
                smelling_user_id=smelling_user_id,
                season=style.get("season"),
                perfume_id_id=p["perfume_id"],
                brand=p.get("brand"),
                perfume_img_url=p.get("perfume_img_url"),
                smelling_rate=p.get("smelling_rate"),
            )

            # 원피스
            if style["style_type"] == "dress":
                dress = style.get("dress")
                if dress:
                    obj.dress_id_id = dress.get("id")
                    obj.dress_color = dress.get("color")
                    obj.dress_img = dress.get("img")

            # 상의 + 하의
            else:
                top = style.get("top")
                bottom = style.get("bottom")

                if top:
                    obj.top_id_id = top.get("id")
                    obj.top_color = top.get("color")
                    obj.top_category = top.get("category")
                    obj.top_img = top.get("img")

                if bottom:
                    obj.bottom_id_id = bottom.get("id")
                    obj.bottom_color = bottom.get("color")
                    obj.bottom_category = bottom.get("category")
                    obj.bottom_img = bottom.get("img")

            # 반드시 for문 안
            obj.save()

        # 세션 정리
        request.session.pop("my_note_cart", None)
        request.session.pop("my_note_style", None)

        return Response({"message": "MyNote 저장 완료"}, status=200)


class MyNoteFilterImagesAPIView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        category_en = request.query_params.get('category')
        item_en = request.query_params.get('item')
        color_en = request.query_params.get('color')

        if not (category_en and item_en and color_en):
            return Response({'images': []})

        map_category = {'top': '상의', 'bottom': '하의', 'onepiece': '원피스'}
        map_item = {
            'blouse': '블라우스', 'tshirt': '티셔츠', 'knit': '니트웨어', 'shirt': '셔츠', 'hoodie': '후드티',
            'pants': '팬츠', 'jeans': '청바지', 'skirt': '스커트', 'leggings': '레깅스',
            'dress': '드레스', 'jumpsuit': '점프수트'
        }
        map_color = {
            'white': '화이트', 'black': '블랙', 'grey': '그레이', 'navy': '네이비', 'beige': '베이지',
            'pink': '핑크', 'skyblue': '스카이블루', 'brown': '브라운', 'red': '레드',
            'green': '그린', 'gold': '골드', 'silver': '실버'
        }

        # 한글 정규화 필수 적용
        cat_kr = unicodedata.normalize('NFC', map_category.get(category_en, ''))
        item_kr = unicodedata.normalize('NFC', map_item.get(item_en, ''))
        color_kr = unicodedata.normalize('NFC', map_color.get(color_en, ''))

        if not (cat_kr and item_kr and color_kr):
            return Response({'images': []})

        # S3 경로 설정
        s3_folder_path = f"ui/clothes/{cat_kr}/{item_kr}/{color_kr}/"
        images = []

        try:
            # [수정] S3에서 파일 목록 가져오기
            _, files = staticfiles_storage.listdir(s3_folder_path)

            for file in files:
                if not file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    continue

                name = os.path.splitext(file)[0]
                parts = name.split("_")

                # 파일명 규칙: 스타일_식별자_상의 (기존 로직 유지)
                if len(parts) < 3: continue
                try:
                    cloth_id = int(parts[1])
                except ValueError:
                    continue

                encoded_cat, encoded_item, encoded_color, encoded_file = quote(cat_kr), quote(item_kr), quote(
                    color_kr), quote(file)

                # [수정] STATIC_URL 적용
                url_path = f"{settings.STATIC_URL}ui/clothes/{encoded_cat}/{encoded_item}/{encoded_color}/{encoded_file}"

                images.append({
                    "id": cloth_id,
                    "img": url_path,
                    "category": category_en,
                    "item": item_en,
                    "color": color_en,
                })
        except Exception as e:
            print(f"❌ MyNote S3 Error: {e}")

        images = random.sample(images, min(len(images), 4))
        while len(images) < 4: images.append(None)
        return Response({'images': images})

class SomeoneSummaryAPIView(APIView):
    """
    For Someone 전용 요약 API
    """
    renderer_classes = [JSONRenderer]

    def get(self, request):
        last_user = UserInfo.objects.last()
        if not last_user:
            return Response({"summary": "데이터가 없습니다."}, status=404)

        # 세션에서 선물 정보 꺼내기
        recipient = request.session.get('recipient') or "소중한 분"
        situation = request.session.get('situation') or "특별한 날"

        try:
            # For Someone 전용 로직 호출
            summary_text = get_someone_recommendation(
                last_user.user_id,
                recipient,
                situation
            )
            return Response({"summary": summary_text}, status=200)
        except Exception as e:
            return Response({"summary": "분석 중 오류가 발생했습니다."}, status=500)


class GiftMessageAPIView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        last_user = UserInfo.objects.last()
        if not last_user:
            return Response({"messages": ["데이터가 없습니다."]}, status=404)

        # 1. 세션에서 선물 정보 가져오기
        recipient = request.session.get('recipient') or "소중한 분"
        situation = request.session.get('situation') or "특별한 날"

        # 2. 쿼리 파라미터에서 메시지 타입 가져오기
        msg_type = request.query_params.get('type', '짧은')

        try:
            from .recommend.gift_message_LLM import get_someone_gift_message

            # [핵심 수정] last_user.user_id를 첫 번째 인자로 전달합니다.
            messages = get_someone_gift_message(
                last_user.user_id,
                recipient,
                situation,
                msg_type
            )

            return Response({"messages": messages}, status=200)
        except Exception as e:
            import traceback
            traceback.print_exc()  # 터미널에 상세 에러 출력
            return Response({"messages": ["마음을 담아 선물하세요."]}, status=500)