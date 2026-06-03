from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    """
    [T010] 회원가입 데이터 검증 및 유저 생성 직렬화기
    - 비밀번호 write_only 처리 및 create 시 create_user를 통한 해싱 적용
    """
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'provider', 'date_joined')
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True},
            'provider': {'read_only': True},
            'date_joined': {'read_only': True}
        }

    def validate_username(self, value):
        # 아이디 중복에 대한 보다 친화적인 유효성 에러
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("이미 가입된 아이디(username)입니다.")
        return value

    def create(self, validated_data):
        # UserManager.create_user를 통해 비밀번호 해싱 처리
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )


from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UserLoginSerializer(TokenObtainPairSerializer):
    """
    [T016] standard username/password 검증용 Serializer
    """
    pass
