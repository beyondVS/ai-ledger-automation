import os
from unittest import TestCase

import yaml


class TestNginxInfrastructure(TestCase):
    @classmethod
    def setUpClass(cls):
        # 프로젝트 루트 경로 추적
        cls.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        cls.nginx_conf_path = os.path.join(cls.project_root, "nginx.conf")
        cls.compose_path = os.path.join(cls.project_root, "docker-compose.prod.yml")

    def test_nginx_conf_exists(self):
        """nginx.conf 파일 존재 확인"""
        assert os.path.exists(self.nginx_conf_path)

    def test_nginx_ssl_offloading_redirect_configured(self):
        """nginx.conf 내부의 HTTPS 리다이렉션 조건(X-Forwarded-Proto != https) 존재 검증"""
        with open(self.nginx_conf_path, encoding="utf-8") as f:
            content = f.read()

        # SSL 오프로딩 환경에서 HTTPS가 아닐 때 301 리다이렉트 처리하는 블록 확인
        assert "http_x_forwarded_proto" in content
        assert "301 https://" in content

    def test_nginx_port_isolation_and_no_443_exposure(self):
        """docker-compose.prod.yml에서 Nginx 포트 80만 노출하고, 443 포트 매핑은 배제되었는지 검증 (SSL Offloading 대응)"""
        with open(self.compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        services = data.get("services", {})
        assert "nginx" in services
        nginx_config = services["nginx"]

        assert "ports" in nginx_config
        ports = nginx_config["ports"]

        mapped_ports = [str(p) for p in ports]
        has_80 = any("80:80" in p or "80" in p for p in mapped_ports)
        has_443 = any("443:443" in p or "443" in p for p in mapped_ports)

        # 포트 80만 개방하고 443 노출은 배제되어야 함
        assert has_80, f"Port 80 binding is missing: {mapped_ports}"
        assert not has_443, f"Security Breach: Port 443 is exposed during SSL Offloading: {mapped_ports}"
