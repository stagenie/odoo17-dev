/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

/**
 * Patch du FormController pour broadcaster les changements de réception
 * Quand une réception est créée/modifiée, on notifie tous les onglets
 */
patch(FormController.prototype, {
    setup() {
        super.setup();

        const resModel = this.props.resModel;

        // Seulement pour les réceptions et les lignes de réception
        if (resModel === "gecafle.reception" || resModel === "gecafle.details_reception") {
            this._isReceptionForm = true;

            // Essayer d'obtenir le service broadcast
            try {
                this._broadcastService = useService("gecafle_broadcast");
            } catch (e) {
                console.warn("[GeCaFle] Service broadcast non disponible");
                this._broadcastService = null;
            }
        }
    },

    /**
     * Override de saveButtonClicked pour broadcaster après sauvegarde
     */
    async saveButtonClicked(params = {}) {
        const result = await super.saveButtonClicked(params);

        // Si c'est une réception et que la sauvegarde a réussi
        if (this._isReceptionForm && result !== false) {
            this._broadcastReceptionChange();
        }

        return result;
    },

    /**
     * Override de save pour capturer toutes les sauvegardes
     */
    async save(params = {}) {
        const result = await super.save(params);

        // Si c'est une réception et que la sauvegarde a réussi
        if (this._isReceptionForm && result !== false) {
            this._broadcastReceptionChange();
        }

        return result;
    },

    /**
     * Broadcast le changement de réception
     */
    _broadcastReceptionChange() {
        console.log("[GeCaFle] Réception modifiée, broadcast du changement");

        if (this._broadcastService) {
            this._broadcastService.broadcastChange({
                model: this.props.resModel,
                resId: this.model.root.resId,
                action: "save",
            });
        } else {
            // Fallback: utiliser directement BroadcastChannel
            try {
                const channel = new BroadcastChannel("gecafle_reception_sync");
                channel.postMessage({
                    type: "reception_changed",
                    timestamp: Date.now().toString(),
                    model: this.props.resModel,
                    resId: this.model.root.resId,
                    action: "save",
                });
                channel.close();
            } catch (e) {
                // Fallback localStorage
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

console.log("[GeCaFle] Patch FormController pour réceptions appliqué");
