import random
from typing import List
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import re
import asyncio

load_dotenv()

# OpenAI 클라이언트 비동기 설정
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
    print("✅ OpenAI 1.0+ 라이브러리 로드 성공")
except ImportError:
    print("⚠️ OpenAI 라이브러리 없음 - 백업 질문 사용")
    OPENAI_AVAILABLE = False

class InterviewGenerator:
    def __init__(self):
        self.openai_client = AsyncOpenAI() if OPENAI_AVAILABLE else None

        self.job_domains = {
            "Management": {
                "areas": ["리더십", "전략기획", "인사관리"],
                "skills": ["의사결정", "팀빌딩", "갈등해결"],
                "scenarios": ["팀 갈등 상황", "예산 부족", "목표 미달"]
            },
            # ... 생략 (기타 직무 동일하게 유지)
        }

    async def generate_questions(self, job_position: str, num_questions: int) -> List[str]:
        if job_position not in self.job_domains:
            raise ValueError(f"지원하지 않는 직무: {job_position}")

        generated_questions = []

        # 1. OpenAI 질문 생성 시도
        try:
            if self.openai_client:
                print("🧠 OpenAI로 질문 생성을 시도합니다.")
                ai_questions = await self._generate_ai_questions(job_position, num_questions)
                print(f"🤖 생성된 질문: {ai_questions}")
                if ai_questions:
                    generated_questions.extend(ai_questions)
        except Exception as e:
            print(f"⚠️ 질문 생성 실패: {e}")

        # 2. "자기소개" 고정
        final_questions = ["자기소개를 해주세요."]
        generated_questions = [q for q in generated_questions if "자기소개" not in q]
        final_questions.extend(generated_questions[:num_questions - 1])

        # 3. 부족하면 백업 질문 추가
        remaining = num_questions - len(final_questions)
        if remaining > 0:
            print(f"🔄 {remaining}개 백업 질문 추가")
            fallback = self._generate_fallback_questions(job_position, num_questions)
            for q in fallback:
                if len(final_questions) >= num_questions:
                    break
                if q not in final_questions:
                    final_questions.append(q)

        return final_questions[:num_questions]

    async def _generate_ai_questions(self, job_position: str, num_questions: int) -> List[str]:
        domain = self.job_domains[job_position]

        prompt = f"""
{job_position} 직무 면접 질문 {num_questions}개를 생성해주세요.

직무 정보:
- 핵심 영역: {', '.join(domain['areas'])}
- 주요 스킬: {', '.join(domain['skills'])}
- 상황 예시: {', '.join(domain['scenarios'])}

요구사항:
1. 실무 중심의 구체적인 질문
2. 역량 평가 가능한 질문
3. "자기소개"는 제외
4. 한국어로 작성
5. 각 질문을 한 줄로 작성

질문 {num_questions}개:
"""

        response = await self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # 또는 gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "당신은 전문 HR 면접관입니다. 실무 중심의 질문을 생성하세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=700,
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()
        parsed = self._parse_questions(content)
        validated = self._validate_questions(parsed)
        return validated

    def _parse_questions(self, content: str) -> List[str]:
        lines = content.strip().split('\n')
        questions = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            line = re.sub(r'^\s*[\d]+[\.|\)]\s*', '', line)
            line = re.sub(r'^[\-\*\•\s]+', '', line)
            if '?' in line or line.endswith(('요', '까', '나요')):
                if not line.endswith('?'):
                    line = line.rstrip('.요까나') + '?'
                questions.append(line)
        return questions

    def _validate_questions(self, questions: List[str]) -> List[str]:
        return [q for q in questions if 10 <= len(q) <= 200 and '자기소개' not in q]

    def _generate_fallback_questions(self, job_position: str, num_questions: int) -> List[str]:
        domain = self.job_domains[job_position]
        fallback_pool = [
            "자기소개를 해주세요.",
            f"{job_position} 분야에서 가장 중요한 역량은 무엇인가요?",
            f"{domain['areas'][0]} 관련 경험을 설명해주세요.",
            f"{domain['scenarios'][0]} 상황에서 어떻게 대응했나요?",
            f"{domain['skills'][0]} 능력을 보여준 경험이 있나요?",
            "팀워크 경험에 대해 말해주세요.",
            "업무 중 가장 어려웠던 문제와 해결 방법은?",
            "앞으로의 커리어 목표는?",
            f"{job_position} 분야의 최근 트렌드에 대해 이야기해보세요.",
            "회사를 선택할 때 가장 중요하게 생각하는 요소는?"
        ]
        selected = [fallback_pool[0]]
        selected.extend(random.sample(fallback_pool[1:], min(num_questions - 1, len(fallback_pool) - 1)))
        return selected[:num_questions]

    def get_available_positions(self) -> List[str]:
        return list(self.job_domains.keys())

    def get_position_info(self, job_position: str) -> dict:
        return self.job_domains.get(job_position, {})
