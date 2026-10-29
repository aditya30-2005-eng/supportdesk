from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "full_name", "role"]
        read_only_fields = fields

    def get_full_name(self, user) -> str:
        return user.get_full_name() or user.username


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs):
        candidate = User(username=attrs.get("username"), email=attrs.get("email"))
        validate_password(attrs["password"], user=candidate)
        return attrs

    def create(self, validated_data):
        # Public sign-up always creates a customer. Agents and admins are made by an admin.
        return User.objects.create_user(role=User.Role.CUSTOMER, **validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class AdminUserSerializer(UserSerializer):
    """Used by admins to manage accounts. Only role and active state can change."""

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["is_active", "date_joined"]
        read_only_fields = [f for f in UserSerializer.Meta.fields + ["date_joined"] if f != "role"]
