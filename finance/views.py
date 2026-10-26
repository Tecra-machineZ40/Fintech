import csv
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from finance.models import GatewayAuditLog, Transaction
from finance.serializers import TransactionSerializer
# Create your views here.
from rest_framework_simplejwt.views import TokenObtainPairView
from finance.serializers import CustomTokenObtainPairSerializer
import random

CURRENCY_RATES_XAF = {
    'XAF': Decimal('1'),
    'EUR': Decimal('655.957'),
    'USD': Decimal('600'),
    'BTC': Decimal('39000000'),
    'ETH': Decimal('2100000'),
}


def enterprise_for_user(user):
    try:
        return user.profile.enterprise
    except Exception:
        return None


def convert_amount(amount, source_currency, target_currency):
    return (amount * CURRENCY_RATES_XAF[source_currency] / CURRENCY_RATES_XAF[target_currency]).quantize(Decimal('0.00000001'))


def transaction_filters(request, enterprise):
    transactions = Transaction.objects.filter(enterprise=enterprise)
    gateway = request.query_params.get('gateway')
    paid = request.query_params.get('is_paid')
    if gateway:
        transactions = transactions.filter(gateway=gateway)
    if paid in ('true', 'false'):
        transactions = transactions.filter(is_paid=(paid == 'true'))
    return transactions


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
class DashboardDataView(APIView):
    # Sécurité : Seul un utilisateur connecté avec un token JWT valide peut appeler cette API
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        enterprise = enterprise_for_user(user)
        if enterprise is None:
            return Response({"error": "Unauthorized profile configuration."}, status=status.HTTP_403_FORBIDDEN)
        user_role = user.profile.role

        target_currency = request.query_params.get('currency', 'XAF').upper()
        if target_currency not in CURRENCY_RATES_XAF:
            return Response({"error": "Unsupported currency."}, status=status.HTTP_400_BAD_REQUEST)
        transactions = transaction_filters(request, enterprise).order_by('-created_at')

        serializer = TransactionSerializer(transactions, many=True)
        transaction_rows = []
        for transaction, row in zip(transactions, serializer.data):
            transaction_rows.append({
                **row,
                'converted_amount': str(convert_amount(transaction.amount, transaction.currency, target_currency)),
                'display_currency': target_currency,
            })

        gateways = [choice[0] for choice in Transaction.PAYMENT_GATEWAYS]
        chart_data = {}
        for g in gateways:
            paid_transactions = Transaction.objects.filter(enterprise=enterprise, gateway=g, is_paid=True)
            chart_data[g] = float(sum(
                (convert_amount(tx.amount, tx.currency, target_currency) for tx in paid_transactions),
                Decimal('0'),
            ))

        total_revenue = sum((Decimal(str(value)) for value in chart_data.values()), Decimal('0'))
        audit_logs = GatewayAuditLog.objects.filter(enterprise=enterprise)[:10]
        recent_failures = Transaction.objects.filter(
            enterprise=enterprise,
            is_paid=False,
            created_at__gte=timezone.now() - timedelta(hours=24),
        )
        failure_alerts = []
        for email in recent_failures.values_list('customer_email', flat=True).distinct():
            count = recent_failures.filter(customer_email=email).count()
            if count >= 3:
                failure_alerts.append({'type': 'repeated_email_failures', 'identifier': email, 'attempts': count})
        for address in recent_failures.exclude(delivery_address='').values_list('delivery_address', flat=True).distinct():
            count = recent_failures.filter(delivery_address=address).count()
            if count >= 3:
                failure_alerts.append({'type': 'repeated_address_failures', 'identifier': address, 'attempts': count})

        return Response({
            "enterprise_name": enterprise.name,
            "user_role": user_role,
            "currency": target_currency,
            "rates_to_xaf": {currency: str(rate) for currency, rate in CURRENCY_RATES_XAF.items()},
            "metrics": {
                "total_revenue": float(total_revenue),
                "transactions_count": transactions.count(),
            },
            "chart_distribution": chart_data,
            "transactions_list": transaction_rows,
            "audit_logs": [{
                'id': log.id,
                'gateway': log.gateway,
                'event_type': log.event_type,
                'response_status': log.response_status,
                'error_message': log.error_message,
                'created_at': log.created_at,
            } for log in audit_logs],
            "fraud_alerts": failure_alerts,
        }, status=status.HTTP_200_OK)

