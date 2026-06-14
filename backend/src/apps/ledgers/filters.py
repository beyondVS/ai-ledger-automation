from django_filters import rest_framework as filters

from .models import Ledger


class LedgerFilter(filters.FilterSet):
    q = filters.CharFilter(field_name="vendor_name", lookup_expr="icontains")
    categories = filters.CharFilter(method="filter_categories")
    start_date = filters.CharFilter(method="filter_start_date")
    end_date = filters.CharFilter(method="filter_end_date")
    min_amount = filters.NumberFilter(field_name="total_amount", lookup_expr="gte")
    max_amount = filters.NumberFilter(field_name="total_amount", lookup_expr="lte")

    class Meta:
        model = Ledger
        fields = ["q", "categories", "start_date", "end_date", "min_amount", "max_amount"]

    def filter_categories(self, queryset, name, value):
        if not value:
            return queryset
        # 쉼표로 구분된 카테고리 명칭을 추출하여 IN 쿼리 수행 (예: "식비,쇼핑" -> ["식비", "쇼핑"])
        category_list = [c.strip() for c in value.split(",") if c.strip()]
        return queryset.filter(category__in=category_list)

    def filter_start_date(self, queryset, name, value):
        if not value:
            return queryset
        import datetime
        import zoneinfo

        from django.conf import settings
        from django.utils import timezone

        try:
            # value: "YYYY-MM-DD"
            date_val = datetime.datetime.strptime(value, "%Y-%m-%d").date()
            local_dt = datetime.datetime.combine(date_val, datetime.time.min)

            request = self.request
            tzname = None
            if request and request.user and request.user.is_authenticated:
                tzname = getattr(request.user, "timezone", None)

            tz = zoneinfo.ZoneInfo(tzname or settings.TIME_ZONE)
            dt_aware = timezone.make_aware(local_dt, tz)
            return queryset.filter(transaction_date__gte=dt_aware)
        except (ValueError, TypeError):
            return queryset

    def filter_end_date(self, queryset, name, value):
        if not value:
            return queryset
        import datetime
        import zoneinfo

        from django.conf import settings
        from django.utils import timezone

        try:
            # value: "YYYY-MM-DD"
            date_val = datetime.datetime.strptime(value, "%Y-%m-%d").date()
            local_dt = datetime.datetime.combine(date_val, datetime.time.max)

            request = self.request
            tzname = None
            if request and request.user and request.user.is_authenticated:
                tzname = getattr(request.user, "timezone", None)

            tz = zoneinfo.ZoneInfo(tzname or settings.TIME_ZONE)
            dt_aware = timezone.make_aware(local_dt, tz)
            return queryset.filter(transaction_date__lte=dt_aware)
        except (ValueError, TypeError):
            return queryset
