/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch du ListController pour broadcaster les changements de réception
 * Capture les sauvegardes dans les trees editables
 */
patch(ListController.prototype, {
    setup() {
        super.setup();

        const resModel = this.props.resModel;

        // Seulement pour les réceptions et les lignes de réception
        if (resModel === "gecafle.reception" || resModel === "gecafle.details_reception") {
            this._isReceptionList = true;

            try {
                this._broadcastService = useService("gecafle_broadcast");
            } catch (e) {
                console.warn("[GeCaFle] Service broadcast non disponible dans ListController");
                this._broadcastService = null;
            }
        }
    },

    /**
     * Override de onClickSave pour les listes éditables
     */
    async onClickSave() {
        const result = await super.onClickSave(...arguments);

        if (this._isReceptionList) {
            this._broadcastReceptionChange("save");
        }

        return result;
    },

    /**
     * Override de createRecord pour les nouvelles lignes
     */
    async createRecord(params) {
        const result = await super.createRecord(params);

        if (this._isReceptionList && result) {
            // Attendre un peu pour que la sauvegarde soit complète
            setTimeout(() => {
                this._broadcastReceptionChange("create");
            }, 500);
        }

        return result;
    },

    /**
     * Broadcast le changement
     */
    _broadcastReceptionChange(action) {
        console.log(`[GeCaFle] Liste réception: ${action}, broadcast du changement`);

        if (this._broadcastService) {
            this._broadcastService.broadcastChange({
                model: this.props.resModel,
                action: action,
            });
        } else {
            try {
                const channel = new BroadcastChannel("gecafle_reception_sync");
                channel.postMessage({
                    type: "reception_changed",
                    timestamp: Date.now().toString(),
                    model: this.props.resModel,
                    action: action,
                });
                channel.close();
            } catch (e) {
                localStorage.setItem(
                    "gecafle_reception_change",
                    JSON.stringify({
                        type: "reception_changed",
                        timestamp: Date.now().toString(),
                    })
                );
            }
        }
    },
});

console.log("[GeCaFle] Patch ListController pour réceptions appliqué");
