from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from finance.models import Transaction

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)  


        # Injection des données d'entreprise et de rôle dans le jeton crypté
        try:
            profile = user.profile
            token['role'] = profile.role
            token['enterprise_name'] = profile.enterprise.name
        except Exception:
            token['role'] = 'GUEST'
            token['enterprise_name'] = 'Demo Enterprise'

        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Ajout des données en clair dans la réponse JSON finale pour le Frontend React
        try:
            profile = self.user.profile
            data['user_info'] = {
                'username': self.user.username,
                'role': profile.role,
                'enterprise': profile.enterprise.name
            }
        except Exception:
            data['user_info'] = {
                'username': self.user.username,
                'role': 'GUEST',
                'enterprise': 'Demo Enterprise'
            }
        return data

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'currency', 'gateway', 'transaction_id', 'customer_email', 'delivery_address', 'crypto_address', 'is_paid', 'created_at']
