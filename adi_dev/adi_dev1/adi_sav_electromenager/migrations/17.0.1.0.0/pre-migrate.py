# -*- coding: utf-8 -*-
"""
Migration script pour nettoyer les champs orphelins de l'ancienne version
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Nettoie les champs orphelins de l'ancienne version du module adi_sav_electromenager
    qui causaient des erreurs lors de la mise à jour.

    Champs supprimés dans la nouvelle version :
    - Modèle sav.return : doc_state, action_taken, picking_id, sale_order_id,
      product_id, serial_number, product_condition, sale_date, filter_from_picking,
      available_product_ids, delivery_date, color, diagnostic, repair_notes,
      reception_date, repair_start_date, repair_end_date, sent_to_repairer_date,
      returned_to_center_date, sent_to_sales_point_date
    """
    _logger.info("Starting migration: cleaning orphaned fields from sav.return model")

    # Liste des champs orphelins à supprimer
    orphaned_fields = [
        'doc_state', 'action_taken', 'picking_id', 'sale_order_id',
        'product_id', 'serial_number', 'product_condition', 'sale_date',
        'filter_from_picking', 'available_product_ids', 'delivery_date',
        'color', 'diagnostic', 'repair_notes', 'reception_date',
        'repair_start_date', 'repair_end_date', 'sent_to_repairer_date',
        'returned_to_center_date', 'sent_to_sales_point_date'
    ]

    # Supprimer les champs orphelins de ir.model.fields
    for field_name in orphaned_fields:
        try:
            cr.execute("""
                DELETE FROM ir_model_fields
                WHERE model = 'sav.return'
                AND name = %s
            """, (field_name,))
            deleted = cr.rowcount
            if deleted > 0:
                _logger.info(f"Deleted orphaned field 'sav.return.{field_name}' ({deleted} record(s))")
        except Exception as e:
            _logger.warning(f"Could not delete field 'sav.return.{field_name}': {e}")

    # Supprimer les enregistrements ir.model.data associés
    try:
        cr.execute("""
            DELETE FROM ir_model_data
            WHERE module = 'adi_sav_electromenager'
            AND name LIKE 'field_sav_return__doc_state%'
        """)
        deleted = cr.rowcount
        if deleted > 0:
            _logger.info(f"Deleted {deleted} orphaned ir.model.data record(s)")
    except Exception as e:
        _logger.warning(f"Could not delete ir.model.data records: {e}")

    _logger.info("Migration completed: orphaned fields cleaned successfully")
