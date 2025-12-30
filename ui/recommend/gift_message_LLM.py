import os
from openai import OpenAI
from dotenv import load_dotenv
from ui.models import UserInfo, Score

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_someone_gift_message(user_id, recipient, situation, msg_type):
    """
    사용자가 작성한 정교한 프롬프트 규칙을 모두 유지하며,
    메시지 타입(짧은/긴)에 따라 분량을 엄격히 조절하여 기프트 카드 문구를 생성합니다.
    """
    try:
        # 1. 값 매핑 (영문/국문 혼용 대응)
        recipient_map = {
            'lover': '연인', 'friend': '친구', 'family': '가족', 'colleague': '직장동료',
            '연인': '연인', '친구': '친구', '가족': '가족', '직장동료': '직장동료'
        }
        situation_map = {
            'firstmeet': '첫만남', 'birthday': '생일', 'anniversary': '축하 기념일',
            'congrats': '축하 기념일', '첫만남': '첫만남', '생일': '생일', '축하 기념일': '축하 기념일'
        }

        recipient_type = recipient_map.get(recipient, '소중한 분')
        situation_type = situation_map.get(situation, '특별한 날')

        # 2. 향수 이름 가져오기 (분위기 파악용 context)
        scores = Score.objects.filter(user_id=user_id).select_related('perfume').order_by('-myscore')[:3]
        perfume_names = [s.perfume.perfume_name for s in scores]

        if not perfume_names:
            perfume_names = ["추천된 향기"]

        # 3. 짧은 문구 / 긴 문구에 따른 지시문 설정
        if msg_type == "짧은":
            format_instruction = "반드시 딱 '1문장'의 짧은 문구로 작성하라."
            paragraph_instruction = "문단 나누지 말고 한 줄로만 작성하라."
            sentence_rule = "1문장 제한"
        else:
            format_instruction = "5~6문장 내외의 정성스러운 편지글 형식으로 작성하라."
            paragraph_instruction = "내용에 따라 2~3문단으로 나누어 작성하라."
            sentence_rule = "5~6문장 유지"

        # 4. 시스템 프롬프트 구성 (기존 규칙 누락 없이 전체 포함)
        system_prompt = f"""
                너는 따뜻하고 감성적인 문장을 쓰는 기프트 카드 작가다.
                사용자가 '{recipient_type}'에게 '{situation_type}'로 향수를 선물하려고 한다.
                선물하는 사람의 마음이 잘 전달되도록 감동적인 카드 문구를 작성하라.

                [입력 값 정의/제약]
                - recipient_type: '{recipient_type}'
                - situation: '{situation_type}'
                - perfume_names(참고용): {", ".join(perfume_names)}

                [작성 규칙]
                1. 연인에게는 부드럽고 다정하게 말한다.
                2. 친구에게는 친근하게 말한다.
                3. 가족에게는 따뜻하게 말한다.
                4. 직장동료에게는 따뜻하고 부드럽게 말한다.
                5. 작성할 때 최대한 말을 자연스럽게, 진짜 사람이 작성하듯이 말한다.
                6. {recipient_type}와 {situation_type}의 의미를 문장에 녹여낸다.
                7. 선택된 향수의 느낌이 '너의 분위기를 닮았다'는 점을 반드시 포함한다.
                8. 결과는 리스트 형태가 아니라, 바로 카드에 적을 수 있는 문장들로만 출력한다.
                9. {format_instruction}
                10. 추천 향수의 이름({", ".join(perfume_names)})은 절대 직접 언급하지 말 것. 대신 그 향이 주는 분위기만 묘사하라.

                [대상(recipient_type)별 톤 강제 규칙]
                11. recipient_type이 '연인'이면: 다정한 호칭/표현을 사용하고, 과한 격식체는 피한다.
                12. recipient_type이 '친구'이면: 편한 말투로 자연스럽게, 과한 로맨틱 표현은 피한다.
                13. recipient_type이 '가족'이면: 고마움/안부/따뜻함을 담고, 연애 뉘앙스 표현은 피한다.
                14. recipient_type이 '직장동료'이면: 예의 있는 따뜻함으로, 너무 사적인 애칭/과한 감정표현은 피한다.

                [상황(situation)별 “의무 포함” 문장]
                15. situation이 '첫만남'이면: “처음의 설렘/시작/첫 인상”을 담은 문장 1개를 반드시 포함한다.
                16. situation이 '생일'이면: “오늘(생일)을 축하”하는 문장 1개를 반드시 포함한다.
                17. situation이 '축하 기념일'이면: “함께한 시간/축하/앞으로도”를 담은 문장 1개를 반드시 포함한다.

                [출력 형식 제약]
                18. {sentence_rule}을 엄격히 준수하라.
                19. {paragraph_instruction}
                20. 불릿(-), 번호(1.), 제목, 따옴표로 감싼 문장, 이모지 사용을 금지한다.
                21. 문장들만 출력하고, 규칙 설명/메타 코멘트/분석을 절대 출력하지 않는다.
                """

        # 5. OpenAI API 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.8,  # 리롤 시 다양한 문구 생성을 위해 약간 높게 설정
        )

        raw_text = response.choices[0].message.content.strip()

        # 문구 리스트 반환 (프론트엔드와 호환을 위해 리스트 형태 유지)
        return [raw_text]

    except Exception as e:
        print(f"Error in LLM: {e}")
        return ["당신의 분위기를 닮은 향기를 선물합니다. 행복한 하루 되세요."]
