/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Composant Many2XAutocomplete personnalisé pour les lignes de réception
 */
class DetailReceptionM2XAutocomplete extends Many2XAutocomplete {
    setup() {
        super.setup();

        try {
            this.syncService = useService("gecafle_sync");
        } catch (e) {
            this.syncService = null;
        }
    }

    /**
     * Override de search pour ajouter un timestamp anti-cache au contexte
     */
    search(name) {
        console.log("[DetailReceptionRealtime] Recherche:", name);

        const originalContext = this.props.context;
        const timestamp = Date.now();
        const changeCounter = this.syncService?.getChangeCounter?.() || 0;

        const contextWithTimestamp = {
            ...originalContext,
            _gecafle_nocache: timestamp,
            _gecafle_counter: changeCounter,
        };

        return this.orm.call(this.props.resModel, "name_search", [], {
            name: name,
            operator: "ilike",
            args: this.props.getDomain(),
            limit: (this.props.searchLimit || 7) + 1,
            context: contextWithTimestamp,
        });
    }
}

/**
 * Widget Many2One temps réel pour les lignes de réception (detail_reception_id)
 */
export class DetailReceptionRealtimeField extends Many2OneField {
    static template = "web.Many2OneField";
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: DetailReceptionM2XAutocomplete,
    };

    setup() {
        super.setup();

        try {
            this.syncService = useService("gecafle_sync");
        } catch (e) {
            this.syncService = null;
        }

        this.realtimeState = useState({
            changeCounter: 0,
            lastCheck: Date.now(),
        });

        this._removeListener = null;

        onMounted(() => {
            if (this.syncService) {
                this._removeListener = this.syncService.addListener((data) => {
                    console.log("[DetailReceptionRealtime] Changement détecté");
                    this.realtimeState.changeCounter = data.changeCounter || Date.now();
                    this.realtimeState.lastCheck = Date.now();
                });
            }
        });

        onWillUnmount(() => {
            if (this._removeListener) {
                this._removeListener();
            }
        });
    }

    get context() {
        const baseContext = super.context;
        return {
            ...baseContext,
            _gecafle_ts: this.realtimeState.changeCounter || Date.now(),
            _gecafle_check: this.realtimeState.lastCheck,
        };
    }

    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        return {
            ...props,
            context: this.context,
        };
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

// Enregistrer le widget
registry.category("fields").add("detail_reception_realtime", detailReceptionRealtimeField);

console.log("[GeCaFle] Widget detail_reception_realtime enregistré");
