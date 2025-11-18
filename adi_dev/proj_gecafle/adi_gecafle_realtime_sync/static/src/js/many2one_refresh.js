/** @odoo-module **/

import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { patch } from "@web/core/utils/patch";

/**
 * Patch simplifié du widget Many2One pour invalider le cache
 * Sans notification, juste rafraîchissement silencieux
 */
patch(Many2OneField.prototype, {
    setup() {
        super.setup();

        const fieldName = this.props.name;
        const resModel = this.props.record?.resModel;

        if ((resModel === 'gecafle.vente' || resModel === 'gecafle.details_ventes') &&
            (fieldName && fieldName.toLowerCase().includes('reception'))) {

            this.receptionUpdateHandler = this._onReceptionUpdate.bind(this);
            window.addEventListener("gecafle_reception_updated", this.receptionUpdateHandler);

            const originalOnWillUnmount = this.onWillUnmount;
            this.onWillUnmount = () => {
                window.removeEventListener("gecafle_reception_updated", this.receptionUpdateHandler);
                if (originalOnWillUnmount) {
                    originalOnWillUnmount.call(this);
                }
            };
        }
    },

    async _onReceptionUpdate(event) {
        try {
            // Invalider le cache si disponible
            if (this.autocomplete && this.autocomplete.cache) {
                this.autocomplete.cache.clear();
            }
        } catch (error) {
            // Silence les erreurs
        }
    },
});

console.log("[GeCaFle Sync] Patch Many2one appliqué");
