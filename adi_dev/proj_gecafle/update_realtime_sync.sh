#!/bin/bash

# Script pour mettre à jour le module adi_gecafle_realtime_sync
# Version simplifiée - sans bus, sans notifications

echo "======================================================"
echo "Mise à jour du module adi_gecafle_realtime_sync"
echo "Version: Polling simple et fiable"
echo "======================================================"

# Couleurs pour le terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ODOO_PATH="/home/stadev/odoo17-dev/odoo-bin"
ADDONS_PATH="/home/stadev/odoo17-dev/adi_dev/proj_gecafle"
DB_NAME="adi_odoo17"
DB_USER="stadev"
DB_PASSWORD="St@dev"
MODULE_NAME="adi_gecafle_realtime_sync"

echo -e "${YELLOW}1. Arrêt des processus Odoo en cours...${NC}"
pkill -f odoo-bin
sleep 2

echo -e "${YELLOW}2. Vérification de l'installation du module...${NC}"
# Vérifier si le module est installé
INSTALLED=$(PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -t -c "SELECT state FROM ir_module_module WHERE name='$MODULE_NAME';")

if [ -z "$INSTALLED" ] || [ "$INSTALLED" = " uninstalled" ]; then
    echo -e "${GREEN}Installation du module $MODULE_NAME...${NC}"
    python3 $ODOO_PATH -c /etc/odoo/odoo17.conf -d $DB_NAME -i $MODULE_NAME --stop-after-init
else
    echo -e "${GREEN}Mise à jour du module $MODULE_NAME...${NC}"
    python3 $ODOO_PATH -c /etc/odoo/odoo17.conf -d $DB_NAME -u $MODULE_NAME --stop-after-init
fi

echo -e "${YELLOW}3. Nettoyage du cache des assets...${NC}"
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -c "DELETE FROM ir_attachment WHERE name LIKE 'web.assets%';"

echo -e "${YELLOW}4. Initialisation du timestamp de synchronisation...${NC}"
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -c "DELETE FROM ir_config_parameter WHERE key = 'gecafle.reception.last_change';"

echo -e "${GREEN}======================================================"
echo -e "Mise à jour terminée avec succès!"
echo -e "======================================================${NC}"
echo ""
echo -e "${YELLOW}Pour démarrer Odoo:${NC}"
echo -e "${GREEN}python3 /home/stadev/odoo17-dev/odoo-bin -c /etc/odoo/odoo17.conf${NC}"
echo ""
echo -e "${YELLOW}Comment ça fonctionne:${NC}"
echo "- Le système vérifie toutes les 3 secondes si des réceptions ont changé"
echo "- Les vues se rafraîchissent SILENCIEUSEMENT (sans notification)"
echo "- Le polling s'arrête quand la fenêtre est cachée (optimisation)"
echo ""
echo -e "${YELLOW}Pour tester:${NC}"
echo "1. Ouvrez deux onglets dans votre navigateur"
echo "2. Onglet 1: Ouvrez une vente (liste ou formulaire)"
echo "3. Onglet 2: Créez une nouvelle réception"
echo "4. Onglet 1: Attendez max 3 secondes - la vue se rafraîchit automatiquement!"
echo "5. Vérifiez la console (F12): [GeCaFle Sync] Changement détecté!"
echo ""
