from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from djoser.views import UserViewSet
from core.throttling import AuthLoginThrottle, AuthRegisterThrottle


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [AuthLoginThrottle]


class ThrottledRegisterView(APIView):
    throttle_classes = [AuthRegisterThrottle]

    def post(self, request: Request, *args, **kwargs) -> Response:
        # Delegate to Djoser's UserViewSet create action
        view = UserViewSet.as_view({"post": "create"})
        # Pass the underlying HttpRequest object
        return view(request._request, *args, **kwargs)
