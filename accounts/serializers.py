from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password], style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password_confirm', 'role')
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'date_joined', 'updated_at')
        read_only_fields = ('id', 'role', 'date_joined', 'updated_at')

class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management — can view and change role/is_active"""
    total_quizzes_created = serializers.SerializerMethodField()
    total_attempts = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'role', 'is_active',
            'date_joined', 'updated_at', 'total_quizzes_created', 'total_attempts'
        )
        read_only_fields = ('id', 'username', 'email', 'date_joined', 'updated_at',
                            'total_quizzes_created', 'total_attempts')

    def get_total_quizzes_created(self, obj):
        return obj.created_quizzes.count()

    def get_total_attempts(self, obj):
        return obj.quiz_attempts.count()