class GatewayAuditView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enterprise = enterprise_for_user(request.user)
        if enterprise is None:
            return Response({"error": "Unauthorized profile configuration."}, status=status.HTTP_403_FORBIDDEN)
        logs = GatewayAuditLog.objects.filter(enterprise=enterprise)
        gateway = request.query_params.get('gateway')
        if gateway:
            logs = logs.filter(gateway=gateway)
        return Response([{
            'id': log.id,
            'gateway': log.gateway,
            'event_type': log.event_type,
            'request_payload': log.request_payload,
            'response_status': log.response_status,
            'response_payload': log.response_payload,
            'error_message': log.error_message,
            'created_at': log.created_at,
        } for log in logs[:100]])

    def post(self, request):
        enterprise = enterprise_for_user(request.user)
        if enterprise is None:
            return Response({"error": "Unauthorized profile configuration."}, status=status.HTTP_403_FORBIDDEN)
        gateway = request.data.get('gateway')
        event_type = request.data.get('event_type')
        if gateway not in dict(Transaction.PAYMENT_GATEWAYS) or not event_type:
            return Response({"error": "A valid gateway and event_type are required."}, status=status.HTTP_400_BAD_REQUEST)

        transaction = None
        transaction_id = request.data.get('transaction_id')
        if transaction_id:
            transaction = Transaction.objects.filter(enterprise=enterprise, transaction_id=transaction_id).first()
            if transaction is None:
                return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)

        log = GatewayAuditLog.objects.create(
            enterprise=enterprise,
            transaction=transaction,
            gateway=gateway,
            event_type=str(event_type)[:50],
            request_payload=request.data.get('request_payload') or {},
            response_status=request.data.get('response_status'),
            response_payload=request.data.get('response_payload') or {},
            error_message=request.data.get('error_message', ''),
        )
        return Response({'id': log.id, 'created_at': log.created_at}, status=status.HTTP_201_CREATED)


class ExchangeRatesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'base': 'XAF',
            'rates_to_xaf': {currency: str(rate) for currency, rate in CURRENCY_RATES_XAF.items()},
            'source': 'demo rates; configure a provider for live exchange data',
        })


class TransactionExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enterprise = enterprise_for_user(request.user)
        if enterprise is None:
            return Response({"error": "Unauthorized profile configuration."}, status=status.HTTP_403_FORBIDDEN)
        try:
            tax_rate = Decimal(request.query_params.get('tax_rate', '19.25'))
            if not tax_rate.is_finite() or tax_rate < 0 or tax_rate > 100:
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            return Response({"error": "tax_rate must be between 0 and 100."}, status=status.HTTP_400_BAD_REQUEST)

        transactions = transaction_filters(request, enterprise).order_by('-created_at')
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response.write('\ufeff')
        response['Content-Disposition'] = 'attachment; filename="transactions_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Transaction ID', 'Date UTC', 'Customer Email', 'Gateway', 'Status', 'Amount', 'Currency', 'VAT Rate (%)', 'VAT Amount', 'Total With VAT'])
        for transaction in transactions:
            tax_amount = (transaction.amount * tax_rate / Decimal('100')).quantize(Decimal('0.01'))
            amount_quantum = Decimal('0.00000001') if transaction.currency in ('BTC', 'ETH') else Decimal('0.01')
            safe_email = transaction.customer_email
            if safe_email.startswith(('=', '+', '-', '@')):
                safe_email = "'" + safe_email
            writer.writerow([
                transaction.transaction_id,
                transaction.created_at.isoformat(),
                safe_email,
                transaction.gateway,
                'PAID' if transaction.is_paid else 'PENDING',
                transaction.amount.quantize(amount_quantum),
                transaction.currency,
                tax_rate,
                tax_amount,
                (transaction.amount + tax_amount).quantize(amount_quantum),
            ])
        return response


class PaymentInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        enterprise = enterprise_for_user(request.user)
        if enterprise is None:
            return Response({"error": "Unauthorized profile configuration."}, status=status.HTTP_403_FORBIDDEN)
        gateway = request.data.get('gateway')
        currency = request.data.get('currency', 'XAF').upper()
        if gateway not in dict(Transaction.PAYMENT_GATEWAYS):
            return Response({"error": "Unsupported payment method."}, status=status.HTTP_400_BAD_REQUEST)
        if currency not in CURRENCY_RATES_XAF:
            return Response({"error": "Unsupported currency."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(request.data.get('amount', '')))
            if not amount.is_finite() or amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            return Response({"error": "A positive amount is required."}, status=status.HTTP_400_BAD_REQUEST)

        transaction = Transaction.objects.create(
            enterprise=enterprise,
            amount=amount,
            currency=currency,
            gateway=gateway,
            transaction_id=f"demo_{uuid.uuid4().hex[:24]}",
            customer_email=request.data.get('customer_email') or request.user.email or 'client@enterprise.com',
            delivery_address=request.data.get('delivery_address', ''),
            is_paid=False,
        )
        payment_details = {}
        if gateway in ('CRYPTO_BTC', 'CRYPTO_ETH'):
            crypto_currency = 'BTC' if gateway == 'CRYPTO_BTC' else 'ETH'
            crypto_amount = convert_amount(amount, currency, crypto_currency)
            payment_address = f"1{uuid.uuid4().hex[:33]}" if crypto_currency == 'BTC' else f"0x{uuid.uuid4().hex[:40]}"
            payment_details = {
                'crypto_amount': str(crypto_amount),
                'payment_address': payment_address,
                'crypto_currency': crypto_currency,
            }
        GatewayAuditLog.objects.create(
            enterprise=enterprise,
            transaction=transaction,
            gateway=gateway,
            event_type='invoice.created',
            request_payload={'amount': str(amount), 'currency': currency},
            response_status=202,
            response_payload={'transaction_id': transaction.transaction_id, 'simulated': True, **payment_details},
        )
        instructions = {
            'BANK_TRANSFER': 'Use the transaction ID as your transfer reference.',
            'MOBILE_MONEY': 'Confirm the payment on your mobile money device.',
            'STRIPE': 'Complete the test card checkout with your configured provider.',
            'PAYPAL': 'Complete the test checkout with your configured provider.',
        }.get(gateway, 'Follow the payment instructions from your selected provider.')
        return Response({
            'transaction_id': transaction.transaction_id,
            'amount': str(transaction.amount),
            'currency': transaction.currency,
            'gateway': transaction.gateway,
            'instructions': instructions,
            'simulated': True,
            **payment_details,
        }, status=status.HTTP_201_CREATED)


class PaymentConfirmationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        enterprise = enterprise_for_user(request.user)
        transaction = Transaction.objects.filter(
            enterprise=enterprise,
            transaction_id=request.data.get('transaction_id'),
        ).first() if enterprise else None
        if transaction is None:
            return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)
        transaction.is_paid = True
        transaction.save(update_fields=['is_paid'])
        GatewayAuditLog.objects.create(
            enterprise=enterprise,
            transaction=transaction,
            gateway=transaction.gateway,
            event_type='payment.confirmed',
            request_payload={'transaction_id': transaction.transaction_id},
            response_status=200,
            response_payload={'is_paid': True, 'simulated': True},
        )
        return Response({'transaction_id': transaction.transaction_id, 'is_paid': True, 'simulated': True})


class CryptoInvoiceGatewayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount_usd = request.data.get('amount_usd')
        crypto_type = request.data.get('crypto_type', 'BTC') # BTC ou ETH

        if not amount_usd:
            return Response({"error": "Amount in USD is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Simulation des taux du marché en 2026 (Prix fictifs stables pour la démo)
        btc_price = 65000.00
        eth_price = 3500.00
        
        rate = btc_price if crypto_type == 'BTC' else eth_price
        crypto_amount = float(amount_usd) / rate

        # Génération d'une fausse adresse de portefeuille publique pour le test
        mock_wallet = f"1{"".join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=33))}" if crypto_type == 'BTC' else f"0x{"".join(random.choices('abcdef0123456789', k=40))}"

        return Response({
            "status": "pending",
            "amount_usd": float(amount_usd),
            "crypto_type": crypto_type,
            "crypto_amount": round(crypto_amount, 6),
            "payment_address": mock_wallet,
            "qr_code_mock": f"https://qrserver.com{mock_wallet}"
        }, status=status.HTTP_200_OK)
