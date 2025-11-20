import json
import os
from typing import List, Dict, Any
from config import DEFAULT_SYMBOLS

SETTINGS_FILE = 'trader_settings.json'

class SettingsManager:
    """트레이더 설정 관리자"""
    
    def __init__(self, settings_file: str = SETTINGS_FILE):
        self.settings_file = settings_file
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """설정 파일 로드 (없으면 기본값 생성)"""
        if not os.path.exists(self.settings_file):
            return self._create_default_settings()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                return self._ensure_structure(loaded)
        except Exception as e:
            print(f"설정 로드 실패: {e}, 기본값 사용")
            return self._create_default_settings()

    def _create_default_settings(self) -> Dict[str, Any]:
        """기본 설정 생성"""
        default_settings = {
            "long_term_symbols": DEFAULT_SYMBOLS,
            "short_term_enabled": True,
            "short_term_pool_size": 3,
            "short_term_candidates": [
                "AMD", "INTC", "QCOM", "MU", "NFLX", "DIS", "NKE", "SBUX", "KO", "PEP"
            ] # 예시 후보군
        }
        structured = self._ensure_structure(default_settings)
        self.save_settings(structured)
        return structured

    def get_settings(self) -> Dict[str, Any]:
        """현재 설정 반환"""
        return self.settings

    def save_settings(self, new_settings: Dict[str, Any]):
        """설정 저장"""
        self.settings = self._ensure_structure(new_settings)
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def _ensure_structure(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """설정 파일에 필수 키가 모두 존재하도록 보정"""
        if not isinstance(settings, dict):
            settings = {}

        settings.setdefault("long_term_symbols", list(DEFAULT_SYMBOLS))
        settings.setdefault("short_term_enabled", True)
        settings.setdefault("short_term_pool_size", 3)
        settings.setdefault("short_term_candidates", [])

        # 타입 보정
        if not isinstance(settings["long_term_symbols"], list):
            settings["long_term_symbols"] = list(DEFAULT_SYMBOLS)

        if not isinstance(settings["short_term_candidates"], list):
            settings["short_term_candidates"] = []

        try:
            settings["short_term_pool_size"] = int(settings.get("short_term_pool_size", 3))
        except ValueError:
            settings["short_term_pool_size"] = 3

        return settings

    def get_long_term_symbols(self) -> List[str]:
        return self.settings.get("long_term_symbols", [])

    def is_short_term_enabled(self) -> bool:
        return self.settings.get("short_term_enabled", False)

    def get_short_term_pool_size(self) -> int:
        return self.settings.get("short_term_pool_size", 3)
    
    def get_short_term_candidates(self) -> List[str]:
        return self.settings.get("short_term_candidates", [])

# 전역 인스턴스
settings_manager = SettingsManager()
