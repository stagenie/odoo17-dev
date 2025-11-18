/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

/**
 * Patch simplifié du ListController pour rafraîchir les listes de vente
 */
patch(ListController.prototype, {
    setup() {
        super.setup();

        const resModel = this.props.resModel;
        if (resModel === "gecafle.vente" || resModel === "gecafle.details_ventes") {
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
            if (this.model && this.model.load) {
                await this.model.load();
            }
        } catch (error) {
            // Silence les erreurs pour ne pas perturber l'utilisateur
        }
    },
});

/**
 * Patch simplifié du FormController pour rafraîchir les formulaires de vente
 */
patch(FormController.prototype, {
    setup() {
        super.setup();

        const resModel = this.props.resModel;
        if (resModel === "gecafle.vente") {
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
            // Ne rafraîchir que si en mode création (pour ne pas perturber l'édition)
            if (this.model && this.model.root && !this.model.root.resId) {
                if (this.model.load) {
                    await this.model.load();
                }
            }
        } catch (error) {
            // Silence les erreurs
        }
    },
});

console.log("[GeCaFle Sync] Patches appliqués");
