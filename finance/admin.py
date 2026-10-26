from django.contrib import admin
from finance.models import EnterpriseProfile, GatewayAuditLog, Transaction, UserProfile

admin.site.register((EnterpriseProfile, UserProfile, Transaction, GatewayAuditLog))
