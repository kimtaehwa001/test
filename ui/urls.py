from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ScoreView

from . import views         # 화면용
from . import api_views     # API용
from .api_views import FilterImagesAPI, UserInputView, RecommendationResultAPIView, RecommendationSummaryAPIView

# ==========================================
# 1. DRF 라우터 설정 (api_views 사용)
# ==========================================
router = DefaultRouter()
router.register(r'colors/clothes', api_views.ClothesColorViewSet)
router.register(r'colors/perfume', api_views.PerfumeColorViewSet)
router.register(r'clothes/topbottom', api_views.TopBottomViewSet)
router.register(r'clothes/dress', api_views.DressViewSet)
router.register(r'perfumes', api_views.PerfumeViewSet)
router.register(r'season', api_views.PerfumeSeasonViewSet)
router.register(r'classification', api_views.PerfumeClassificationViewSet)


urlpatterns = [
    # ==========================================
    # 2. 화면 페이지 (views 사용)
    # ==========================================
    path('', views.home, name='home'),
    path('for-me/', views.for_me, name='for_me'),
    path('for-someone/', views.for_someone, name='for_someone'),
    path('result/', views.result, name='result'),
    path('result/someone/', views.result_someone, name='result_someone'),
    path('api/user-input/', UserInputView.as_view(), name='user-input'),
    path('api/score/', ScoreView.as_view(), name='recommendation'),
    path('api/filter-images/', FilterImagesAPI.as_view(), name='filter-images'),
    path('api/user-outfit/', api_views.UserOutfitAPIView.as_view(), name='user-outfit'),
    path('api/perfume-top3-images/', api_views.PerfumeTop3ImageAPI.as_view(), name='perfume-top3-images'),
    path('api/recommendation-results/', api_views.RecommendationResultAPIView.as_view(), name='recommendation-results'),
    path('api/recommendation-summary/', api_views.RecommendationSummaryAPIView.as_view(),  name='recommendation-summary'),

    # ==========================================
    # 4. 데이터 API 라우터 연결
    # ==========================================
    path('api/', include(router.urls)),
]