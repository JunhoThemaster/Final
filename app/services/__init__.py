from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 사용 예시
openai_key = os.getenv("OPENAI_API_KEY")
print("🔑 OpenAI API Key:", openai_key[:10], "...")  # 앞 10글자만 출력 (보안)
