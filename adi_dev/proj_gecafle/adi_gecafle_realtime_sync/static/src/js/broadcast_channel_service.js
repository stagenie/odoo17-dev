/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Service de communication inter-onglets via BroadcastChannel API
 * Permet une synchronisation temps réel entre les onglets du même navigateur
 *
 * DOUBLE SÉCURITÉ:
 * 1. BroadcastChannel pour communication instantanée entre onglets
 * 2. Polling serveur toutes les 3 secondes comme backup
 */
export const broadcastChannelService = {
    dependencies: ["rpc", "orm"],

    start(env, { rpc, orm }) {
        console.log("[GeCaFle Broadcast] Service démarré (avec polling 3s)");

        // Configuration
        const CHANNEL_NAME = "gecafle_reception_sync";
        const POLLING_INTERVAL = 3000; // 3 secondes

        let channel = null;
        let lastKnownTimestamp = null;
        let listeners = new Set();
        let pollingInterval = null;
        let isPolling = false;

        // Vérifier si BroadcastChannel est supporté
        const isBroadcastSupported = typeof BroadcastChannel !== "undefined";

        if (isBroadcastSupported) {
            channel = new BroadcastChannel(CHANNEL_NAME);
            console.log("[GeCaFle Broadcast] BroadcastChannel créé");

            // Écouter les messages des autres onglets
            channel.onmessage = (event) => {
                console.log("[GeCaFle Broadcast] Message reçu via BroadcastChannel:", event.data);
                if (event.data.type === "reception_changed") {
                    lastKnownTimestamp = event.data.timestamp;
                    notifyListeners(event.data);
                }
            };
        } else {
            console.warn("[GeCaFle Broadcast] BroadcastChannel non supporté");
        }

        // Écouter aussi les changements localStorage (pour communication cross-tab)
        window.addEventListener("storage", (event) => {
            if (event.key === "gecafle_reception_change") {
                try {
                    const data = JSON.parse(event.newValue);
                    if (data && data.timestamp !== lastKnownTimestamp) {
                        console.log("[GeCaFle Broadcast] Message reçu via localStorage:", data);
                        lastKnownTimestamp = data.timestamp;
                        notifyListeners(data);
                    }
                } catch (e) {
                    // Ignorer les erreurs de parsing
                }
            }
        });

        /**
         * Démarre le polling serveur (toutes les 3 secondes)
         */
        function startPolling() {
            if (pollingInterval) return; // Déjà démarré

            console.log(`[GeCaFle Broadcast] Démarrage du polling (toutes les ${POLLING_INTERVAL/1000}s)`);

            // Vérification initiale
            checkServerTimestamp();

            // Polling régulier
            pollingInterval = setInterval(async () => {
                await checkServerTimestamp();
            }, POLLING_INTERVAL);
        }

        /**
         * Arrête le polling
         */
        function stopPolling() {
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
                console.log("[GeCaFle Broadcast] Polling arrêté");
            }
        }

        /**
         * Vérifie le timestamp serveur
         */
        async function checkServerTimestamp() {
            if (isPolling) return; // Éviter les appels concurrents

            isPolling = true;
            try {
                const timestamp = await rpc("/web/dataset/call_kw/gecafle.reception/get_last_change_timestamp", {
                    model: "gecafle.reception",
                    method: "get_last_change_timestamp",
                    args: [[]],
                    kwargs: {},
                });

                // Première vérification : juste sauvegarder le timestamp
                if (lastKnownTimestamp === null) {
                    lastKnownTimestamp = timestamp;
                    console.log("[GeCaFle Broadcast] Timestamp initial:", timestamp);
                    return;
                }

                // Si le timestamp a changé, notifier les listeners
                if (timestamp && timestamp !== lastKnownTimestamp) {
                    console.log("[GeCaFle Broadcast] Changement détecté via polling!", timestamp);
                    lastKnownTimestamp = timestamp;
                    notifyListeners({ type: "reception_changed", timestamp, source: "polling" });
                }
            } catch (error) {
                // Ne pas logger les erreurs réseau pour éviter le spam
                // console.error("[GeCaFle Broadcast] Erreur polling:", error);
            } finally {
                isPolling = false;
            }
        }

        /**
         * Notifie tous les listeners enregistrés
         */
        function notifyListeners(data) {
            console.log(`[GeCaFle Broadcast] Notification de ${listeners.size} listener(s)`);
            listeners.forEach((callback) => {
                try {
                    callback(data);
                } catch (error) {
                    console.error("[GeCaFle Broadcast] Erreur dans listener:", error);
                }
            });
        }

        /**
         * Envoie un message de changement à tous les onglets
         */
        function broadcastChange(data = {}) {
            const message = {
                type: "reception_changed",
                timestamp: Date.now().toString(),
                ...data,
            };

            console.log("[GeCaFle Broadcast] Envoi du message:", message);

            // Envoyer via BroadcastChannel (instantané)
            if (channel) {
                channel.postMessage(message);
            }

            // Toujours mettre à jour localStorage (backup cross-tab)
            try {
                localStorage.setItem("gecafle_reception_change", JSON.stringify(message));
            } catch (e) {
                // Ignorer les erreurs localStorage (mode privé, etc.)
            }

            // Notifier aussi les listeners locaux (même onglet)
            lastKnownTimestamp = message.timestamp;
            notifyListeners(message);
        }

        /**
         * Enregistre un listener pour les changements
         */
        function addListener(callback) {
            listeners.add(callback);
            console.log(`[GeCaFle Broadcast] Listener ajouté, total: ${listeners.size}`);
            return () => {
                listeners.delete(callback);
                console.log(`[GeCaFle Broadcast] Listener supprimé, total: ${listeners.size}`);
            };
        }

        /**
         * Force une vérification immédiate du serveur
         */
        async function forceCheck() {
            await checkServerTimestamp();
        }

        /**
         * Récupère le dernier timestamp connu
         */
        function getLastTimestamp() {
            return lastKnownTimestamp;
        }

        // === DÉMARRAGE AUTOMATIQUE ===

        // Démarrer le polling automatiquement (double sécurité avec BroadcastChannel)
        startPolling();

        // Gérer la visibilité de la fenêtre (pause quand caché, reprise quand visible)
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                console.log("[GeCaFle Broadcast] Fenêtre cachée, pause du polling");
                stopPolling();
            } else {
                console.log("[GeCaFle Broadcast] Fenêtre visible, reprise du polling");
                startPolling();
            }
        });

        return {
            broadcastChange,
            addListener,
            forceCheck,
            getLastTimestamp,
            startPolling,
            stopPolling,
        };
    },
};

registry.category("services").add("gecafle_broadcast", broadcastChannelService);