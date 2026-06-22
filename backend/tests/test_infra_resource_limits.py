import os
from unittest import TestCase

import pytest
import yaml


class TestInfraResourceLimits(TestCase):
    @classmethod
    def setUpClass(cls):
        # 프로젝트 루트 경로에 위치한 docker-compose.prod.yml 파일 위치 추적
        cls.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        cls.compose_path = os.path.join(cls.project_root, "docker-compose.prod.yml")

    def test_prod_compose_file_exists(self):
        """docker-compose.prod.yml 파일이 실제로 존재하는지 검증"""
        assert os.path.exists(self.compose_path), f"Compose file not found at: {self.compose_path}"

    def test_prod_compose_parsable(self):
        """YAML 파일이 정상 파싱 가능한지 검증"""
        with open(self.compose_path, encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                assert data is not None
                assert "services" in data
            except yaml.YAMLError as exc:
                pytest.fail(f"YAML parsing failed: {exc}")

    def test_services_resource_limits_defined(self):
        """모든 서비스 컨테이너에 CPU 및 메모리 limits/reservations 제한이 정적으로 정의되어 있는지 검증"""
        with open(self.compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        services = data.get("services", {})
        required_services = ["postgres_db", "redis_broker", "api-server", "async_worker", "nginx"]

        for s_name in required_services:
            assert s_name in services, f"Required service '{s_name}' is missing in compose"
            s_config = services[s_name]

            # deploy 및 resources 스펙 검증
            assert "deploy" in s_config, f"Service '{s_name}' does not have 'deploy' block"
            deploy = s_config["deploy"]
            assert "resources" in deploy, f"Service '{s_name}' does not have 'resources' limits in deploy"
            resources = deploy["resources"]

            # limits 사양 검사
            assert "limits" in resources, f"Service '{s_name}' is missing 'limits' specification"
            limits = resources["limits"]
            assert "cpus" in limits, f"Service '{s_name}' limits is missing 'cpus' constraint"
            assert "memory" in limits, f"Service '{s_name}' limits is missing 'memory' constraint"

            # reservations 사양 검사 (nginx, postgres_db, redis_broker, api-server, async_worker 공통)
            assert "reservations" in resources, f"Service '{s_name}' is missing 'reservations' specification"
            reservations = resources["reservations"]
            assert "cpus" in reservations, f"Service '{s_name}' reservations is missing 'cpus' constraint"
            assert "memory" in reservations, f"Service '{s_name}' reservations is missing 'memory' constraint"

    def test_essential_services_healthchecks_and_restart_policy(self):
        """핵심 백엔드 서비스(DB, Redis, API)에 헬스 체크와 자동 재기동(restart) 정책이 적용되었는지 검증"""
        with open(self.compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        services = data.get("services", {})
        healthcheck_targets = ["postgres_db", "redis_broker", "api-server"]

        for s_name in healthcheck_targets:
            assert s_name in services, f"Essential service '{s_name}' missing"
            s_config = services[s_name]

            # restart 정책 검증
            assert "restart" in s_config, f"Service '{s_name}' is missing 'restart' policy"
            assert (
                s_config["restart"] in ["always", "unless-stopped"] or "on-failure" in s_config["restart"]
            ), f"Service '{s_name}' has invalid restart policy: {s_config.get('restart')}"

            # healthcheck 사양 검증
            assert "healthcheck" in s_config, f"Service '{s_name}' is missing 'healthcheck' block"
            hc = s_config["healthcheck"]
            assert "test" in hc, f"Service '{s_name}' healthcheck test command is missing"
            assert "interval" in hc, f"Service '{s_name}' healthcheck interval is missing"
            assert "timeout" in hc, f"Service '{s_name}' healthcheck timeout is missing"
            assert "retries" in hc, f"Service '{s_name}' healthcheck retries count is missing"
