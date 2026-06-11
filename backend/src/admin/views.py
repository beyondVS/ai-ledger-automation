from apps.ledgers.models import MerchantTemplate
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class MerchantTemplateVerifyView(APIView):
    """
    [T019] MerchantTemplateVerifyView
    - 제안된 템플릿(is_verified: False)을 승인(is_verified: True)하여
      정적 우회(Bypass) 파싱 대상으로 등록합니다.
    """

    def post(self, request, template_id, *args, **kwargs):
        template = get_object_or_404(MerchantTemplate, id=template_id)
        template.is_verified = True
        template.save()

        return Response(
            {
                "id": str(template.id),
                "vendor_registration_number": template.vendor_registration_number,
                "vendor_name": template.vendor_name,
                "is_verified": template.is_verified,
                "parsing_rules": template.parsing_rules,
            },
            status=status.HTTP_200_OK,
        )
