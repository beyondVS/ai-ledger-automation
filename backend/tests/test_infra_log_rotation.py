import os
from unittest import TestCase

import yaml


class TestInfraLogRotation(TestCase):
    @classmethod
    def setUpClass(cls):
        # 프로젝트 루트 경로에 위치한 docker-compose.prod.yml 파일 위치 추적
        cls.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        cls.compose_path = os.path.join(cls.project_root, "docker-compose.prod.yml")

    def test_prod_compose_file_exists(self):
        """docker-compose.prod.yml 파일이 존재하는지 검증"""
        assert os.path.exists(self.compose_path)

    def test_global_logging_anchor_defined(self):
        """YAML 설정 내에 공통 로깅 기본 템플릿(x-logging)이 선언되었는지 검증"""
        with open(self.compose_path, encoding="utf-8") as f:
            yaml.safe_load(f)

        # PyYAML은 앵커(&)를 파싱할 때 딕셔너리에 병합하므로, 원시 텍스트 상에서 앵커 키워드가 있는지 확인
        with open(self.compose_path, encoding="utf-8") as f:
            raw_text = f.read()
            assert (
                "x-logging:" in raw_text or "default-logging" in raw_text
            ), "Global logging anchor 'x-logging' is missing in raw compose text"

    def test_services_log_rotation_policy_applied(self):
        """모든 서비스에 json-file 로그 드라이버 및 max-size: 10m, max-file: 3 제한 정책이 누락 없이 강제 적용되었는지 검증"""
        with open(self.compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        services = data.get("services", {})
        required_services = ["postgres_db", "redis_broker", "api-server", "async_worker", "nginx"]

        for s_name in required_services:
            assert s_name in services, f"Required service '{s_name}' is missing"
            s_config = services[s_name]

            # 로깅 지시문 존재 확인
            assert "logging" in s_config, f"Service '{s_name}' does not define a 'logging' block"
            logging = s_config["logging"]

            # 로깅 드라이버 방식 확인
            assert (
                logging.get("driver") == "json-file"
            ), f"Service '{s_name}' logging driver must be 'json-file', got: {logging.get('driver')}"

            # 상세 옵션 확인
            options = logging.get("options", {})
            max_size = options.get("max-size")
            max_file = options.get("max-file")

            # 10m 및 3 제한 검증 (문자열 또는 숫자 호환 대조)
            assert str(max_size) == "10m", f"Service '{s_name}' logging 'max-size' must be '10m', got: {max_size}"
            assert str(max_file) == "3", f"Service '{s_name}' logging 'max-file' must be '3', got: {max_file}"
