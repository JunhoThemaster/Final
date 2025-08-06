from typing import List
from openai import AsyncOpenAI
import re
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
    print("✅ OpenAI 라이브러리 로드 성공")
except ImportError:
    print("⚠️ OpenAI 라이브러리 없음 - 질문 생성을 사용할 수 없습니다.")
    OPENAI_AVAILABLE = False


class InterviewGenerator:
    def __init__(self):
        self.openai_client = AsyncOpenAI() if OPENAI_AVAILABLE else None

    async def generate_questions(self, job_position: str, job_url: str, num_questions: int) -> List[str]:
        if not self.openai_client:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다.")

        prompt = f"""
당신은 AI 면접관입니다. 아래 정보를 참고하여 해당 직무에 적합한 면접 질문 {num_questions}개를 작성해주세요.

직무명: {job_position}
채용공고 URL: {job_url}

요구사항:
- 각 질문은 실무 중심이어야 하며, 지원자의 역량을 평가할 수 있어야 합니다.
- 너무 일반적이지 않게, 가능하면 실제 인터뷰에서 쓸 수 있는 질문으로 만드세요.
- 각 질문은 한 줄로 작성해주세요.
- 질문 끝에 반드시 물음표(?)를 붙이세요.
- "자기소개"는 제외해주세요.
- 한국어로 작성해주세요.

질문 {num_questions}개:
"""

        response = await self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 채용 전문가 AI입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()
        return self._parse_questions(content)

    def _parse_questions(self, content: str) -> List[str]:
        """
        번호나 불릿 기호를 제거하고 질문 문장만 추출
        """
        lines = content.strip().split('\n')
        questions = []
        for line in lines:
            line = re.sub(r'^\s*[\d]+[\.\)]\s*', '', line)  # "1. " or "1)" 제거
            line = re.sub(r'^[\-\*\•]\s*', '', line)        # 불릿 기호 제거
            line = line.strip()
            if line and line.endswith("?") and "자기소개" not in line:
                questions.append(line)
        return questions
