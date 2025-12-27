# import pandas as pd
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
#
# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#
# # 데이터 로드
# score_df = pd.read_csv("data/03_results/recommendation/score.csv")
# user_df = pd.read_csv("data/03_results/clothes/user_info.csv")
# perfume_df = pd.read_csv("data/03_results/perfume/perfume.csv")
# perfume_classification = pd.read_csv("data/03_results/perfume/perfume_classification.csv")
# perfume_color = pd.read_csv("data/03_results/perfume/perfume_color.csv")
# perfume_season = pd.read_csv("data/03_results/perfume/perfume_season.csv")
#
#
# ###사용자 id 가정
# user_id = 1
#
# # 추천 향수 3개의 LLM 입력 데이터 생성
# ## A) 사용자
# def build_user_context(user_df: pd.DataFrame, user_id):
#     user = user_df[user_df["사용자_식별자"] == user_id].iloc[0]
#
#     user_style_text = []
#     if pd.notna(user["상의_색상"]):
#         user_style_text.append(f"상의는 {user['상의_색상']} 계열")
#     if pd.notna(user["하의_색상"]):
#         user_style_text.append(f"하의는 {user['하의_색상']} 계열")
#     if pd.notna(user["원피스_색상"]):
#         user_style_text.append(f"원피스는 {user['원피스_색상']} 계열")
#
#     user_style_summary = ", ".join(user_style_text)
#
#     return {
#         "user_season": user["계절"],
#         "user_style": f"전체적으로 {user_style_summary}의 차분하고 부드러운 스타일",
#         "disliked_accords": user["비선호_향조"]
#     }
#
#
# ## B) 향수
# def build_perfume_context(
#     score_row,
#     perfume_df,
#     perfume_classification,
#     perfume_color,
#     perfume_season,
#     user_context
# ):
#     perfume_id = score_row["perfume_id"]
#
#     perfume = perfume_df[perfume_df["perfume_id"] == perfume_id].iloc[0]
#     accords = perfume_classification[perfume_classification["perfume_id"] == perfume_id].iloc[0]
#     season_info = perfume_season[perfume_season["perfume_id"] == perfume_id].iloc[0]
#
#     # 1) 향 결 설명 (사람 언어)
#     fragrance_desc = accords["fragrance"]
#
#     # 2) 계절 적합도 상위 2개 추출
#     season_scores = {
#         "봄": season_info["spring"],
#         "여름": season_info["summer"],
#         "가을": season_info["fall"],
#         "겨울": season_info["winter"],
#     }
#
#     top_seasons = sorted(
#         season_scores.items(),
#         key=lambda x: x[1],
#         reverse=True
#     )[:2]
#
#     season_desc = ", ".join([s[0] for s in top_seasons])
#
#     return {
#         "perfume_name": perfume["Perfume"],
#         "brand": perfume["Brand"],
#
#         "my_score": score_row["myscore"],
#         "color_score": score_row["color_score"],
#         "season_score": score_row["season_score"],
#
#         "user_style": score_row["user_style"],
#         "user_season": user_context["user_season"],
#
#         "fragrance_desc": fragrance_desc,          # 예: 플로럴향, 달콤한향
#         "best_seasons": season_desc,               # 예: 가을, 겨울
#
#         "perfume_mainaccords": ", ".join([
#             perfume["mainaccord1"],
#             perfume["mainaccord2"],
#             perfume["mainaccord3"]
#         ]),
#
#         "review_summary": "(리뷰없음)"
#     }
#
#     ## A+B) 종합
# def build_top3_llm_inputs(
#     score_df,
#     user_df,
#     perfume_df,
#     perfume_classification,
#     perfume_color,
#     perfume_season
# ):
#     user_context = build_user_context(user_df, user_id)
#
#     llm_inputs = []
#
#     # user_id 기준으로 score_df 필터링
#     score_df_user = score_df[score_df["user_id"] == user_id]
#     if score_df_user.empty:
#         raise ValueError(f"user_id {user_id}에 대한 score가 없습니다.")
#
#     for _, row in score_df_user.iterrows():
#         llm_input = build_perfume_context(
#             row,
#             perfume_df,
#             perfume_classification,
#             perfume_color,
#             perfume_season,
#             user_context
#         )
#         llm_inputs.append(llm_input)
#
#     return llm_inputs
# # LLM 호출하여 종합 추천 이유 생성
# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#
# def generate_top3_recommend_summary(
#     user_style: str,
#     user_season: str,
#     perfumes: list
# ):
#     system_prompt = """
#     너는 향수 추천 서비스에서 종합 추천 이유를 작성하는 에디터다.
#
#     다음 구조를 반드시 지켜서 작성한다.
#
#     1. 총 3개의 문단으로만 작성한다.
#     2. 각 문단은 한 줄 이상 띄우지 않는다.
#     3. 각 문단은 명확한 역할을 가진다.
#
#     - 1문단:
#     왜 이 세 가지 향수가 함께 추천되었는지에 대한 전체 요약.
#     사용자의 스타일과 계절을 중심으로 공통된 방향성을 설명한다.
#
#     - 2문단:
#     style / color / season 관점에서 공통적으로 작용한 요소를 구체적으로 풀어 설명한다.
#     이때 color는 반드시 아래 순서로 자세히 설명한다.
#
#     (필수 색감 서술 규칙)
#     A) 사용자 착장의 색감(상의/하의/원피스)을 먼저 구체적으로 묘사한다.
#     - 밝기(밝은/중간/짙은), 채도(선명한/차분한), 온도감(웜/쿨), 대비(톤온톤/대비감) 중 최소 2가지를 포함한다.
#     B) 그 색감이 향수의 분위기(따뜻함/차분함/세련됨/생동감 등)와 어떻게 이어지는지 설명한다.
#     C) 문장만 나열하지 말고, “어떤 장면에서 어울리는지”를 짧게 한 번 붙인다. (예: 가을 오후 산책, 운동 후 데일리 등)
#
#     점수의 수치나 비교 표현은 사용하지 않는다.
#     같은 의미의 문장을 반복하지 않는다.
#
#     - 3문단:
#     세 향수가 서로 어떤 결의 차이를 가지는지 한 문장씩 간결하게 정리한다.
#     이 문단에서만 향수명을 언급할 수 있다.
#
#     추가 규칙:
#     - 개별 향수를 장황하게 설명하지 않는다.
#     - 부정적인 비교 표현을 사용하지 않는다.
#     - 과장된 마케팅 문구를 사용하지 않는다.
#     - 문단 사이에는 줄바꿈을 정확히 한 번만 사용한다.
#     - 단어 중간에서 줄바꿈하거나 공백을 삽입하지 않는다.
#     """
#
#     perfume_block = ""
#     for p in perfumes:
#         perfume_block += f"""
# - {p['perfume_name']} ({p['brand']})
#   · 스타일 점수 반영
#   · 색상 점수 반영
#   · 계절 점수 반영
#   · 주요 향조: {p['perfume_mainaccords']}
#   · 향의 결: {p['fragrance_desc']}
#     · 잘 어울리는 계절: {p['best_seasons']}
#
#
# """
#
#     user_prompt = f"""
# 아래는 점수 기반 분석을 통해 선별된 향수 3종의 요약이다.
# 이 정보를 바탕으로 종합 추천 이유를 작성해줘.
#
# 작성 조건:
# - 분량은 250~350자
# - 개별 향수 설명 ❌
# - 공통적인 추천 이유를 중심으로 자세히 설명
# - style / color / season 관점에서 왜 함께 묶였는지 설명
# - 마지막 문장에서 세 향수의 분위기 차이를 간단히 정리
# - 광고 문구, 과장 표현 금지
#
# [사용자 정보]
# - 사용자 스타일: {user_style}
# - 사용 계절: {user_season}
#
# [추천 향수 요약]
# {perfume_block}
# """
#
#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt}
#         ],
#         temperature=0.55,
#         max_tokens=500
#     )
#
#     return response.choices[0].message.content
#
# # 실행
# top3_llm_inputs = build_top3_llm_inputs(
#     score_df,
#     user_df,
#     perfume_df,
#     perfume_classification,
#     perfume_color,
#     perfume_season
# )
#
# top3_perfumes = [
#     {
#         "perfume_name": p["perfume_name"],
#         "brand": p["brand"],
#         "color_score": p["color_score"],
#         "season_score": p["season_score"],
#         "perfume_mainaccords": p["perfume_mainaccords"],
#         "fragrance_desc": p["fragrance_desc"],
#         "best_seasons": p["best_seasons"]
#     }
#     for p in top3_llm_inputs
# ]
# user_style = top3_llm_inputs[0]["user_style"]
# user_season = top3_llm_inputs[0]["user_season"]
#
# summary = generate_top3_recommend_summary(
#     user_style=user_style,
#     user_season=user_season,
#     perfumes=top3_perfumes
# )
#
# print(summary)

