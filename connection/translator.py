"""DeepL API를 이용한 한↔영 검색어 번역기."""
import os
from functools import lru_cache
from pathlib import Path

import deepl
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
_translator = None


def _get_translator():
    global _translator
    if _translator is None:
        api_key = os.getenv("DEEPL_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPL_API_KEY가 .env에 설정되어 있지 않습니다.")
        _translator = deepl.Translator(api_key)
    return _translator


@lru_cache(maxsize=256)
def translate_ko_to_en(text: str) -> str:
    if not text or not text.strip():
        return text
    clean = text.strip()
    if clean.isascii():
        return clean
    try:
        result = _get_translator().translate_text(
            clean, source_lang="KO", target_lang="EN-US"
        )
        return result.text if result.text else clean
    except Exception as e:
        print(f"[DeepL 한→영 번역 오류] 원본 텍스트를 그대로 사용합니다: {e}")
        return clean


@lru_cache(maxsize=256)
def translate_en_to_ko(text: str) -> str:
    if not text or not text.strip():
        return text
    clean = text.strip()
    if not clean.isascii():
        return clean
    try:
        translator = _get_translator()
        result = translator.translate_text(
            clean.lower(), source_lang="EN", target_lang="KO"
        )
        translated = result.text.strip() if result.text else clean
        # 단독 영단어라 DeepL이 번역하지 않고 그대로 반환한 경우 관사 문맥을 붙여 재시도
        if translated.lower() == clean.lower() and " " not in clean:
            retry = translator.translate_text(
                f"a {clean.lower()}", source_lang="EN", target_lang="KO"
            )
            if retry.text and retry.text.strip().lower() != clean.lower():
                translated = retry.text.strip()
        return translated
    except Exception as e:
        print(f"[DeepL 영→한 번역 오류] 원본 텍스트를 그대로 사용합니다: {e}")
        return clean
