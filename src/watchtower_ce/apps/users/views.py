from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import serializers


class UserViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = User.objects.all()
    serializer_class: type[Serializer] = serializers.UserSerializer


class HybridTokenObtainPairView(TokenObtainPairView):
    """
    Standard login view that returns the access token in JSON
    but hides the refresh token in an httpOnly cookie.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            refresh_token = response.data.pop("refresh")
            cookie_settings = settings.SIMPLE_JWT

            response.set_cookie(
                key=cookie_settings["AUTH_COOKIE_REFRESH"],
                value=refresh_token,
                max_age=int(cookie_settings["REFRESH_TOKEN_LIFETIME"].total_seconds()),
                secure=cookie_settings["AUTH_COOKIE_SECURE"],
                httponly=cookie_settings["AUTH_COOKIE_HTTP_ONLY"],
                samesite=cookie_settings["AUTH_COOKIE_SAMESITE"],
                path=cookie_settings["AUTH_COOKIE_PATH"],
            )
        return response


class HybridTokenRefreshView(TokenRefreshView):
    """
    Standard refresh view that looks for the refresh token in a cookie
    instead of the JSON body.
    """

    def post(self, request, *args, **kwargs):
        cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"]
        refresh_token = request.COOKIES.get(cookie_name)

        if refresh_token:
            # Manually inject the token into the request data for the serializer
            data = request.data.copy()
            data["refresh"] = refresh_token
            serializer = self.get_serializer(data=data)

            try:
                serializer.is_valid(raise_exception=True)
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

            response = Response(serializer.validated_data, status=status.HTTP_200_OK)

            # If rotation is on, update the cookie with the new refresh token
            if settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]:
                new_refresh = serializer.validated_data.get("refresh")
                if new_refresh:
                    cookie_settings = settings.SIMPLE_JWT
                    response.set_cookie(
                        key=cookie_name,
                        value=new_refresh,
                        max_age=int(
                            cookie_settings["REFRESH_TOKEN_LIFETIME"].total_seconds()
                        ),
                        secure=cookie_settings["AUTH_COOKIE_SECURE"],
                        httponly=cookie_settings["AUTH_COOKIE_HTTP_ONLY"],
                        samesite=cookie_settings["AUTH_COOKIE_SAMESITE"],
                        path=cookie_settings["AUTH_COOKIE_PATH"],
                    )
            return response
        return Response(
            {"detail": "Refresh token not found in cookies."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
