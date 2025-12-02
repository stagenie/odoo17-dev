/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch du FormController pour broadcaster les changements de réception
 *
 * Quand une réception ou une ligne de réception est sauvegardée,
 * ce patch notifie tous les onglets pour qu'ils rafraîchissent leurs données.
 */
patch(FormController.prototype, {
    setup() {
        super.setup();

        const resModel = this.props.resModel;

        // Activer uniquement pour les réceptions et lignes de réception
        if (resModel === "gecafle.reception" || resModel === "gecafle.details_reception") {
            this._isReceptionForm = true;

            try {
                this._syncService = useService("gecafle_sync");
            } catch (e) {
                console.warn("[GeCaFle Patch] Service gecafle_sync non disponible");
                this._syncService = null;
            }
        }
    },

    /**
     * Override saveButtonClicked pour broadcaster après sauvegarde
     */
    async saveButtonClicked(params = {}) {
        const result = await super.saveButtonClicked(params);

        if (this._isReceptionForm && result !== false) {
            this._broadcastChange("save");
        }

        return result;
    },

    /**
     * Override save pour capturer toutes les sauvegardes
     */
    async save(params = {}) {
        const result = await super.save(params);

        if (this._isReceptionForm && result !== false) {
            this._broadcastChange("save");
        }

        return result;
    },

    /**
     * Broadcast le changement à tous les onglets
     */
    _broadcastChange(action) {
        console.log(`[GeCaFle Patch] Réception ${action}, broadcast du changement`);

        if (this._syncService) {
            this._syncService.broadcastChange({
                model: this.props.resModel,
                resId: this.model.root.resId,
                action: action,
            });
        } else {
            // Fallback direct via BroadcastChannel
            this._fallbackBroadcast(action);
        }
    },

    /**
     * Fallback si le service n'est pas disponible
     */
    _fallbackBroadcast(action) {
        const message = {
            type: "reception_changed",
            timestamp: Date.now().toString(),
            model: this.props.resModel,
            resId: this.model.root.resId,
            action: action,
        };

        try {
            if (typeof BroadcastChannel !== "undefined") {
                const channel = new BroadcastChannel("gecafle_reception_sync");
                channel.postMessage(message);
                channel.close();
            }
        } catch (e) {
            // Ignorer
        }

        try {
            localStorage.setItem("gecafle_reception_change", JSON.stringify(message));
        } catch (e) {
            // Ignorer
        }
    },
});

console.log("[GeCaFle] Patch FormController appliqué");
