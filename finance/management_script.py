import os
import random
import uuid
from decimal import Decimal
from django.contrib.auth.models import User
from finance.models import EnterpriseProfile, UserProfile, Transaction

def generate_mock_data():
    print("🚀 Démarrage de la génération des données de test...")

    # 1. Création de l'entreprise fictive
    enterprise, _ = EnterpriseProfile.objects.get_or_create(name="Nexus Global Technologies")

    # 2. Création des utilisateurs avec différents rôles
    # Compte Financial Manager
    if not User.objects.filter(username="manager_demo").exists():
        user_mgr = User.objects.create_user(username="manager_demo", password="PasswordDemo2026")
        UserProfile.objects.create(user=user_mgr, enterprise=enterprise, role="MANAGER")
        print("✅ Utilisateur Manager créé : manager_demo / PasswordDemo2026")

    # Compte Comptable (Accountant)
    if not User.objects.filter(username="accountant_demo").exists():
        user_acct = User.objects.create_user(username="accountant_demo", password="PasswordDemo2026")
        UserProfile.objects.create(user=user_acct, enterprise=enterprise, role="ACCOUNTANT")
        print("✅ Utilisateur Accountant créé : accountant_demo / PasswordDemo2026")

    # 3. Création des 50 transactions simulées
    gateways = ['STRIPE', 'PAYPAL', 'PAYONEER', 'CREDIT_CARD', 'BANK_TRANSFER', 'MOBILE_MONEY', 'OTHER', 'CRYPTO_BTC', 'CRYPTO_ETH']
    currencies = ['USD', 'EUR', 'XAF', 'BTC', 'ETH']
    emails = ['customer1@gmail.com', 'b2b-client@techcorp.io', 'billing@startup.co', 'investor@nexus.com']
    
    # Nettoyage des anciennes transactions de test pour repartir à zéro
    Transaction.objects.filter(enterprise=enterprise).delete()

    for i in range(50):
        selected_gateway = random.choice(gateways)
        amount = Decimal(round(random.uniform(50.00, 4500.00), 2))
        currency = 'BTC' if selected_gateway == 'CRYPTO_BTC' else 'ETH' if selected_gateway == 'CRYPTO_ETH' else random.choice(currencies[:3])
        
        # Simulation d'un ID de transaction unique selon la passerelle
        if 'STRIPE' in selected_gateway:
            tx_id = f"ch_{uuid.uuid4().hex[:16]}"
        elif 'PAYPAL' in selected_gateway:
            tx_id = f"PAYID-{uuid.uuid4().hex[:12].upper()}"
        else:
            tx_id = f"tx_{uuid.uuid4().hex[:10]}"

        # Simulation d'une adresse de portefeuille pour la crypto
        crypto_addr = f"0x{uuid.uuid4().hex}" if "CRYPTO" in selected_gateway else None

        Transaction.objects.create(
            enterprise=enterprise,
            amount=amount,
            currency=currency,
            gateway=selected_gateway,
            transaction_id=tx_id,
            customer_email=random.choice(emails),
            crypto_address=crypto_addr,
            is_paid=random.choice([True, True, True, False]) # 75% de chances d'être payé
        )

    print(f"🎉 Succès ! 50 transactions simulées (Stripe, PayPal, Crypto) ont été injectées en base de données.")
