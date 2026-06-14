import django.contrib.postgres.indexes
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ledgers", "0009_monthlybudget"),
    ]

    operations = [
        # pg_trgm extension 활성화 (GIN Trigram 인덱스에 필수)
        TrigramExtension(),
        # 1. (user_id, transaction_date DESC) 시계열 복합 인덱스 추가
        migrations.AddIndex(
            model_name="ledger",
            index=models.Index(fields=["user", "-transaction_date"], name="ledger_user_date_idx"),
        ),
        # 2. vendor_name Trigram GIN 인덱스 추가 (상호명 부분 일치 icontains 초고속 검색 튜닝)
        migrations.AddIndex(
            model_name="ledger",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["vendor_name"], name="ledger_vendor_trgm_idx", opclasses=["gin_trgm_ops"]
            ),
        ),
    ]