import os
from openai import OpenAI
from dotenv import load_dotenv
from ui.models import UserInfo, Score, Perfume, PerfumeClassification, PerfumeSeason

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_llm_recommendation(user_id):
    try:
        # 1. DB에서 데이터 가져오기 (CSV 로직을 Model 로직으로 교체)
        user = UserInfo.objects.get(user_id=user_id)
        # 해당 유저의 상위 3개 점수 데이터 가져오기
        top3_scores = Score.objects.filter(user=user).select_related('perfume').order_by('-myscore')[:3]

        if not top3_scores:
            return "추천 데이터가 부족하여 분석 결과를 생성할 수 없습니다."

        # 2. 사용자 컨텍스트 생성 (기존 build_user_context 로직)
        user_style_text = []
        if user.top_color: user_style_text.append(f"상의는 {user.top_color} {user.top_category or ''}")
        if user.bottom_color: user_style_text.append(f"하의는 {user.bottom_color} {user.bottom_category or ''}")
        if user.dress_color: user_style_text.append(f"원피스는 {user.dress_color}")
        user_style_summary = ", ".join(user_style_text)

        # 3. 추천 향수 3개의 상세 데이터 생성 (기존 build_perfume_context 로직)
        perfumes_for_llm = []
        for s in top3_scores:
            p = s.perfume

            # 데이터가 없으면 여기서 바로 에러(DoesNotExist)가 발생합니다.
            classif = PerfumeClassification.objects.get(perfume=p)
            frag_desc = classif.fragrance

            # 계절 정보도 마찬가지로 없으면 에러가 나도록 수정했습니다.
            ps = PerfumeSeason.objects.get(perfume=p)
            s_data = {"봄": ps.spring, "여름": ps.summer, "가을": ps.fall, "겨울": ps.winter}
            top_seasons = sorted(s_data.items(), key=lambda x: x[1], reverse=True)[:2]
            season_desc = ", ".join([ts[0] for ts in top_seasons])

            perfumes_for_llm.append({
                "perfume_name": p.perfume_name,
                "brand": p.brand,
                "perfume_mainaccords": f"{p.mainaccord1}, {p.mainaccord2}, {p.mainaccord3}",
                "fragrance_desc": frag_desc,
                "best_seasons": season_desc
            })

        # 4. LLM 실행 (사용자님이 주신 프롬프트와 규칙 그대로 적용)
        return generate_top3_recommend_summary(
            user_style=f"전체적으로 {user_style_summary}의 스타일",
            user_season=user.season,
            perfumes=perfumes_for_llm
        )

    except Exception as e:
        return f"분석 중 오류 발생: {str(e)}"


