/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            this.updateCreateButton();
        });
    },

    updateCreateButton() {
        // Vérifier si on est sur une facture protégée
        if (this.props.resModel === 'account.move' && this.model.root) {
            const record = this.model.root.data;
            if (record && record.is_protected_gecafle) {
                // Masquer le bouton créer
                const createBtn = document.querySelector('.o_form_button_create');
                if (createBtn) {
                    createBtn.style.display = 'none';
                }
            }
        }
    }
});
