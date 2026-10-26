# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class EnterpriseProfile(models.Model):
    # Permet de gérer le "Multi-Tenant" (chaque entreprise a ses propres données)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    # Associe un utilisateur Django à un rôle strict pour l'entreprise
    ROLE_CHOICES = [
        ('MANAGER', 'Financial Manager'),
        ('ACCOUNTANT', 'Accountant'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    enterprise = models.ForeignKey(EnterpriseProfile, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ACCOUNTANT')

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Transaction(models.Model):
    # Liste exhaustive des canaux de paiement d'entreprise
    PAYMENT_GATEWAYS = [
        ('STRIPE', 'Stripe Processing'),
        ('PAYPAL', 'PayPal Commerce'),
        ('PAYONEER', 'Payoneer Business'),
        ('CREDIT_CARD', 'Direct Credit Card (Visa/MC)'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('OTHER', 'Other Payment Method'),
        ('CRYPTO_BTC', 'Cryptocurrency (Bitcoin)'),
        ('CRYPTO_ETH', 'Cryptocurrency (Ethereum)'),
    ]
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('XAF', 'Central African CFA Franc'),
        ('BTC', 'Bitcoin'),
        ('ETH', 'Ethereum'),
    ]
    
    enterprise = models.ForeignKey(EnterpriseProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    gateway = models.CharField(max_length=20, choices=PAYMENT_GATEWAYS, default='STRIPE')
    
    # Champs spécifiques pour tracer les transactions
    transaction_id = models.CharField(max_length=100, unique=True, help_text="ID simulé de l'API (ch_..., pay_...)")
    customer_email = models.EmailField(default="client@enterprise.com")
    delivery_address = models.CharField(max_length=500, blank=True)
    
    # Pour la partie Crypto
    crypto_address = models.CharField(max_length=100, blank=True, null=True)
    
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gateway} - {self.amount} {self.currency} ({'Paid' if self.is_paid else 'Pending'})"


class GatewayAuditLog(models.Model):
    enterprise = models.ForeignKey(EnterpriseProfile, on_delete=models.CASCADE, related_name='gateway_audit_logs')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    gateway = models.CharField(max_length=20, choices=Transaction.PAYMENT_GATEWAYS)
    event_type = models.CharField(max_length=50)
    request_payload = models.JSONField(default=dict, blank=True)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.gateway} {self.event_type} ({self.response_status or 'no response'})"
