from apps.ledgers.models import MerchantTemplate, TemplateExecutionHistory
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class MerchantTemplateVerifyView(APIView):
    """
    [T019] MerchantTemplateVerifyView
    - 제안된 템플릿(is_verified: False)을 승인(is_verified: True)하여
      정적 우회(Bypass) 파싱 대상으로 등록합니다.
    """

    permission_classes = [permissions.AllowAny]  # 개발/테스트 편의를 위해 일단 AllowAny로 설정 (인증 생략)

    def post(self, request, template_id, *args, **kwargs):
        template = get_object_or_404(MerchantTemplate, id=template_id)
        # request body에 parsing_rules가 제공되면 갱신
        parsing_rules = request.data.get("regex_pattern")
        if parsing_rules:
            template.parsing_rules = parsing_rules

        # is_verified 파라미터가 제공되면 업데이트, 생략 시 정규식 패턴 수정만 처리되도록 보정
        is_verified_param = request.data.get("is_verified")
        if is_verified_param is not None:
            if isinstance(is_verified_param, str):
                template.is_verified = is_verified_param.lower() == "true"
            else:
                template.is_verified = bool(is_verified_param)
        else:
            if not parsing_rules:
                template.is_verified = True

        if template.is_verified:
            template.is_blacklisted = False
            template.self_healing_attempts = 0

        template.save()

        return Response(
            {
                "status": "success",
                "message": "Template has been manually verified and promoted.",
                "id": str(template.id),
                "vendor_registration_number": template.vendor_registration_number,
                "vendor_name": template.vendor_name,
                "is_verified": template.is_verified,
                "parsing_rules": template.parsing_rules,
                "template": {
                    "id": str(template.id),
                    "is_verified": template.is_verified,
                    "is_blacklisted": template.is_blacklisted,
                    "self_healing_attempts": template.self_healing_attempts,
                },
            },
            status=status.HTTP_200_OK,
        )


class AdminTemplateListView(APIView):
    """
    [T007] AdminTemplateListView
    - 가맹점 템플릿 목록 조회 (필터링: is_verified, is_blacklisted, 사업자번호)
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        is_verified = request.query_params.get("is_verified")
        is_blacklisted = request.query_params.get("is_blacklisted")
        vrn = request.query_params.get("vendor_registration_number")

        queryset = MerchantTemplate.objects.all()
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == "true")
        if is_blacklisted is not None:
            queryset = queryset.filter(is_blacklisted=is_blacklisted.lower() == "true")
        if vrn is not None:
            queryset = queryset.filter(vendor_registration_number=vrn)

        results = []
        from apps.ledgers.models import Ledger

        for t in queryset:
            usernames = list(
                Ledger.objects.filter(vendor_registration_number=t.vendor_registration_number)
                .exclude(user__isnull=True)
                .values_list("user__username", flat=True)
                .distinct()
            )
            results.append(
                {
                    "id": str(t.id),
                    "vendor_registration_number": t.vendor_registration_number,
                    "vendor_name": t.vendor_name,
                    "is_verified": t.is_verified,
                    "is_blacklisted": t.is_blacklisted,
                    "consistency_count": t.consistency_count,
                    "self_healing_attempts": t.self_healing_attempts,
                    "last_healing_at": t.last_healing_at.isoformat() if t.last_healing_at else None,
                    "associated_users": usernames,
                }
            )

        return Response({"count": len(results), "results": results}, status=status.HTTP_200_OK)


class AdminTemplateHistoryView(APIView):
    """
    [T007] AdminTemplateHistoryView
    - 특정 템플릿의 실행 이력 및 자가치유 로그 조회
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, template_id, *args, **kwargs):
        # 템플릿 존재 검증
        get_object_or_404(MerchantTemplate, id=template_id)

        histories = TemplateExecutionHistory.objects.filter(template_id=template_id).order_by("-execution_time")
        results = []
        for h in histories:
            results.append(
                {
                    "id": str(h.id),
                    "ledger_id": str(h.ledger_id) if h.ledger_id else None,
                    "execution_time": h.execution_time.isoformat(),
                    "parsing_mode": h.parsing_mode,
                    "is_success": h.is_success,
                    "user_corrected": h.user_corrected,
                    "corrected_diff": h.corrected_diff,
                    "error_message": h.error_message,
                }
            )

        return Response({"template_id": str(template_id), "history": results}, status=status.HTTP_200_OK)


class AdminTemplateResetHealingView(APIView):
    """
    [T007] AdminTemplateResetHealingView
    - 자가 치유 횟수 초기화 및 블랙리스트 해제
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, template_id, *args, **kwargs):
        template = get_object_or_404(MerchantTemplate, id=template_id)
        template.is_blacklisted = False
        template.is_verified = False
        template.self_healing_attempts = 0
        template.save()

        return Response(
            {
                "status": "success",
                "message": "Self-healing counter has been reset. Template is ready for auto-promotion loop.",
                "template": {
                    "id": str(template.id),
                    "is_verified": template.is_verified,
                    "is_blacklisted": template.is_blacklisted,
                    "self_healing_attempts": template.self_healing_attempts,
                },
            },
            status=status.HTTP_200_OK,
        )
