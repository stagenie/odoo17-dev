#!/bin/bash

echo "=================================================="
echo "SCRIPT DE NETTOYAGE ET CORRECTION ODOO 17"
echo "=================================================="

# 1. Arrêter Odoo
echo ""
echo "1️⃣ Arrêt d'Odoo..."
sudo systemctl stop odoo17 2>/dev/null || echo "Service odoo17 non trouvé, continuons..."

# 2. Vider le cache Python
echo ""
echo "2️⃣ Suppression du cache Python..."
find /home/stadev/odoo17-dev -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find /home/stadev/odoo17-dev/adi_dev -name "*.pyc" -delete 2>/dev/null
echo "✅ Cache Python supprimé"

# 3. Créer le répertoire manquant pour l'erreur FileNotFoundError
echo ""
echo "3️⃣ Création des répertoires filestore manquants..."
mkdir -p /home/stadev/.local/share/Odoo/filestore/o17_gecafle_final_tests_f/a2/
mkdir -p /home/stadev/.local/share/Odoo/filestore/o17_gecafle_final_base/
echo "✅ Répertoires créés"

# 4. Donner les bonnes permissions
echo ""
echo "4️⃣ Correction des permissions..."
chown -R stadev:stadev /home/stadev/.local/share/Odoo/
chmod -R 755 /home/stadev/.local/share/Odoo/
echo "✅ Permissions corrigées"

# 5. Vider le cache Odoo via PostgreSQL
echo ""
echo "5️⃣ Vidage du cache dans la base de données..."
PGPASSWORD='St@dev' psql -U stadev -d o17_gecafle_final_base << EOF
-- Vider le cache des vues
DELETE FROM ir_ui_view WHERE arch_fs IS NOT NULL AND name LIKE '%gecafle%reception%';

-- Forcer la recompilation des modèles
UPDATE ir_module_module
SET state = 'to upgrade'
WHERE name IN ('adi_gecafle_receptions', 'adi_gecafle_reception_extended');

-- Vider le cache des attachments orphelins
DELETE FROM ir_attachment
WHERE res_model = 'ir.ui.view'
AND res_id NOT IN (SELECT id FROM ir_ui_view);

VACUUM ANALYZE;
EOF
echo "✅ Cache de la base de données vidé"

echo ""
echo "=================================================="
echo "NETTOYAGE TERMINÉ"
echo "=================================================="
echo ""
echo "Prochaines étapes :"
echo "1. Démarrer Odoo avec l'option de mise à jour :"
echo "   cd /home/stadev/odoo17-dev"
echo "   ./odoo-bin -c odoo17.conf -d o17_gecafle_final_base -u adi_gecafle_receptions,adi_gecafle_reception_extended"
echo ""
echo "2. OU utiliser le service :"
echo "   sudo systemctl start odoo17"
echo "   Puis dans l'interface, mettre à jour les modules"