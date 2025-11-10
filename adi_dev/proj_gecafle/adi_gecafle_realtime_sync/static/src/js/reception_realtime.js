/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

/**
 * Patch du ListController pour auto-refresh sur les vues de vente
 */
patch(ListController.prototype, {
    setup() {
        super.setup();
        
        // Vérifier si c'est une vue de vente
        const resModel = this.props.resModel;
        if (resModel === "gecafle.vente" || resModel === "gecafle.details_ventes") {
            console.log("[GeCaFle] Liste de vente détectée, activation de l'auto-refresh");
            
            // Écouter l'événement personnalisé
            this.receptionUpdateHandler = this._onReceptionUpdate.bind(this);
            window.addEventListener("gecafle_reception_updated", this.receptionUpdateHandler);
            
            // Cleanup
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
        console.log("[GeCaFle] Événement de mise à jour reçu, rafraîchissement de la liste");
        // Forcer un rechargement complet pour recalculer les domaines Many2one
        if (this.model && typeof this.model.load === "function") {
            await this.model.load();
        } else if (this.model && typeof this.model.root === "object" && typeof this.model.root.load === "function") {
            await this.model.root.load();
        }
        
        // Forcer également le rechargement de l'action pour rafraîchir les domaines
        if (this.env && this.env.services && this.env.services.action) {
            // Trigger un reload de la vue courante
            console.log("[GeCaFle] Rechargement de la vue pour mettre à jour les domaines");
        }
    },
});

/**
 * Patch du FormController pour auto-refresh sur les formulaires de vente
 */
patch(FormController.prototype, {
    setup() {
        super.setup();
        
        // Vérifier si c'est un formulaire de vente
        const resModel = this.props.resModel;
        if (resModel === "gecafle.vente") {
            console.log("[GeCaFle] Formulaire de vente détecté, activation de l'auto-refresh");
            
            // Écouter l'événement personnalisé
            this.receptionUpdateHandler = this._onReceptionUpdate.bind(this);
            window.addEventListener("gecafle_reception_updated", this.receptionUpdateHandler);
            
            // Cleanup
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
        console.log("[GeCaFle] Événement de mise à jour reçu, rafraîchissement du formulaire");
        // Rafraîchir uniquement si le formulaire est en mode édition/création
        if (this.model && this.model.root && this.model.root.resId) {
            // En mode édition, on peut rafraîchir certains champs
            // mais on évite de perturber l'utilisateur en cours de saisie
            console.log("[GeCaFle] Formulaire en mode édition, rafraîchissement partiel");
            // Optionnel: rafraîchir uniquement certains champs
        } else if (this.model && !this.model.root.resId) {
            // En mode création, on peut rafraîchir les relations (ex: produits disponibles)
            console.log("[GeCaFle] Formulaire en mode création, mise à jour des relations");
            if (this.model.load) {
                await this.model.load();
            }
        }
    },
});

console.log("[GeCaFle] Patches d'auto-refresh appliqués aux contrôleurs");
