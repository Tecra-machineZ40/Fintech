import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='transaction',
            old_name='amount_usd',
            new_name='amount',
        ),
        migrations.AlterField(
            model_name='transaction',
            name='amount',
            field=models.DecimalField(decimal_places=8, max_digits=18),
        ),
        migrations.AddField(
            model_name='transaction',
            name='currency',
            field=models.CharField(choices=[('USD', 'US Dollar'), ('EUR', 'Euro'), ('XAF', 'Central African CFA Franc'), ('BTC', 'Bitcoin'), ('ETH', 'Ethereum')], default='USD', max_length=3),
        ),
        migrations.AddField(
            model_name='transaction',
            name='delivery_address',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='gateway',
            field=models.CharField(choices=[('STRIPE', 'Stripe Processing'), ('PAYPAL', 'PayPal Commerce'), ('PAYONEER', 'Payoneer Business'), ('CREDIT_CARD', 'Direct Credit Card (Visa/MC)'), ('BANK_TRANSFER', 'Bank Transfer'), ('MOBILE_MONEY', 'Mobile Money'), ('OTHER', 'Other Payment Method'), ('CRYPTO_BTC', 'Cryptocurrency (Bitcoin)'), ('CRYPTO_ETH', 'Cryptocurrency (Ethereum)')], default='STRIPE', max_length=20),
        ),
        migrations.CreateModel(
            name='GatewayAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gateway', models.CharField(choices=[('STRIPE', 'Stripe Processing'), ('PAYPAL', 'PayPal Commerce'), ('PAYONEER', 'Payoneer Business'), ('CREDIT_CARD', 'Direct Credit Card (Visa/MC)'), ('BANK_TRANSFER', 'Bank Transfer'), ('MOBILE_MONEY', 'Mobile Money'), ('OTHER', 'Other Payment Method'), ('CRYPTO_BTC', 'Cryptocurrency (Bitcoin)'), ('CRYPTO_ETH', 'Cryptocurrency (Ethereum)')], max_length=20)),
                ('event_type', models.CharField(max_length=50)),
                ('request_payload', models.JSONField(blank=True, default=dict)),
                ('response_status', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('response_payload', models.JSONField(blank=True, default=dict)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('enterprise', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gateway_audit_logs', to='finance.enterpriseprofile')),
                ('transaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='finance.transaction')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]