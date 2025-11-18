#!/bin/bash

echo "=============================================="
echo "REDÉMARRAGE D'ODOO AVEC MISE À JOUR FORCÉE"
echo "=============================================="
echo ""

# Arrêter Odoo s'il tourne
echo "1️⃣ Arrêt d'Odoo..."
sudo systemctl stop odoo17 2>/dev/null
pkill -f odoo-bin 2>/dev/null
sleep 2

# Se placer dans le répertoire Odoo
cd /home/stadev/odoo17-dev

# Démarrer Odoo avec mise à jour forcée des modules
echo ""
echo "2️⃣ Démarrage d'Odoo avec mise à jour des modules..."
echo ""
echo "Commande exécutée :"
echo "./odoo-bin -c odoo17.conf -d o17_gecafle_final_base -u adi_gecafle_receptions,adi_gecafle_reception_extended --log-level=info"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter Odoo après la mise à jour"
echo ""
echo "📝 SURVEILLEZ LES LOGS POUR :"
echo "   - Module adi_gecafle_receptions: to upgrade"
echo "   - Module adi_gecafle_reception_extended: to upgrade"
echo "   - [PAYMENT SYNC] pour les messages de synchronisation"
echo ""
echo "=============================================="
echo ""

# Démarrer Odoo
./odoo-bin \
    -c odoo17.conf \
    -d o17_gecafle_final_base \
    -u adi_gecafle_receptions,adi_gecafle_reception_extended \
    --log-level=info 2>&1 | grep -E "(adi_gecafle|PAYMENT SYNC|WARNING|ERROR|module|upgrade|installing)"