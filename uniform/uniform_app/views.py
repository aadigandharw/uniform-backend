from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, LoginSerializer
from rest_framework.permissions import AllowAny , IsAuthenticated
from .models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404


# ✅ REGISTER
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({"msg": "User created"}, status=201)

        return Response(serializer.errors, status=400)


# ✅ LOGIN
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = User.objects.filter(email=email).first()

        if not user:
            return Response({"error": "User not found"}, status=400)

        # 🔥 APPROVAL CHECK
        if not user.is_active:
            return Response({"error": "Wait for admin approval"}, status=403)

        if not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=400)

        # ✅ JWT TOKEN
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Login successful",
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })
    

class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.all().order_by('-id')

        data = []
        for u in users:
            data.append({
                "id": u.id,
                "name": u.full_name,
                "email": u.email,
                "status": "present" if u.is_active else "absent",
                "role": "User",
                "dept": "App User",
                "phone": "N/A",
                "sal": 0,
                "join": "New",
                "jobs": 0
            })

        return Response(data)
    
class ApproveUserView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):

        if not request.user.is_staff:
            return Response(
                {"error": "Only admin can approve users"},
                status=403
            )

        user = get_object_or_404(User, id=id)

        user.is_active = True
        user.save()

        return Response({"msg": "User approved successfully"})

class UpdateUserView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):

        # 🔥 ONLY ADMIN EDIT
        if not request.user.is_staff:
            return Response(
                {"error": "Only admin can edit users"},
                status=403
            )

        user = get_object_or_404(User, id=id)

        user.full_name = request.data.get("name", user.full_name)
        user.save()

        return Response({"msg": "User updated successfully"})


# ✅ 🔥 ADD THIS NEW CLASS HERE (LAST ME)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "email": request.user.email,
            "full_name": request.user.full_name,
            "is_staff": request.user.is_staff,
            "is_active": request.user.is_active
        })