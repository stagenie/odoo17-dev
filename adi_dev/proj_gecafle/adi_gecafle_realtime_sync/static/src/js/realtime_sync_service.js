/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/**
 * Service de synchronisation temps réel pour GeCaFle
 * Écoute les notifications du bus et rafraîchit les vues automatiquement
 */
export const realtimeSyncService = {
    dependencies: ["bus_service", "notification", "action"],

    start(env, { bus_service, notification, action }) {
        console.log("[GeCaFle] Service de synchronisation temps réel démarré");

        let receptionListeners = new Set();
        let venteViews = new Set();

        // S'abonner au canal de réceptions
        bus_service.subscribe("gecafle_reception_sync", (message) => {
            console.log("[GeCaFle] Notification reçue:", message);
            handleReceptionChange(message);
        });

        // S'abonner aux notifications de type 'gecafle.reception.change'
        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const notification of notifications) {
                if (notification.type === "gecafle.reception.change") {
                    console.log("[GeCaFle] Changement de réception détecté:", notification.payload);
                    handleReceptionChange(notification.payload);
                }
            }
        });

        /**
         * Gère les changements de réception
         */
        function handleReceptionChange(message) {
            const operation = message.operation;
            const receptionId = message.reception_id;

            // Afficher une notification visuelle
            let notifMessage = "";
            if (operation === "create") {
                notifMessage = `Nouvelle réception créée: ${message.reception_name || receptionId}`;
            } else if (operation === "update") {
                notifMessage = `Réception mise à jour: ${message.reception_name || receptionId}`;
            } else if (operation === "delete") {
                notifMessage = `Réception(s) supprimée(s)`;
            }

            if (notifMessage) {
                notification.add(notifMessage, {
                    type: "info",
                    title: "Synchronisation GeCaFle",
                    sticky: false,
                });
                
                // Si on est dans une vue de vente en mode formulaire, 
                // afficher un message supplémentaire
                if (env.services.action && env.services.action.currentController) {
                    const controller = env.services.action.currentController;
                    if (controller.props && controller.props.resModel === 'gecafle.vente') {
                        notification.add(
                            "💡 Astuce: Rechargez le champ 'Réception' pour voir les nouvelles options disponibles",
                            {
                                type: "info",
                                title: "GeCaFle",
                                sticky: true,  // Reste visible
                            }
                        );
                    }
                }
            }

            // Rafraîchir les vues de vente
            refreshVenteViews();

            // Notifier les listeners enregistrés
            receptionListeners.forEach((listener) => {
                try {
                    listener(message);
                } catch (error) {
                    console.error("[GeCaFle] Erreur dans le listener:", error);
                }
            });
        }

        /**
         * Rafraîchit les vues de vente ouvertes
         */
        async function refreshVenteViews() {
            console.log("[GeCaFle] Rafraîchissement des vues de vente...");
            
            // Déclencher un événement personnalisé pour rafraîchir les vues
            const event = new CustomEvent("gecafle_reception_updated", {
                detail: { timestamp: Date.now() },
            });
            window.dispatchEvent(event);

            // Forcer le rechargement de l'action courante pour recalculer les domaines Many2one
            try {
                const actionService = env.services.action;
                if (actionService && actionService.currentController) {
                    const controller = actionService.currentController;
                    
                    // Vérifier si c'est une vue de vente
                    if (controller.props && 
                        (controller.props.resModel === 'gecafle.vente' || 
                         controller.props.resModel === 'gecafle.details_ventes')) {
                        
                        console.log("[GeCaFle] Vue de vente détectée, rechargement complet pour recalculer les domaines");
                        
                        // Méthode 1: Recharger le model
                        if (controller.model && controller.model.load) {
                            await controller.model.load();
                        }
                        
                        // Méthode 2: Forcer le reload de l'action complète (recalcule les domaines)
                        if (actionService.doAction) {
                            const currentAction = controller.props.context;
                            // On peut déclencher un soft reload ici si nécessaire
                        }
                    }
                }
            } catch (error) {
                console.error("[GeCaFle] Erreur lors du rafraîchissement:", error);
            }
        }

        /**
         * Enregistre un listener pour les changements de réception
         */
        function addReceptionListener(callback) {
            receptionListeners.add(callback);
            return () => receptionListeners.delete(callback);
        }

        /**
         * Enregistre une vue de vente
         */
        function registerVenteView(viewId) {
            venteViews.add(viewId);
            return () => venteViews.delete(viewId);
        }

        return {
            addReceptionListener,
            registerVenteView,
            refreshVenteViews,
        };
    },
};

registry.category("services").add("gecafle_realtime_sync", realtimeSyncService);
