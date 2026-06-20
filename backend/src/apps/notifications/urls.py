from apps.notifications.views import UserPushSubscriptionViewSet, VapidPublicKeyView
from django.urls import include, path
from rest_framework.routers import DefaultRouter

app_name = "notifications"

router = DefaultRouter()
router.register("subscriptions", UserPushSubscriptionViewSet, basename="subscription")

urlpatterns = [
    path("vapid-public-key/", VapidPublicKeyView.as_view(), name="vapid-public-key"),
    path("", include(router.urls)),
]
