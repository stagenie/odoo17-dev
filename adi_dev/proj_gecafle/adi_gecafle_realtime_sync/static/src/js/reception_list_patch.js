/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch du ListController pour broadcaster les changements de réception
 *
 * Capture les sauvegardes dans les listes éditables (trees éditables).
 */
patch(ListController.prototype, {
    setup() {
        super.setup();

        const resModel = this.props.resModel;

        // Activer uniquement pour les réceptions et lignes de réception
        if (resModel === "gecafle.reception" || resModel === "gecafle.details_reception") {
            this._isReceptionList = true;

            try {
                this._syncService = useService("gecafle_sync");
            } catch (e) {
                console.warn("[GeCaFle Patch List] Service gecafle_sync non disponible");
                this._syncService = null;
            }
        }
    },

    /**
     * Override onClickSave pour les listes éditables
     */
    async onClickSave() {
        const result = await super.onClickSave(...arguments);

        if (this._isReceptionList) {
            this._broadcastChange("save");
        }

        return result;
    },

    /**
     * Override createRecord pour les nouvelles lignes
     */
    async createRecord(params) {
        const result = await super.createRecord(params);

        if (this._isReceptionList && result) {
            // Petit délai pour que la sauvegarde soit complète
            setTimeout(() => {
                this._broadcastChange("create");
            }, 300);
        }

        return result;
    },

    /**
     * Broadcast le changement
     */
    _broadcastChange(action) {
        console.log(`[GeCaFle Patch List] ${action}, broadcast du changement`);

        if (this._syncService) {
            this._syncService.broadcastChange({
                model: this.props.resModel,
                action: action,
            });
        } else {
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

console.log("[GeCaFle] Patch ListController appliqué");
