
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ScoreView

from . import views         # 화면용
from . import api_views     # API용
from .api_views import FilterImagesAPI, UserInputView, RecommendationResultAPIView, RecommendationSummaryAPIView, MyNoteStyleAPIView, MyNotePerfumeCartAPIView, MyNotePerfumeSearchAPIView, MyNotePerfumeCompleteAPIView, MyNoteFilterImagesAPIView, SomeoneSummaryAPIView, GiftMessageAPIView

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
    # My Note
    path('my-note/style/', views.my_note_style, name='my_note_style'),
    path('my-note/perfume/', views.my_note_perfume, name='my_note_perfume'),
    path('my-note/result/', views.my_note_result, name='my_note_result'),

    path('api/user-input/', UserInputView.as_view(), name='user-input'),
    path('api/score/', ScoreView.as_view(), name='recommendation'),
    path('api/filter-images/', FilterImagesAPI.as_view(), name='filter-images'),
    path('api/user-outfit/', api_views.UserOutfitAPIView.as_view(), name='user-outfit'),
    path('api/perfume-top3-images/', api_views.PerfumeTop3ImageAPI.as_view(), name='perfume-top3-images'),
    path('api/recommendation-results/', api_views.RecommendationResultAPIView.as_view(), name='recommendation-results'),
    path('api/recommendation-summary/', api_views.RecommendationSummaryAPIView.as_view(),  name='recommendation-summary'),
    path('api/my-note/style/', MyNoteStyleAPIView.as_view(), name='my-note-style'),
    path('api/my-note/perfume/cart/', api_views.MyNotePerfumeCartAPIView.as_view()),
    path('api/my-note/perfume/search/', api_views.MyNotePerfumeSearchAPIView.as_view()),
    path("api/my-note/perfume/complete/", MyNotePerfumeCompleteAPIView.as_view()),
    path('api/someone-summary/', SomeoneSummaryAPIView.as_view(), name='someone-summary'),
    path('api/gift-message/', GiftMessageAPIView.as_view(), name='gift-message'),
    path("my-note/result/", views.my_note_result, name="my_note_result"),
    path("api/my-note/filter-images/", api_views.MyNoteFilterImagesAPIView.as_view()),

    # ==========================================
    # 4. 데이터 API 라우터 연결
    # ==========================================
    path('api/', include(router.urls)),

    path("complete/", views.complete_and_update_weight, name="complete"),
]
