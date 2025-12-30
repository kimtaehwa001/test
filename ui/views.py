
from django.shortcuts import render
from .models import UserSmellingInput
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from ui.recommend.weight_cal import find_best_weights
from ui.models import Weight

# ==========================================
# 화면 렌더링 Views (HTML 페이지 연결)
# ==========================================

def home(request):
    return render(request, 'ui/home.html')

def for_me(request):
    return render(request, 'ui/for_me.html')

def for_someone(request):
    return render(request, 'ui/for_someone.html')

def result(request):
    return render(request, 'ui/result.html')

def result_someone(request):
    return render(request, 'ui/result_someone.html')

def my_note_style(request):
    request.session.pop("my_note_style", None)
    request.session.pop("my_note_perfumes", None)

    return render(request, "ui/my_note_style.html")


def my_note_perfume(request):
    return render(request, "ui/my_note_perfume.html")

def my_note_result(request):
    # =========================
    # 1. 가장 최근 smelling_user_id
    # =========================
    last_row = (
        UserSmellingInput.objects
        .order_by("-smelling_user_id")
        .first()
    )

    if not last_row:
        # 아직 저장된 MyNote가 없는 경우
        return render(request, "ui/my_note_result.html", {
            "onepiece_img": None,
            "top_img": None,
            "bottom_img": None,
            "mynote_list": [],
        })

    smelling_user_id = last_row.smelling_user_id

    # =========================
    # 2. 같은 MyNote 묶음 전체
    # =========================
    rows = UserSmellingInput.objects.filter(
        smelling_user_id=smelling_user_id
    )

    # =========================
    # 3. 스타일 이미지
    # =========================
    onepiece_img = None
    top_img = None
    bottom_img = None

    style_row = rows.first()

    if style_row.dress_img:
        onepiece_img = style_row.dress_img
    else:
        top_img = style_row.top_img
        bottom_img = style_row.bottom_img

    # =========================
    # 4. 향수 리스트
    # =========================
    mynote_list = []
    for r in rows:
        mynote_list.append({
            "image_url": r.perfume_img_url,
            "name": r.perfume_id.perfume_name if r.perfume_id else "",
            "brand": r.brand,
            "score": r.smelling_rate,
        })

    context = {
        "onepiece_img": onepiece_img,
        "top_img": top_img,
        "bottom_img": bottom_img,
        "mynote_list": mynote_list,
    }

    return render(request, "ui/my_note_result.html", context)

@require_POST
def complete_and_update_weight(request):
    w_style, w_color, w_season = find_best_weights()

    Weight.objects.create(
        style_weight=w_style,
        color_weight=w_color,
        season_weight=w_season,
    )

    return redirect("home")
