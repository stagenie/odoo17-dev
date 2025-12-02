/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Composant Many2XAutocomplete personnalisé pour les réceptions
 * Override la méthode search pour garantir des données fraîches
 */
class ReceptionM2XAutocomplete extends Many2XAutocomplete {
    setup() {
        super.setup();

        // Référence au service de sync si disponible
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
        console.log("[ReceptionRealtime] Recherche:", name);

        // Modifier temporairement le contexte pour ajouter un timestamp anti-cache
        const originalContext = this.props.context;
        const timestamp = Date.now();
        const changeCounter = this.syncService?.getChangeCounter?.() || 0;

        // Créer un nouveau contexte avec le timestamp
        const contextWithTimestamp = {
            ...originalContext,
            _gecafle_nocache: timestamp,
            _gecafle_counter: changeCounter,
        };

        // Appel à name_search avec le contexte modifié
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
 * Widget Many2One temps réel pour les réceptions
 */
export class ReceptionRealtimeField extends Many2OneField {
    static template = "web.Many2OneField";
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: ReceptionM2XAutocomplete,
    };

    setup() {
        super.setup();

        // Service de synchronisation
        try {
            this.syncService = useService("gecafle_sync");
        } catch (e) {
            this.syncService = null;
        }

        // État pour forcer le rechargement
        this.realtimeState = useState({
            changeCounter: 0,
            lastCheck: Date.now(),
        });

        // Listener pour les changements
        this._removeListener = null;

        onMounted(() => {
            if (this.syncService) {
                this._removeListener = this.syncService.addListener((data) => {
                    console.log("[ReceptionRealtime] Changement détecté");
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

    /**
     * Override du contexte pour ajouter un paramètre anti-cache
     */
    get context() {
        const baseContext = super.context;
        return {
            ...baseContext,
            _gecafle_ts: this.realtimeState.changeCounter || Date.now(),
            _gecafle_check: this.realtimeState.lastCheck,
        };
    }

    /**
     * Override des props pour Many2XAutocomplete
     */
    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        return {
            ...props,
            context: this.context,
        };
    }
}

// Définition du widget
export const receptionRealtimeField = {
    ...many2OneField,
    component: ReceptionRealtimeField,
    displayName: "Réception Temps Réel",
    supportedTypes: ["many2one"],
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneField.extractProps(fieldInfo, dynamicInfo);
        return {
            ...props,
        };
    },
};

// Enregistrer le widget
registry.category("fields").add("reception_realtime", receptionRealtimeField);

console.log("[GeCaFle] Widget reception_realtime enregistré");
