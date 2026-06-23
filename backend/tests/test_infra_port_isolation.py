import os
from unittest import TestCase

import yaml


class TestInfraPortIsolation(TestCase):
    @classmethod
    def setUpClass(cls):
        # 프로젝트 루트 경로에 위치한 docker-compose.prod.yml 파일 위치 추적
        cls.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        cls.compose_path = os.path.join(cls.project_root, "docker-compose.prod.yml")

    def test_prod_compose_file_exists(self):
        """docker-compose.prod.yml 파일이 존재하는지 검증"""
        assert os.path.exists(self.compose_path)

    def test_backend_ports_isolation(self):
        """Nginx 이외의 다른 모든 컨테이너 서비스에 포트 바인딩(ports)이 설정되지 않았는지 검증"""
        with open(self.compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        services = data.get("services", {})
        private_services = ["postgres_db", "redis_broker", "api-server", "async_worker"]

        for s_name in private_services:
            assert s_name in services, f"Service '{s_name}' is missing"
            s_config = services[s_name]

            # 포트 노출 방지 체크 (ports 바인딩이 아예 없어야 함)
            assert (
                "ports" not in s_config or not s_config["ports"]
            ), f"Security Violation: Service '{s_name}' is exposing ports to host: {s_config.get('ports')}"

    def test_nginx_gateway_ports_mapped(self):
        """Nginx 서비스에 포트 매핑(80 포트)이 지정되어 외부 트래픽 수신이 가능한지 검증 (SSL Offloading 적용)"""
        with open(self.compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        services = data.get("services", {})
        assert "nginx" in services, "Gateway service 'nginx' is missing"
        nginx_config = services["nginx"]

        # ports 바인딩 존재 검사
        assert "ports" in nginx_config, "Gateway 'nginx' is missing 'ports' configuration"
        ports = nginx_config["ports"]
        assert len(ports) > 0, "Gateway 'nginx' ports mapping is empty"

        # 포트 매핑 값 검사
        mapped_ports = [str(p) for p in ports]
        has_80 = any("80:80" in p or "80" in p for p in mapped_ports)
        has_443 = any("443:443" in p or "443" in p for p in mapped_ports)

        assert has_80, f"Gateway 'nginx' is missing Port 80 binding: {mapped_ports}"
        assert not has_443, f"Gateway 'nginx' should not expose Port 443 during SSL Offloading: {mapped_ports}"

    def test_network_isolation_unified(self):
        """모든 컨테이너가 동일한 가상 격리 네트워크(prod-bridge)를 사용하는지 검증"""
        with open(self.compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        services = data.get("services", {})
        required_services = ["postgres_db", "redis_broker", "api-server", "async_worker", "nginx"]

        for s_name in required_services:
            assert s_name in services, f"Service '{s_name}' is missing"
            s_config = services[s_name]

            assert "networks" in s_config, f"Service '{s_name}' is missing network configuration"
            networks = s_config["networks"]
            assert "prod-bridge" in networks, f"Service '{s_name}' is not bound to 'prod-bridge' network"
