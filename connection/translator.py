from deep_translator import GoogleTranslator

def translate_ko_to_en(text: str) -> str:
    if not text or not text.strip():
        return text
    try:
        return GoogleTranslator(source='ko', target='en').translate(text)
    except Exception as e:
        print(f"[번역 오류] 원본 텍스트를 그대로 사용합니다: {e}")
        return text
