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
            너는 향수를 선물할 때의 이유를 자연스럽게 풀어내는 기프트 카드 작가다.
            사용자는 '{recipient_type}'에게 '{situation_type}'이라는 상황으로 향수를 선물하려 한다.
    
            카드에는 왜 이 향을 골랐는지가 드러나야 하며,
            그 이유는 반드시 style, color, season의 흐름으로 설명되어야 한다.
    
            [작성 방향]
            - 편지처럼 부드럽고 자연스러운 문장으로 작성한다.
            - 감정 표현은 절제하되, 진심이 느껴지도록 쓴다.
            - 향수 이름이나 브랜드는 언급하지 않는다.
            - 리스트나 설명문이 아닌, 바로 카드에 적을 수 있는 문장만 출력한다.
    
            [핵심 서술 규칙]
            1. 왜 이 향수를 선물하는지가 드러나야 한다.
            2. 이유는 반드시 다음 순서를 따른다.
               style → color → season
    
            - style:
            '{recipient_type}'인 그 사람의 분위기나 인상을 언급하며 문장을 시작하거나 연결한다.
    
            - color:
              그 사람에게 어울리는 색감이나 이미지의 결을 묘사하고,
              그 색감이 향의 분위기와 어떻게 이어지는지 설명한다.
    
            - season:
              지금의 계절이나 공기감이 이 향과 왜 잘 어울리는지를 덧붙인다.
    
            3. 향에 대한 감각적 표현을 반드시 포함한다.
               - 처음 닿을 때의 인상, 잔향, 가까이 있을 때의 공기감 중 최소 2가지 사용
               - 노트 나열이나 추상적인 표현은 피한다.
    
            [형식 제약]
            - {format_instruction}
            - {sentence_rule}을 엄격히 지킨다.
            - {paragraph_instruction}
            - 불릿, 번호, 제목, 이모지 사용 금지
            - 규칙 설명이나 메타 코멘트는 출력하지 않는다.
            
            [긴 문구 문단 분리 강제 규칙]
            - 긴 문구일 경우 반드시 줄바꿈을 사용해 2~3문단으로 나눈다.
            - 각 문단은 최소 1문장 이상 포함해야 한다.
            - 문단 사이에는 줄바꿈을 정확히 한 번만 사용한다.
            
            [짧은 문구 전용 길이 제한]
            - 짧은 문구(1문장)는 40~60자 이내로 작성한다.
            - style, color, season은 한 단어 또는 짧은 구로만 언급한다.
            - 향에 대한 감각 표현은 1가지만 사용한다.
            [받는 사람·상황 의무 규칙]
            - 짧은 문구(1문장)일 경우에도 recipient_type과 situation_type을 반드시 직접 언급해야 한다.
            - 대명사(너, 당신)만 사용하고 상황을 생략하는 것은 허용하지 않는다.
            - 문장 앞이나 중간에 자연스럽게 포함한다.
            
            [말투 강제 규칙]
            - 모든 문장은 recipient_type에 맞는 말투를 반드시 따른다.
            - 말투가 맞지 않으면 규칙 위반으로 간주한다.
            
            · recipient_type = '연인'
              - 부드럽고 다정한 어투를 사용한다.
              - 거리감 있는 존댓말, 설명체 문장은 피한다.
            
            · recipient_type = '친구'
              - 편안하고 자연스러운 말투를 사용한다.
              - 과도한 감정 표현이나 로맨틱한 뉘앙스는 피한다.
            
            · recipient_type = '가족'
              - 따뜻하고 안정적인 말투를 사용한다.
              - 애정은 담되 연인처럼 들리는 표현은 사용하지 않는다.
            
            · recipient_type = '직장동료'
              - 예의 있는 존댓말을 사용한다.
              - 지나치게 사적인 표현이나 감정 과잉을 피한다.

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