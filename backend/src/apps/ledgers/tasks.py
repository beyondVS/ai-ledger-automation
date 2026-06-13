import logging

from django.contrib.auth import get_user_model

logger = logging.getLogger("apps.ledgers")
User = get_user_model()


# process_llm_fallback_task has been deprecated and removed.
# All receipt parsing and ingestion route through extract_receipt_text_task.
