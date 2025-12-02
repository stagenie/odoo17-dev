/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Service de synchronisation temps réel pour les réceptions GeCaFle
 *
 * Ce service gère:
 * 1. Polling du serveur toutes les 2 secondes pour détecter les changements
 * 2. BroadcastChannel API pour synchronisation instantanée inter-onglets
 * 3. localStorage comme fallback pour les navigateurs plus anciens
 * 4. Notification des widgets quand un changement est détecté
 */
export const receptionSyncService = {
    dependencies: ["rpc"],

    start(env, { rpc }) {
        console.log("[GeCaFle Sync] Service de synchronisation démarré");

        // Configuration
        const POLLING_INTERVAL = 2000; // 2 secondes pour réactivité accrue
        const CHANNEL_NAME = "gecafle_reception_sync";

        // État interne
        let channel = null;
        let lastKnownTimestamp = null;
        let listeners = new Set();
        let pollingInterval = null;
        let isPolling = false;
        let changeCounter = 0; // Compteur incrémenté à chaque changement

        // === INITIALISATION BROADCASTCHANNEL ===
        const isBroadcastSupported = typeof BroadcastChannel !== "undefined";

        if (isBroadcastSupported) {
            try {
                channel = new BroadcastChannel(CHANNEL_NAME);
                console.log("[GeCaFle Sync] BroadcastChannel initialisé");

                channel.onmessage = (event) => {
                    console.log("[GeCaFle Sync] Message BroadcastChannel reçu:", event.data);
                    if (event.data.type === "reception_changed") {
                        handleChange(event.data);
                    }
                };
            } catch (e) {
                console.warn("[GeCaFle Sync] Erreur BroadcastChannel:", e);
            }
        }

        // === FALLBACK LOCALSTORAGE ===
        window.addEventListener("storage", (event) => {
            if (event.key === "gecafle_reception_change") {
                try {
                    const data = JSON.parse(event.newValue);
                    if (data && data.timestamp !== lastKnownTimestamp) {
                        console.log("[GeCaFle Sync] Changement détecté via localStorage");
                        handleChange(data);
                    }
                } catch (e) {
                    // Ignorer les erreurs de parsing
                }
            }
        });

        // === GESTION DES CHANGEMENTS ===
        function handleChange(data) {
            lastKnownTimestamp = data.timestamp;
            changeCounter++;

            console.log(`[GeCaFle Sync] Notification de ${listeners.size} listener(s), compteur: ${changeCounter}`);

            // Notifier tous les listeners avec le compteur de changement
            const changeData = {
                ...data,
                changeCounter,
                timestamp: data.timestamp || Date.now().toString(),
            };

            listeners.forEach((callback) => {
                try {
                    callback(changeData);
                } catch (error) {
                    console.error("[GeCaFle Sync] Erreur dans listener:", error);
                }
            });
        }

        // === POLLING SERVEUR ===
        async function checkServer() {
            if (isPolling) return;

            isPolling = true;
            try {
                const timestamp = await rpc(
                    "/web/dataset/call_kw/gecafle.reception/get_last_change_timestamp",
                    {
                        model: "gecafle.reception",
                        method: "get_last_change_timestamp",
                        args: [[]],
                        kwargs: {},
                    }
                );

                // Première exécution: juste sauvegarder le timestamp
                if (lastKnownTimestamp === null) {
                    lastKnownTimestamp = timestamp;
                    console.log("[GeCaFle Sync] Timestamp initial:", timestamp);
                    return;
                }

                // Changement détecté
                if (timestamp && timestamp !== lastKnownTimestamp) {
                    console.log("[GeCaFle Sync] Changement serveur détecté!", {
                        ancien: lastKnownTimestamp,
                        nouveau: timestamp,
                    });
                    handleChange({
                        type: "reception_changed",
                        timestamp,
                        source: "polling",
                    });
                }
            } catch (error) {
                // Silencieux pour éviter le spam de logs
            } finally {
                isPolling = false;
            }
        }

        function startPolling() {
            if (pollingInterval) return;

            console.log(`[GeCaFle Sync] Démarrage polling (${POLLING_INTERVAL}ms)`);
            checkServer(); // Vérification initiale
            pollingInterval = setInterval(checkServer, POLLING_INTERVAL);
        }

        function stopPolling() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
                console.log("[GeCaFle Sync] Polling arrêté");
            }
        }

        // === GESTION VISIBILITÉ ===
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                stopPolling();
            } else {
                startPolling();
                // Vérification immédiate au retour
                checkServer();
            }
        });

        // Démarrer le polling automatiquement
        startPolling();

        // === API PUBLIQUE ===
        return {
            /**
             * Envoie une notification de changement à tous les onglets
             */
            broadcastChange(data = {}) {
                const message = {
                    type: "reception_changed",
                    timestamp: Date.now().toString(),
                    ...data,
                };

                console.log("[GeCaFle Sync] Broadcast changement:", message);

                // BroadcastChannel
                if (channel) {
                    try {
                        channel.postMessage(message);
                    } catch (e) {
                        console.warn("[GeCaFle Sync] Erreur envoi BroadcastChannel:", e);
                    }
                }

                // localStorage (fallback + trigger pour autres onglets)
                try {
                    localStorage.setItem("gecafle_reception_change", JSON.stringify(message));
                } catch (e) {
                    // Mode privé ou quota dépassé
                }

                // Notifier localement aussi
                handleChange(message);
            },

            /**
             * Ajoute un listener pour les changements
             * Retourne une fonction pour supprimer le listener
             */
            addListener(callback) {
                listeners.add(callback);
                console.log(`[GeCaFle Sync] Listener ajouté (total: ${listeners.size})`);

                return () => {
                    listeners.delete(callback);
                    console.log(`[GeCaFle Sync] Listener supprimé (total: ${listeners.size})`);
                };
            },

            /**
             * Force une vérification immédiate du serveur
             */
            async forceCheck() {
                console.log("[GeCaFle Sync] Vérification forcée");
                await checkServer();
            },

            /**
             * Retourne le compteur de changements
             * Utilisé pour invalider les caches
             */
            getChangeCounter() {
                return changeCounter;
            },

            /**
             * Retourne le dernier timestamp connu
             */
            getLastTimestamp() {
                return lastKnownTimestamp;
            },

            /**
             * Incrémente le compteur de changements
             * Utilisé pour forcer un rechargement
             */
            incrementCounter() {
                changeCounter++;
                return changeCounter;
            },
        };
    },
};

// Enregistrer le service
registry.category("services").add("gecafle_sync", receptionSyncService);

console.log("[GeCaFle] Service gecafle_sync enregistré");
