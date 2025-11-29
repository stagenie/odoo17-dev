/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Widget Many2One personnalisé pour les lignes de réception (detail_reception_id)
 * Écoute les changements en temps réel et force le rechargement des options
 *
 * STRATÉGIE: Vérification au moment du clic/focus (plus léger que le polling)
 */
export class DetailReceptionRealtimeField extends Many2OneField {
    static template = "web.Many2OneField";

    setup() {
        super.setup();

        this.orm = useService("orm");

        // Essayer d'obtenir le service broadcast
        try {
            this.broadcastService = useService("gecafle_broadcast");
        } catch (e) {
            console.warn("[DetailReceptionRealtime] Service broadcast non disponible");
            this.broadcastService = null;
        }

        // État pour forcer le rechargement
        this.realtimeState = useState({
            needsReload: false,
            lastUpdate: null,
            searchCount: 0,
        });

        // Référence pour le cleanup
        this.removeListener = null;

        onMounted(() => {
            // S'abonner aux changements de réception (via broadcast/polling)
            if (this.broadcastService) {
                this.removeListener = this.broadcastService.addListener((data) => {
                    console.log("[DetailReceptionRealtime] Changement reçu, marquage pour reload");
                    this.realtimeState.needsReload = true;
                    this.realtimeState.lastUpdate = data.timestamp;
                    this.realtimeState.searchCount++;
                });
            }
        });

        onWillUnmount(() => {
            if (this.removeListener) {
                this.removeListener();
            }
        });
    }

    /**
     * Override de search pour forcer le rechargement des options
     */
    async search(name) {
        // IMPORTANT: Forcer une vérification serveur AVANT la recherche
        await this._forceServerCheck();

        if (this.realtimeState.needsReload) {
            console.log("[DetailReceptionRealtime] Force reload activé pour la recherche");
            this.realtimeState.needsReload = false;
        }

        // Incrémenter pour invalider le cache
        this.realtimeState.searchCount++;

        return super.search(name);
    }

    /**
     * Force une vérification du serveur avant d'afficher les options
     */
    async _forceServerCheck() {
        if (this.broadcastService) {
            console.log("[DetailReceptionRealtime] Vérification serveur au clic...");
            await this.broadcastService.forceCheck();
        }
    }

    /**
     * Override getContext pour ajouter un paramètre anti-cache
     */
    get searchContext() {
        const context = super.searchContext || {};
        return {
            ...context,
            _gecafle_nocache: this.realtimeState.searchCount,
            _timestamp: Date.now(),
        };
    }

    /**
     * Override onInput pour vérifier à chaque frappe
     */
    onInput(ev) {
        // Incrémenter le compteur anti-cache
        this.realtimeState.searchCount++;
        return super.onInput?.(ev);
    }
}

// Définition du widget
export const detailReceptionRealtimeField = {
    ...many2OneField,
    component: DetailReceptionRealtimeField,
    displayName: "Ligne Réception Temps Réel",
    supportedTypes: ["many2one"],
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneField.extractProps(fieldInfo, dynamicInfo);
        return {
            ...props,
        };
    },
};

// Enregistrer le widget dans le registry
registry.category("fields").add("detail_reception_realtime", detailReceptionRealtimeField);

console.log("[GeCaFle] Widget detail_reception_realtime enregistré");
