import os
import random
from urllib.parse import quote

from django.db import transaction
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.safestring import mark_safe

# DRF 관련 임포트
from rest_framework.views import APIView
from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer

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
    UserInputSerializer,
    RecommendationResultSerializer
)

# 추천 엔진 및 LLM
from .recommend.calculation_v3 import myscore_cal
from .recommend.ver2_LLM import get_llm_recommendation


# =============================================================
# 1. 이미지 데이터 조회 API (S3 대응 완료)
# =============================================================
class FilterImagesAPI(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        category_en = request.query_params.get('category')
        item_en = request.query_params.get('item')
        color_en = request.query_params.get('color')

        if not (category_en and item_en and color_en):
            return Response({'images': [None, None, None, None]})

        # 영한 매핑
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

        # [수정 포인트] 한글 자모 분리 방지를 위해 NFC 정규화 적용
        cat_kr = unicodedata.normalize('NFC', map_category.get(category_en, ''))
        item_kr = unicodedata.normalize('NFC', map_item.get(item_en, ''))
        color_kr = unicodedata.normalize('NFC', map_color.get(color_en, ''))

        if not (cat_kr and item_kr and color_kr):
            return Response({'images': [None, None, None, None]})

        # S3 내부 경로
        s3_folder_path = f"ui/clothes/{cat_kr}/{item_kr}/{color_kr}/"
        valid_images = []

        try:
            print(f"🔍 S3 listdir 시도 중 : {s3_folder_path}")
            # settings.py의 location('static') 이후의 경로를 뒤집니다.
            _, files = default_storage.listdir(s3_folder_path)
            print(f"✅ S3에서 찾은 파일 개수 : {len(files)}")

            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    # URL에 들어갈 한글 인코딩
                    # S3 객체 경로 자체는 정규화된 한글이어야 합니다.
                    url_path = f"{settings.STATIC_URL}ui/clothes/{quote(cat_kr)}/{quote(item_kr)}/{quote(color_kr)}/{quote(file)}"
                    valid_images.append(url_path)
        except Exception as e:
            print(f"❌ S3 Path Error: {e}")

        selected_images = random.sample(valid_images, min(len(valid_images), 4)) if valid_images else []
        while len(selected_images) < 4:
            selected_images.append(None)

        return Response({'images': selected_images})


# =============================================================
# 2. 최근 선택한 코디 이미지 경로 API
# =============================================================
class UserOutfitAPIView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        last_user = UserInfo.objects.last()
        if not last_user:
            return Response({"error": "데이터가 없습니다."}, status=404)

        # 필드명을 dress_img로 수정
        data = {
            "top_img": f"{settings.STATIC_URL}{last_user.top_img}" if last_user.top_img else None,
            "bottom_img": f"{settings.STATIC_URL}{last_user.bottom_img}" if last_user.bottom_img else None,
            "onepiece_img": f"{settings.STATIC_URL}{last_user.dress_img}" if last_user.dress_img else None,
        }
        return Response(data, status=200)

# =============================================================
# 3. 추천 결과 상세 조회 API
# =============================================================
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

        response_data = {
            "user_outfit": {
                "top_img": f"{settings.STATIC_URL}{last_user.top_img}" if last_user and last_user.top_img else None,
                "bottom_img": f"{settings.STATIC_URL}{last_user.bottom_img}" if last_user and last_user.bottom_img else None,
                "onepiece_img": f"{settings.STATIC_URL}{last_user.dress_img}" if last_user and last_user.dress_img else None,
            },
            "perfumes": perfumes_data
        }
        return Response(response_data, status=200)


# =============================================================
# 4. 향수 Top3 이미지 및 정보 API
# =============================================================
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


# 나머지 ViewSet (CRUD 용)
class PerfumeViewSet(viewsets.ModelViewSet):
    queryset = Perfume.objects.all().order_by('perfume_id')
    serializer_class = PerfumeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['brand', 'perfume_name']


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


# 추천 요청 처리 뷰
class UserInputView(APIView):
    def post(self, request):
        serializer = UserInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        try:
            map_item = {
                'blouse': '블라우스', 'tshirt': '티셔츠', 'knit': '니트웨어', 'shirt': '셔츠', 'sleeveless': '탑',
                'hoodie': '후드티', 'sweatshirt': '맨투맨', 'bratop': '브라탑',
                'pants': '팬츠', 'jeans': '청바지', 'skirt': '스커트', 'long_skirt': '롱스커트', 'leggings': '레깅스',
                'jogger': '트레이닝', 'slacks': '슬랙스', 'dress': '드레스', 'onepiece': '원피스', 'jumpsuit': '점프수트'
            }
            map_color = {
                'white': '화이트', 'black': '블랙', 'beige': '베이지', 'pink': '핑크',
                'skyblue': '스카이블루', 'grey': '그레이', 'brown': '브라운', 'navy': '네이비',
                'red': '레드', 'yellow': '옐로우', 'blue': '블루', 'lavender': '라벤더',
                'wine': '와인', 'silver': '실버', 'orange': '오렌지', 'khaki': '카키',
                'green': '그린', 'purple': '퍼플', 'mint': '민트', 'gold': '골드', 'neon': '네온',
            }

            with transaction.atomic():
                user_top_obj = None
                user_bottom_obj = None
                user_dress_obj = None

                if data.get('top') and data.get('bottom'):
                    top_color_obj = ClothesColor.objects.get(color=map_color.get(data.get('top_color')))
                    bottom_color_obj = ClothesColor.objects.get(color=map_color.get(data.get('bottom_color')))
                    user_top_obj = TopBottom.objects.filter(top_category=map_item.get(data['top']),
                                                            top_color=top_color_obj).first()
                    user_bottom_obj = TopBottom.objects.filter(bottom_category=map_item.get(data['bottom']),
                                                               bottom_color=bottom_color_obj).first()
                elif data.get('onepiece'):
                    dress_color_obj = ClothesColor.objects.get(color=map_color.get(data.get('onepiece_color')))
                    user_dress_obj = Dress.objects.filter(dress_color=dress_color_obj).first()

                new_user_info = UserInfo.objects.create(
                    season=data['season'],
                    disliked_accord=", ".join(data.get('disliked_accords', [])) if data.get(
                        'disliked_accords') else None,
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

                top3_scores = myscore_cal(new_user_info.user_id)
                Score.objects.filter(user=new_user_info).delete()
                for s in top3_scores: s.save()

            return Response({"message": "추천 완료", "user_id": new_user_info.user_id}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class RecommendationSummaryAPIView(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        try:
            target_user_id = UserInfo.objects.last().user_id
            summary_text = get_llm_recommendation(target_user_id)
            return Response({"summary": summary_text}, status=200)
        except Exception as e:
            return Response({"summary": "분석 중 오류 발생"}, status=500)

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