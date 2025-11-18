/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/**
 * Service de synchronisation temps réel pour GeCaFle
 * Utilise un système de polling simple pour vérifier les changements
 * Pas de bus, pas de notifications - juste un rafraîchissement silencieux
 */
export const realtimeSyncService = {
    dependencies: ["rpc", "action"],

    start(env, { rpc, action }) {
        console.log("[GeCaFle Sync] Service démarré");

        let lastKnownTimestamp = null;
        let pollingInterval = null;
        let isPolling = false;

        /**
         * Vérifie si des réceptions ont changé
         */
        async function checkForChanges() {
            if (isPolling) return; // Éviter les appels concurrents

            isPolling = true;
            try {
                // Appel RPC pour obtenir le timestamp de la dernière modification
                const currentTimestamp = await rpc('/web/dataset/call_kw/gecafle.reception/get_last_change_timestamp', {
                    model: 'gecafle.reception',
                    method: 'get_last_change_timestamp',
                    args: [[]],
                    kwargs: {}
                });

                // Si c'est la première vérification, juste sauvegarder le timestamp
                if (lastKnownTimestamp === null) {
                    lastKnownTimestamp = currentTimestamp;
                    console.log("[GeCaFle Sync] Timestamp initial:", currentTimestamp);
                    return;
                }

                // Si le timestamp a changé, rafraîchir les vues
                if (currentTimestamp !== lastKnownTimestamp) {
                    console.log("[GeCaFle Sync] Changement détecté! Rafraîchissement...");
                    lastKnownTimestamp = currentTimestamp;
                    await refreshVenteViews();
                }

            } catch (error) {
                console.error("[GeCaFle Sync] Erreur lors de la vérification:", error);
            } finally {
                isPolling = false;
            }
        }

        /**
         * Rafraîchit les vues de vente ouvertes (silencieusement)
         */
        async function refreshVenteViews() {
            try {
                // Déclencher un événement personnalisé
                const event = new CustomEvent("gecafle_reception_updated", {
                    detail: { timestamp: Date.now() }
                });
                window.dispatchEvent(event);

                // Essayer de rafraîchir la vue active si c'est une vente
                const actionService = env.services.action;
                if (actionService && actionService.currentController) {
                    const controller = actionService.currentController;

                    if (controller.props &&
                        (controller.props.resModel === 'gecafle.vente' ||
                         controller.props.resModel === 'gecafle.details_ventes')) {

                        console.log("[GeCaFle Sync] Vue de vente détectée, rafraîchissement silencieux");

                        // Rafraîchir le modèle
                        if (controller.model) {
                            if (controller.model.load && typeof controller.model.load === 'function') {
                                await controller.model.load();
                            } else if (controller.model.root && controller.model.root.load) {
                                await controller.model.root.load();
                            }
                        }
                    }
                }
            } catch (error) {
                console.error("[GeCaFle Sync] Erreur lors du rafraîchissement:", error);
            }
        }

        /**
         * Démarre le polling
         */
        function startPolling() {
            if (pollingInterval) return; // Déjà démarré

            console.log("[GeCaFle Sync] Démarrage du polling (toutes les 3 secondes)");

            // Vérification initiale
            checkForChanges();

            // Polling toutes les 3 secondes
            pollingInterval = setInterval(checkForChanges, 3000);
        }

        /**
         * Arrête le polling
         */
        function stopPolling() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
                console.log("[GeCaFle Sync] Polling arrêté");
            }
        }

        // Démarrer le polling automatiquement
        startPolling();

        // Arrêter le polling quand la fenêtre est cachée (optimisation)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log("[GeCaFle Sync] Fenêtre cachée, pause du polling");
                stopPolling();
            } else {
                console.log("[GeCaFle Sync] Fenêtre visible, reprise du polling");
                startPolling();
            }
        });

        return {
            startPolling,
            stopPolling,
            checkForChanges,
            refreshVenteViews,
        };
    },
};

registry.category("services").add("gecafle_realtime_sync", realtimeSyncService);
