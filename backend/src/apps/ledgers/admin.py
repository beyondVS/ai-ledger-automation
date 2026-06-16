from apps.ledgers.models import Ledger, LedgerItem, MerchantTemplate
from django.contrib import admin


class LedgerItemInline(admin.TabularInline):
    """
    1:N 관계를 어드민 상에서 일체형으로 통합 관리하기 위한 인라인 설정
    """

    model = LedgerItem
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Ledger)
class LedgerAdmin(admin.ModelAdmin):
    """
    Ledger 모델 어드민 커스텀 설정
    """

    list_display = ("id", "user", "vendor_name", "total_amount", "transaction_date", "created_at")
    search_fields = ("vendor_name", "vendor_registration_number", "user__email")
    ordering = ("-transaction_date",)
    inlines = [LedgerItemInline]


@admin.register(MerchantTemplate)
class MerchantTemplateAdmin(admin.ModelAdmin):
    """
    MerchantTemplate 모델 어드민 커스텀 설정
    """

    list_display = ("id", "vendor_registration_number", "vendor_name", "is_verified", "created_at")
    list_filter = ("is_verified",)
    search_fields = ("vendor_name", "vendor_registration_number")
    ordering = ("-created_at",)


@admin.register(LedgerItem)
class LedgerItemAdmin(admin.ModelAdmin):
    """
    LedgerItem 모델 어드민 단독 관리 설정
    """

    list_display = ("id", "ledger", "item_name", "quantity", "unit_price", "total_price", "created_at")
    search_fields = ("item_name", "ledger__vendor_name")
    ordering = ("-created_at",)
