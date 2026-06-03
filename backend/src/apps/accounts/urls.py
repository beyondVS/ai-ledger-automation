from django.urls import path

from .views import UserLoginView, UserLogoutView, UserRegisterView, UserTokenRefreshView

urlpatterns = [
    path("register/", UserRegisterView.as_view(), name="user-register"),
    path("login/", UserLoginView.as_view(), name="user-login"),
    path("logout/", UserLogoutView.as_view(), name="user-logout"),
    path("refresh/", UserTokenRefreshView.as_view(), name="token-refresh"),
]
