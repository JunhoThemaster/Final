def clova_transcribe(audio_file_path: str) -> str:
    import requests
    import os

    API_KEY = os.getenv("NAVER_CLOVA_API_KEY")
    API_SECRET = os.getenv("NAVER_CLOVA_API_SECRET")
    API_URL = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt"

    if not os.path.exists(audio_file_path):
        print(f"❌ 파일이 존재하지 않음: {audio_file_path}")
        return "[파일 없음]"
    
    try:
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        
        headers = {
            'X-NCP-APIGW-API-KEY-ID': API_KEY,
            'X-NCP-APIGW-API-KEY': API_SECRET,
            'Content-Type': 'application/octet-stream'
        }
        params = { 'lang': 'Kor' }

        response = requests.post(API_URL, data=audio_data, headers=headers, params=params, timeout=30)

        if response.status_code == 200:
            result = response.json()
            text = result.get('text', '').strip()
            print(f"✅ Clova 변환 성공: '{text}'")
            return text or "[전사 결과 없음]"
        else:
            print(f"❌ Clova API 오류: {response.status_code}")
            print(f"📄 응답 내용: {response.text}")
            return "[전사 실패]"
    except Exception as e:
        print(f"❌ Clova 음성 인식 실패: {e}")
        return "[전사 실패]"
