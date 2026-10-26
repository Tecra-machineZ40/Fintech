from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from finance.views import (
  CustomTokenObtainPairView,
  DashboardDataView,
  CryptoInvoiceGatewayView,
  ExchangeRatesView,
  GatewayAuditView,
  PaymentConfirmationView,
  PaymentInvoiceView,
  TransactionExportView,
)

urlpatterns = [
    # C'est cet endpoint que la page de Login Next.js va requêter
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

  # Données financières du Dashboard
    path('dashboard/metrics/', DashboardDataView.as_view(), name='dashboard_metrics'),
    path('crypto/invoice/', CryptoInvoiceGatewayView.as_view(), name='crypto_invoice'),
    path('exchange-rates/', ExchangeRatesView.as_view(), name='exchange_rates'),
    path('audit-logs/', GatewayAuditView.as_view(), name='audit_logs'),
    path('transactions/export/', TransactionExportView.as_view(), name='transactions_export'),
    path('payments/invoice/', PaymentInvoiceView.as_view(), name='payment_invoice'),
    path('payments/confirm/', PaymentConfirmationView.as_view(), name='payment_confirmation'),
  ]
