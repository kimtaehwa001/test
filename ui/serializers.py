
from rest_framework import serializers
from .models import TopBottom, Dress, ClothesColor, PerfumeColor, Perfume, PerfumeSeason, PerfumeClassification, UserInfo, Score


# ==========================================
# 1. 데이터 관리용 Serializers
# ==========================================

# 1. 옷 색상
class ClothesColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothesColor
        fields = '__all__'


# 2. 향수 컬러(향조)
class PerfumeColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfumeColor
        fields = '__all__'


# 3. 상의 & 하의
class TopBottomSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopBottom
        fields = '__all__'


# 4. 원피스
class DressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dress
        fields = '__all__'

# 5. 향수
class PerfumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfume
        fields = '__all__'

# 6. 계절
class PerfumeSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfumeSeason
        fields = '__all__'

#7. 향수 분류 정보

class PerfumeClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfumeClassification
        fields = '__all__'


class UserInputSerializer(serializers.Serializer):
    """
    프론트엔드에서 보내주는 JSON 데이터를 검증합니다.
    이미지 경로(top_img, bottom_img, onepiece_img) 필드를 추가했습니다.
    """
    # 공통 정보
    season = serializers.CharField(required=True)
    disliked_accords = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )

    # 1. 상의 정보
    top = serializers.CharField(required=False, allow_null=True)
    top_color = serializers.CharField(required=False, allow_null=True)
    top_img = serializers.CharField(required=False, allow_null=True)

    # 2. 하의 정보
    bottom = serializers.CharField(required=False, allow_null=True)
    bottom_color = serializers.CharField(required=False, allow_null=True)
    bottom_img = serializers.CharField(required=False, allow_null=True)

    # 3. 원피스 정보
    onepiece = serializers.CharField(required=False, allow_null=True)
    onepiece_color = serializers.CharField(required=False, allow_null=True)
    onepiece_img = serializers.CharField(required=False, allow_null=True)

    # for_someone 전용
    recipient = serializers.CharField(required=False, allow_null=True)
    situation = serializers.CharField(required=False, allow_null=True)

    def validate(self, data):
        """
        코디 정보(상의+하의 또는 원피스) 중 하나는 반드시 완성되어야 함을 검증합니다.
        """
        top = data.get("top")
        bottom = data.get("bottom")
        onepiece = data.get("onepiece")
        season = data.get("season")

        if not season:
            raise serializers.ValidationError("계절은 필수 항목입니다.")

        # 투피스 조합 확인 (아이템과 색상이 모두 있어야 함)
        has_2pc = top and data.get("top_color") and bottom and data.get("bottom_color")
        # 원피스 조합 확인
        has_1pc = onepiece and data.get("onepiece_color")

        if not (has_2pc or has_1pc):
            raise serializers.ValidationError("코디 정보(상의+하의 또는 원피스)를 모두 선택해야 합니다.")

        return data


# ==========================================
# 3. 추천 결과 응답용 Serializer (기존 복원)
# ==========================================

class RecommendationResultSerializer(serializers.ModelSerializer):
    perfume_name = serializers.ReadOnlyField(source='perfume.perfume_name')
    brand = serializers.ReadOnlyField(source='perfume.brand')
    gender = serializers.ReadOnlyField(source='perfume.gender')

    myscore = serializers.SerializerMethodField()
    top_season = serializers.SerializerMethodField()
    accords = serializers.SerializerMethodField()

    class Meta:
        model = Score
        fields = [
            'perfume_id', 'perfume_name', 'brand', 'gender',
            'myscore', 'top_season', 'accords'
        ]

    def get_myscore(self, obj):
        # 소수점 첫째 자리까지 반올림 (예: 141.7)
        return round(float(obj.myscore), 3)

    def get_top_season(self, obj):
        try:
            season = obj.perfume.season
            season_data = {
                "Spring": season.spring, "Summer": season.summer,
                "Fall": season.fall, "Winter": season.winter
            }
            max_season = max(season_data, key=season_data.get)
            return max_season
        except:
            return None

    def get_accords(self, obj):
        p = obj.perfume
        accords = []
        if p.mainaccord1: accords.append(p.mainaccord1.mainaccord)
        if p.mainaccord2: accords.append(p.mainaccord2.mainaccord)
        if p.mainaccord3: accords.append(p.mainaccord3.mainaccord)
        return accords
