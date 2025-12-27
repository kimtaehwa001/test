from django.contrib import admin
from .models import (
    ClothesColor, PerfumeColor, TopBottom, Dress, UserInfo,
    Perfume, PerfumeSeason, PerfumeClassification, Score
)


# ==========================================
# 1. 색상 관리
# ==========================================
@admin.register(ClothesColor)
class ClothesColorAdmin(admin.ModelAdmin):
    list_display = ('color', 'rgb_tuple')
    search_fields = ('color',)


@admin.register(PerfumeColor)
class PerfumeColorAdmin(admin.ModelAdmin):
    list_display = ('mainaccord', 'color')
    search_fields = ('mainaccord',)


# ==========================================
# 2. 옷 데이터 관리
# ==========================================
@admin.register(TopBottom)
class TopBottomAdmin(admin.ModelAdmin):
    # 모든 필드를 리스트에 보여줍니다.
    list_display = [field.name for field in TopBottom._meta.fields]

    # 필터링 및 검색
    list_filter = ('top_category', 'bottom_category', 'style')
    search_fields = ('id', 'style', 'sub_style')
    list_per_page = 20

    # [최적화] 색상 데이터가 많을 경우 드롭박스 대신 팝업 검색창을 사용하게 합니다.
    raw_id_fields = ('top_color', 'bottom_color')


@admin.register(Dress)
class DressAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Dress._meta.fields]

    list_filter = ('style', 'dress_length')
    search_fields = ('id', 'style', 'dress_detail')

    # [최적화] 마찬가지로 색상 선택 시 팝업 검색창 사용
    raw_id_fields = ('dress_color',)


# ==========================================
# 3. 사용자 정보 관리
# ==========================================
@admin.register(UserInfo)
class UserInfoAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'season', 'top_id', 'bottom_id', 'dress_id')
    list_filter = ('season',)
    # 옷 정보는 ID로 직접 연결되므로 검색하기 쉽게 설정
    raw_id_fields = ('top_id', 'bottom_id', 'dress_id')


# ==========================================
# 4. 향수 데이터 관리 (여기가 핵심!)
# ==========================================

# [편의성] 향수 상세 페이지 들어갔을 때, 시즌/분류/점수도 한 화면에서 수정 가능하게 함
class PerfumeSeasonInline(admin.StackedInline):
    model = PerfumeSeason
    can_delete = False
    verbose_name_plural = '계절별 점수'


class PerfumeClassificationInline(admin.StackedInline):
    model = PerfumeClassification
    can_delete = False
    verbose_name_plural = '향수 분류'


class ScoreInline(admin.StackedInline):
    model = Score
    can_delete = False
    verbose_name_plural = '종합 점수'


@admin.register(Perfume)
class PerfumeAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Perfume._meta.fields]
    list_filter = ('brand', 'gender')
    search_fields = ('perfume_name', 'brand')
    list_display_links = ('perfume_name',)

    # [최적화] FK(향조)가 많으므로, DB를 미리 긁어와서 속도 저하 방지
    list_select_related = (
        'mainaccord1', 'mainaccord2', 'mainaccord3', 'mainaccord4', 'mainaccord5'
    )

    # [편의성] 향조 선택할 때 드롭박스가 너무 길어지지 않게 팝업 검색 사용
    raw_id_fields = (
        'mainaccord1', 'mainaccord2', 'mainaccord3', 'mainaccord4', 'mainaccord5'
    )

    # [편의성] 위에 만든 Inline 클래스를 연결 -> 향수 수정 화면에서 시즌/점수도 같이 수정 가능
    inlines = [PerfumeSeasonInline, PerfumeClassificationInline, ScoreInline]


# ==========================================
# 5. 향수 부가 정보 (개별 관리용)
# ==========================================


@admin.register(PerfumeSeason)
class PerfumeSeasonAdmin(admin.ModelAdmin):
    list_display = ('perfume', 'spring', 'summer', 'fall', 'winter')
    search_fields = ('perfume__perfume_name',)
    # 향수 이름이 바로 보이도록 설정
    autocomplete_fields = ['perfume']


@admin.register(PerfumeClassification)
class PerfumeClassificationAdmin(admin.ModelAdmin):
    list_display = ('perfume', 'fragrance')
    search_fields = ('perfume__perfume_name', 'fragrance')
    autocomplete_fields = ['perfume']


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('perfume', 'myscore', 'season_score', 'color_score', 'style_score')
    search_fields = ('perfume__perfume_name',)
    autocomplete_fields = ['perfume']