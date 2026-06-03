import os
import sys
from pathlib import Path

import django

# backend/src/ 경로를 최상위 sys.path 검색 경로로 정밀 등록
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.insert(0, SRC_DIR)

# Django 설정 인프라 로드
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# django.setup() 기동을 통한 모델 정보 안전 인스톨
django.setup()
