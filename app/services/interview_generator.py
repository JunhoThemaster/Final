from typing import List
from openai import AsyncOpenAI
import json
import re
import ast
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
- 너무 일반적이지 않게, 가능하면 실제 인터뷰에서 쓸 수 있는 전문적인 질문으로 만드세요.
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
        lines = content.strip().split('\n')
        questions = []
        for line in lines:
            line = re.sub(r'^\s*[\d]+[\.\)]\s*', '', line)
            line = re.sub(r'^[\-\*\•]\s*', '', line)
            line = line.strip()
            if line and line.endswith("?") and "자기소개" not in line:
                questions.append(line)
        return questions

    async def build_audio_prompt(self, audio_data, job_position: str, job_url: str) -> str:
        parts = []
        for idx, r in enumerate(audio_data, 1):
            parts.append(
                f"{idx}. 질문: \"{r.question}\"\n"
                f"   감정: {r.emotion}, 확률 분포: {r.probabilities}"
            )
        joined = "\n".join(parts)

        prompt = (
            "다음은 면접 응답에 대한 감정 분석 결과입니다.\n"
            "각 질문에 대해 감지된 감정과 그 확률 분포가 주어집니다.\n"
            "이 중 감정적으로 가장 두드러진 질문 하나를 하이라이트로 선택하고,\n"
            "전체 면접의 감정 분위기를 요약해 주세요.\n"
            f"직무: {job_position}\n\n"
            f"{joined}\n\n"
            "🔸 출력 형식은 다음과 같습니다:\n"
            "{\n"
            "  'overall_emotion': '자신감',\n"
            "  'highlight_question': {\n"
            "    'question': '기술 스택 중 자신 있는 것은?',\n"
            "    'emotion': '불안',\n"
            "    'commentary': '이 질문에서 불안 감정이 가장 높게 나타났습니다.'\n"
            "  },   \n"
            "  'feedback': '전체적으로  답변을 잘했지만 특정 기술에대한 이해도가 부족. 해당 기술에 대한 구체적인 학습 필요.'\n"
            "}"
        )

        return prompt

    async def build_video_prompt(self, video_data, job_position: str, job_url: str) -> str:
        parts = []
        for idx, r in enumerate(video_data, 1):
            head_pose = r.head_pose if isinstance(r.head_pose, list) else [0, 0, 0]
            parts.append(
                f"{idx}. [타임스탬프: {r.timestamp}]\n"
                f"   감정: {r.emotion} (신뢰도: {round(r.confidence or 0.0, 2)})\n"
                f"   자세: {r.posture}, 눈깜빡임: {r.blink_count or 0}회\n"
                f"   시선: ({r.gaze_x}, {r.gaze_y}), EAR: {r.ear}, 머리 자세: {head_pose}"
            )
        joined = "\n".join(parts)

        prompt = (
            "다음은 면접자의 영상 기반 감정 및 자세 분석 결과입니다.\n"
            "각 프레임 또는 타임스탬프에 대해 감정, 자세, 시선 및 기타 시각적 정보가 기록되어 있습니다.\n"
            "이 정보를 바탕으로 다음을 도출해 주세요:\n\n"
            "1. 전체적인 감정 분위기를 요약 (`overall_emotion`)\n"
            "2. 감정적으로 또는 자세적으로 가장 특이점이 나타난 시점의 하이라이트 (`highlight_frame`)\n"
            "3. 자세, 시선, 감정 표현 등에서 드러난 강점과 개선할 점 (`feedback`)\n\n"
            f"직무: {job_position}\n\n"
            f"{joined}\n\n"
            "🔸 출력 형식은 다음과 같습니다:\n"
            "{\n"
            "  'overall_emotion': '예: 침착함',\n"
            "  'highlight_frame': {\n"
            "    'timestamp': '2025-08-06 20:13:15',\n"
            "    'emotion': '불안',\n"
            "    'commentary': '이 시점에서 시선이 아래로 치우치고 EAR 수치가 낮아, 긴장 상태로 보였습니다.'\n"
            "  },\n"
            "  'feedback': '전체적으로 자세는 안정적이었으나, 질문 중간에 눈을 자주 깜빡이며 불안한 모습을 보였습니다. 시선 처리가 개선되면 더 나은 인상을 줄 수 있습니다.'\n"
            "}"
        )

        return prompt

    async def call_llm(self, prompt: str, model: str = "gpt-4") -> dict:
        if not self.openai_client:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다.")

        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "넌 감정 분석,면접 요약 전문가야. JSON으로 결과를 정확히 반환해."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(content)
            except Exception as e:
                raise ValueError(f"LLM 응답 파싱 실패: {e}")
    async def build_comprehensive_interview_feedback(
                self,
                audio_analysis: dict,
                video_analysis: dict,
                job_position: str,
                job_url: str = "",
            ) -> str:
                prompt = (
                    "당신은 면접 평가 전문가입니다.\n"
                    "다음은 한 면접자의 오디오 및 영상 기반 감정/자세 분석 데이터입니다.\n\n"
                    "이 데이터를 종합적으로 분석하여 다음 5가지를 평가하세요:\n\n"

                    "1️⃣ 전체 면접 태도 (`overall_attitude`)\n"
                    "- 면접 전반에서 드러난 태도, 자신감, 성실성, 긴장감 등을 요약하세요.\n"
                    "- 예: \"전반적으로 침착하고 성실한 태도를 보였으나, 일부 질문에서 불안한 모습을 드러냈습니다.\"\n\n"

                    "2️⃣ 음성 감정 흐름 (`voice_emotion_summary`)\n"
                    "- 각 질문 응답 중의 감정 변화, 일관성 여부, 강도 등을 기술하세요.\n"
                    "- 예: \"대부분의 질문에서 침착한 태도를 보였으나, 지원 동기 질문에서 불안과 긴장이 감지되었습니다.\"\n\n"

                    "3️⃣ 시각적 태도 및 자세 평가 (`posture_summary`)\n"
                    "- EAR, blink_count, gaze, head_pose 등을 바탕으로 비언어적 태도를 분석하세요.\n"
                    "- 예: \"시선이 자주 흔들렸고, EAR이 낮은 구간이 있어 피로감이나 긴장이 감지됨\"\n\n"

                    "4️⃣ 응답 품질 요약 (`answer_quality`)\n"
                    "- 음성 텍스트 응답을 바탕으로 논리성, 명확성, 직무 적합성을 평가하세요.\n"
                    "- 예: \"답변의 구조가 명확했고, 직무 관련 질문에서는 일관성 있게 경험을 설명함\"\n\n"

                    "5️⃣ 개선할 수 있는 점 (`improvement_suggestions`)\n"
                    "- 음성 및 시각적 표현에서 개선이 필요한 점을 구체적으로 제안하세요.\n"
                    "- 예: \"\'기술 스택\' 질문에서 시선이 자주 흔들리고 말이 빨라져 긴장이 드러났음. 정면 응시와 천천히 말하는 연습 필요.\"\n"
                    "- 가능하다면 특정 질문에 대한 모범답안 예시 또는 개선 전략도 포함하세요.\n\n"

                    f"📝 직무명: {job_position}\n"
                    f"🌐 채용공고 URL: {job_url or '없음'}\n\n"

                    "🎧 오디오 기반 분석 요약 (audio_analysis):\n"
                    f"{json.dumps(audio_analysis, ensure_ascii=False, indent=2)}\n\n"

                    "🎥 영상 기반 분석 요약 (video_visual_analysis):\n"
                    f"{json.dumps(video_analysis, ensure_ascii=False, indent=2)}\n\n"

                    "📌 반드시 아래 JSON 형식으로만 결과를 출력하세요 (코드 블록, 설명 문구 없이 순수 JSON만 출력):\n"
                    '{\n'
                    '  "overall_attitude": "",\n'
                    '  "voice_emotion_summary": "",\n'
                    '  "posture_summary": "",\n'
                    '  "answer_quality": "",\n'
                    '  "improvement_suggestions": ""\n'
                    '}\n'
                )
                return prompt

