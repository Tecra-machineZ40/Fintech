import csv
from io import StringIO

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from finance.models import EnterpriseProfile, GatewayAuditLog, Transaction, UserProfile


class FinanceApiTests(TestCase):
	def setUp(self):
		self.enterprise = EnterpriseProfile.objects.create(name='Test Enterprise')
		self.user = User.objects.create_user(username='finance-user', password='test-pass')
		UserProfile.objects.create(user=self.user, enterprise=self.enterprise, role='MANAGER')
		self.client = APIClient()
		self.client.force_authenticate(self.user)

	def create_transaction(self, **overrides):
		values = {
			'enterprise': self.enterprise,
			'amount': '100.00',
			'currency': 'XAF',
			'gateway': 'STRIPE',
			'transaction_id': f'tx-{Transaction.objects.count()}',
			'customer_email': 'client@example.com',
			'is_paid': True,
		}
		values.update(overrides)
		return Transaction.objects.create(**values)

	def test_dashboard_converts_amounts_and_isolates_enterprises(self):
		self.create_transaction(amount='10.00', currency='USD')
		other_enterprise = EnterpriseProfile.objects.create(name='Other Enterprise')
		Transaction.objects.create(
			enterprise=other_enterprise,
			amount='9999.00',
			currency='XAF',
			gateway='PAYPAL',
			transaction_id='other-enterprise-tx',
		)

		response = self.client.get('/api/dashboard/metrics/?currency=XAF')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['metrics']['total_revenue'], 6000.0)
		self.assertEqual(response.data['transactions_list'][0]['converted_amount'], '6000.00000000')
		self.assertEqual(response.data['metrics']['transactions_count'], 1)

	def test_dashboard_reports_repeated_failed_email_and_address(self):
		for index in range(3):
			self.create_transaction(
				transaction_id=f'failed-{index}',
				customer_email='suspicious@example.com',
				delivery_address='Repeated delivery address',
				is_paid=False,
			)

		response = self.client.get('/api/dashboard/metrics/')

		alert_types = {alert['type'] for alert in response.data['fraud_alerts']}
		self.assertEqual(alert_types, {'repeated_email_failures', 'repeated_address_failures'})

	def test_audit_log_keeps_gateway_error_details(self):
		transaction = self.create_transaction(transaction_id='stripe-failed')

		response = self.client.post('/api/audit-logs/', {
			'gateway': 'STRIPE',
			'event_type': 'payment.failed',
			'transaction_id': transaction.transaction_id,
			'response_status': 402,
			'response_payload': {'code': 'card_declined'},
			'error_message': 'The card was declined.',
		}, format='json')

		self.assertEqual(response.status_code, 201)
		log = GatewayAuditLog.objects.get(pk=response.data['id'])
		self.assertEqual(log.error_message, 'The card was declined.')
		self.assertEqual(log.transaction, transaction)

	def test_csv_export_applies_vat_and_gateway_filter(self):
		self.create_transaction(amount='10000.00', gateway='BANK_TRANSFER', transaction_id='bank-tx')
		self.create_transaction(amount='400.00', gateway='PAYPAL', transaction_id='paypal-tx')

		response = self.client.get('/api/transactions/export/?gateway=BANK_TRANSFER&tax_rate=19.25')

		self.assertEqual(response.status_code, 200)
		rows = list(csv.DictReader(StringIO(response.content.decode('utf-8-sig'))))
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]['VAT Amount'], '1925.00')
		self.assertEqual(rows[0]['Total With VAT'], '11925.00')

	def test_invoice_can_use_mobile_money_and_confirmation_is_audited(self):
		invoice = self.client.post('/api/payments/invoice/', {
			'amount': '25000',
			'currency': 'XAF',
			'gateway': 'MOBILE_MONEY',
		}, format='json')

		self.assertEqual(invoice.status_code, 201)
		self.assertEqual(invoice.data['gateway'], 'MOBILE_MONEY')
		confirmation = self.client.post('/api/payments/confirm/', {
			'transaction_id': invoice.data['transaction_id'],
		}, format='json')

		self.assertEqual(confirmation.status_code, 200)
		self.assertTrue(Transaction.objects.get(transaction_id=invoice.data['transaction_id']).is_paid)
		self.assertEqual(GatewayAuditLog.objects.filter(transaction__transaction_id=invoice.data['transaction_id']).count(), 2)