def generate_top3_recommend_summary(user_style: str, user_season: str, perfumes: list):
    # [사용자님의 시스템 프롬프트 복구]
    system_prompt = """
    너는 향수 추천 서비스에서 종합 추천 이유를 작성하는 에디터다.
    다음 구조를 반드시 지켜서 작성한다.
    1. 총 3개의 문단으로만 작성한다.
    2. 각 문단은 한 줄 이상 띄우지 않는다.
    3. 각 문단은 명확한 역할을 가진다.
    - 1문단: 왜 이 세 가지 향수가 함께 추천되었는지에 대한 전체 요약. 사용자의 스타일과 계절을 중심으로 공통된 방향성을 설명한다.
    - 2문단: style / color / season 관점에서 공통적으로 작용한 요소를 구체적으로 풀어 설명한다. 이때 color는 반드시 아래 순서로 자세히 설명한다.
    (필수 색감 서술 규칙)
    A) 사용자 착장의 색감(상의/하의/원피스)을 먼저 구체적으로 묘사한다.
    - 밝기(밝은/중간/짙은), 채도(선명한/차분한), 온도감(웜/쿨), 대비(톤온톤/대비감) 중 최소 2가지를 포함한다.
    B) 그 색감이 향수의 분위기(따뜻함/차분함/세련됨/생동감 등)와 어떻게 이어지는지 설명한다.
    C) 문장만 나열하지 말고, “어떤 장면에서 어울리는지”를 짧게 한 번 붙인다. (예: 가을 오후 산책, 운동 후 데일리 등)
    점수의 수치나 비교 표현은 사용하지 않는다. 같은 의미의 문장을 반복하지 않는다.
    - 3문단: 세 향수가 서로 어떤 결의 차이를 가지는지 한 문장씩 간결하게 정리한다. 이 문단에서만 향수명을 언급할 수 있다.
    추가 규칙: 개별 향수를 장황하게 설명하지 않는다. 부정적인 비교 표현을 사용하지 않는다. 과장된 마케팅 문구를 사용하지 않는다. 문단 사이에는 줄바꿈을 정확히 한 번만 사용한다. 단어 중간에서 줄바꿈하거나 공백을 삽입하지 않는다.
    """

    perfume_block = ""
    for p in perfumes:
        perfume_block += f"""
    - {p['perfume_name']} ({p['brand']})
      · 스타일 점수 반영
      · 색상 점수 반영
      · 계절 점수 반영
      · 주요 향조: {p['perfume_mainaccords']}
      · 향의 결: {p['fragrance_desc']}
      · 잘 어울리는 계절: {p['best_seasons']}
    """

    # [사용자님의 유저 프롬프트 복구]
    user_prompt = f"""
    아래는 점수 기반 분석을 통해 선별된 향수 3종의 요약이다. 이 정보를 바탕으로 종합 추천 이유를 작성해줘.
    작성 조건:
    - 분량은 250~350자
    - 개별 향수 설명 ❌
    - 공통적인 추천 이유를 중심으로 자세히 설명
    - style / color / season 관점에서 왜 함께 묶였는지 설명
    - 마지막 문장에서 세 향수의 분위기 차이를 간단히 정리
    - 광고 문구, 과장 표현 금지
    [사용자 정보]
    - 사용자 스타일: {user_style}
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
        temperature=0.55,
        max_tokens=500
    )
    return response.choices[0].message.content