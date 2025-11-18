#!/bin/bash
# Script de mise à jour pour appliquer la correction de synchronisation des paiements

echo "=================================="
echo "MISE À JOUR - Synchronisation Paiements"
echo "=================================="

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Ce script va mettre à jour les modules Odoo pour corriger la synchronisation des paiements.${NC}"
echo ""
echo "Modules concernés:"
echo "  - adi_gecafle_receptions"
echo "  - adi_gecafle_reception_extended"
echo ""

# Demander la base de données
read -p "Nom de la base de données (ex: o17_gecafle_final_tests_f): " DB_NAME

if [ -z "$DB_NAME" ]; then
    echo -e "${RED}❌ Nom de base de données requis!${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Vérification de la base de données...${NC}"
PGPASSWORD='St@dev' psql -U stadev -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ La base de données '$DB_NAME' n'existe pas!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Base de données trouvée${NC}"
echo ""

# Chemin vers odoo-bin
ODOO_BIN="/home/stadev/odoo17-dev/odoo-bin"

if [ ! -f "$ODOO_BIN" ]; then
    echo -e "${RED}❌ odoo-bin non trouvé à: $ODOO_BIN${NC}"
    exit 1
fi

echo -e "${YELLOW}Mise à jour des modules...${NC}"
echo ""

# Mise à jour avec odoo-bin
$ODOO_BIN -d "$DB_NAME" \
    -u adi_gecafle_receptions,adi_gecafle_reception_extended \
    --stop-after-init \
    --no-http \
    --log-level=info

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ MISE À JOUR RÉUSSIE!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Les modifications suivantes ont été appliquées:"
    echo ""
    echo "1. Champ 'avance_producteur' converti en champ compute"
    echo "   → Se calcule automatiquement depuis les paiements validés"
    echo ""
    echo "2. Champ 'transport' converti en champ compute"
    echo "   → Se calcule automatiquement depuis les paiements de transport validés"
    echo ""
    echo "3. Champ 'paiement_emballage' converti en champ compute"
    echo "   → Se calcule automatiquement depuis les paiements d'emballage validés"
    echo ""
    echo -e "${YELLOW}Note importante:${NC}"
    echo "Les champs se mettront à jour automatiquement dès qu'un paiement sera validé."
    echo "Vous pouvez aussi forcer un recalcul en ouvrant et sauvegardant une réception."
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ ERREUR LORS DE LA MISE À JOUR${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Veuillez vérifier les logs ci-dessus pour plus de détails."
    echo ""
    exit 1
fi

# Proposer de recalculer les valeurs existantes
echo ""
read -p "Voulez-vous recalculer les montants pour toutes les réceptions existantes? (o/N): " RECALC

if [[ "$RECALC" =~ ^[oO]$ ]]; then
    echo ""
    echo -e "${YELLOW}Recalcul des montants...${NC}"

    $ODOO_BIN shell -d "$DB_NAME" --no-http --stop-after-init << 'EOFSHELL'
import logging
_logger = logging.getLogger(__name__)

_logger.info("Recalcul des montants de paiements...")

# Récupérer toutes les réceptions
receptions = env['gecafle.reception'].search([])
_logger.info(f"Nombre de réceptions trouvées: {len(receptions)}")

# Forcer le recalcul
for reception in receptions:
    try:
        # Invalider le cache et recalculer
        reception.invalidate_recordset(['avance_producteur', 'transport', 'paiement_emballage'])
        # Forcer le compute en accédant aux champs
        _ = reception.avance_producteur
        _ = reception.transport
        _ = reception.paiement_emballage
    except Exception as e:
        _logger.error(f"Erreur pour réception {reception.name}: {e}")

env.cr.commit()
_logger.info("Recalcul terminé!")
exit()
EOFSHELL

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Recalcul terminé avec succès!${NC}"
    else
        echo -e "${RED}❌ Erreur lors du recalcul${NC}"
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Terminé!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
