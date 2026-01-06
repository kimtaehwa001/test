import os
from openai import OpenAI
from dotenv import load_dotenv
from ui.models import UserInfo, Score, Perfume, PerfumeClassification, PerfumeSeason

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_someone_recommendation(user_id, recipient, situation):
    """
    UserInfo에서 스타일 정보를 가져오고, 세션에서 넘겨받은 선물 정보를 조합하여
    선물 전용 LLM 추천 사유를 생성합니다.
    """
    try:
        # 1. DB에서 데이터 가져오기
        user = UserInfo.objects.get(user_id=user_id)
        top3_scores = Score.objects.filter(user=user).select_related('perfume').order_by('-myscore')[:3]

        if not top3_scores:
            return "추천 데이터가 부족하여 분석 결과를 생성할 수 없습니다."

        # 2. 사용자(선물 대상자) 컨텍스트 생성
        user_style_text = []
        if user.top_color: user_style_text.append(f"상의는 {user.top_color} {user.top_category or ''}")
        if user.bottom_color: user_style_text.append(f"하의는 {user.bottom_color} {user.bottom_category or ''}")
        if user.dress_color: user_style_text.append(f"원피스는 {user.dress_color}")
        user_style_summary = ", ".join(user_style_text)

        # 3. 추천 향수 3개의 상세 데이터 생성 (기존 로직 유지 + 빈값 처리)
        perfumes_for_llm = []
        for s in top3_scores:
            p = s.perfume

            # 향 설명 추출
            frag_desc = ""
            try:
                classif = PerfumeClassification.objects.get(perfume=p)
                if classif.fragrance: frag_desc = classif.fragrance
            except:
                pass

            # 계절 정보 추출 (상위 2개)
            season_desc = ""
            try:
                ps = PerfumeSeason.objects.get(perfume=p)
                s_data = {"봄": ps.spring, "여름": ps.summer, "가을": ps.fall, "겨울": ps.winter}
                top_seasons = sorted(s_data.items(), key=lambda x: x[1], reverse=True)[:2]
                season_desc = ", ".join([ts[0] for ts in top_seasons])
            except:
                pass

            perfumes_for_llm.append({
                "perfume_name": p.perfume_name,
                "brand": p.brand,
                "perfume_mainaccords": f"{p.mainaccord1}, {p.mainaccord2}, {p.mainaccord3}",
                "fragrance_desc": frag_desc,
                "best_seasons": season_desc
            })

        # 4. LLM 실행 (선물용 프롬프트 적용)
        return generate_someone_summary(
            user_style=f"전체적으로 {user_style_summary}의 스타일",
            user_season=user.season,
            perfumes=perfumes_for_llm,
            recipient=recipient,
            situation=situation
        )

    except Exception as e:
        return f"분석 중 오류 발생: {str(e)}"


def generate_someone_summary(user_style: str, user_season: str, perfumes: list, recipient: str, situation: str):
    """
    기존 generate_top3_recommend_summary의 형식을 유지하되,
    선물 대상과 상황에 초점을 맞춰 작성합니다.
    """
    # 시스템 프롬프트 (구조는 유지하되 역할만 선물 큐레이터로 변경)
    system_prompt = f"""
    너는 향수 추천 서비스에서 종합 추천 이유를 작성하는 에디터다.
    단순한 추천을 넘어, 선물하는 이의 마음이 전달되도록 '{recipient}'님과 '{situation}'이라는 상황의 특수성을 문장에 녹여낸다.

    다음 구조를 반드시 지켜서 작성한다.
    1. 총 3개의 문단으로만 작성한다.
    2. 각 문단은 한 문장으로만 작성한다.
    3. 문단 사이에는 줄바꿈을 정확히 한 번만 사용한다.
    4. 전체 분량은 반드시 150~200자 이내여야 한다.

    - 1문단:
      {recipient}에게 {situation}이 갖는 의미를 짧게 언급하며,
      이 향수들이 왜 그 순간에 어울리는 선물인지 감정 중심으로 요약한다.
      설명은 하나의 핵심 감정만 사용한다.

    - 2문단:
      style / color / season 관점이 모두 포함되어야 하며,
      서술 순서는 style → color → season으로 고정한다.
      색감 설명은 아래 규칙을 따른다.

      (필수 색감 서술 규칙)
      A) 사용자 착장의 색감을 간결하게 묘사한다.
         - 밝기, 채도, 온도감, 대비 중 최대 2가지만 사용한다.
      B) 그 색감이 향수의 분위기와 어떻게 이어지는지만 설명한다.
      C) 어울리는 장면은 한 번만 짧게 덧붙인다.

      불필요한 수식어를 사용하지 않는다.

    - 3문단:
      세 향수가 {recipient}의 서로 다른 면모를 어떻게 드러내는지 간단히 대비한다.
      선택을 돕는 방향 제시만 하고 설명은 덧붙이지 않는다.

    추가 규칙:
    - 점수, 수치, 순위 언급 금지
    - 광고성·과장 표현 금지
    - '~인 것 같다'와 같은 추측 표현 금지
    - 단어 중간 줄바꿈 금지
    """

    # 향수 블록 생성 (데이터가 있는 항목만 포함)
    perfume_block = ""
    for p in perfumes:
        perfume_block += f"- {p['perfume_name']} ({p['brand']})\n"
        perfume_block += f"  · 주요 향조: {p['perfume_mainaccords']}\n"
        if p['fragrance_desc']: perfume_block += f"  · 향의 결: {p['fragrance_desc']}\n"
        if p['best_seasons']: perfume_block += f"  · 추천 계절: {p['best_seasons']}\n"
        perfume_block += "\n"

    # 유저 프롬프트 (대상과 상황 정보 추가)
    user_prompt = f"""
    아래 정보를 바탕으로 {recipient}님에게 줄 {situation} 선물 추천 사유를 작성하라.

    [작성 조건]
    - 전체 분량 150~200자
    - 3문단, 각 문단 1문장
    - 공통 추천 이유 중심
    - 마지막 문단은 분위기 차이 요약만 수행
    - 광고 문구, 과장 표현 사용 금지

    [선물 정보]
    - 선물 대상: {recipient}
    - 선물 상황: {situation}

    [대상자 정보]
    - 스타일: {user_style}
    - 사용 계절: {user_season}

    [추천 향수 요약]
    {perfume_block}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.6,
        max_tokens=600
    )
    return response.choices[0].message.content