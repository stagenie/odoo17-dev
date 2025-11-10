odoo.define('adi_reception_flexibility.auto_refresh', function(require) {
    "use strict";

    const ListController = require('web.ListController');
    const session = require('web.session');
    const Dialog = require('web.Dialog');
    const core = require('web.core');
    const _t = core._t;

    let lastCheckTime = null;
    let refreshInterval = null;

    ListController.include({
        init: function() {
            this._super.apply(this, arguments);

            // Activer uniquement pour les modèles concernés
            if (this.modelName === 'gecafle.reception' || this.modelName === 'gecafle.vente') {
                this.startAutoRefresh();
            }
        },

        startAutoRefresh: function() {
            const self = this;

            // Récupérer l'intervalle depuis la configuration
            const interval = session.company_settings?.auto_refresh_interval || 30;

            // Nettoyer l'intervalle existant
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }

            // Démarrer le nouvel intervalle
            refreshInterval = setInterval(function() {
                self.checkForUpdates();
            }, interval * 1000);

            // Sauvegarder l'heure actuelle
            lastCheckTime = new Date().toISOString();
        },

        checkForUpdates: function() {
            const self = this;

            if (this.modelName === 'gecafle.reception') {
                this._rpc({
                    model: 'gecafle.reception',
                    method: 'search_count',
                    args: [[['write_date', '>', lastCheckTime]]],
                }).then(function(count) {
                    if (count > 0) {
                        self.showUpdateNotification(count);
                    }
                });
            } else if (this.modelName === 'gecafle.vente') {
                // Vérifier les nouvelles réceptions pour la vue vente
                this._rpc({
                    model: 'gecafle.vente',
                    method: 'check_new_receptions',
                    args: [lastCheckTime],
                }).then(function(result) {
                    if (result.has_new) {
                        self.showNewReceptionNotification(result.count);
                    }
                });
            }

            lastCheckTime = new Date().toISOString();
        },

        showUpdateNotification: function(count) {
            const self = this;

            // Afficher une notification
            this.do_notify(
                _t("Données mises à jour"),
                _t(count + " réception(s) ont été modifiées. Cliquez pour rafraîchir."),
                false
            );

            // Option de rafraîchissement automatique après 3 secondes
            setTimeout(function() {
                self.reload();
            }, 3000);
        },

        showNewReceptionNotification: function(count) {
            const self = this;

            // Notification pour les nouvelles réceptions
            const message = _t(count + " nouvelle(s) réception(s) disponible(s)");

            // Afficher un bouton de rafraîchissement
            this.do_notify(
                _t("Nouvelles réceptions"),
                message,
                false,
                function() {
                    self.reload();
                }
            );
        },

        destroy: function() {
            // Nettoyer l'intervalle lors de la destruction
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
            this._super.apply(this, arguments);
        },
    });

    // Extension pour le champ Many2one dans les formulaires de vente
    const FieldMany2One = require('web.relational_fields').FieldMany2One;

    FieldMany2One.include({
        _onInputClick: function() {
            const self = this;

            // Si c'est un champ de réception dans une vente
            if (this.model === 'gecafle.details_ventes' && this.name === 'reception_id') {
                // Forcer le rechargement du domaine
                this._rpc({
                    model: 'gecafle.vente',
                    method: 'get_available_receptions',
                    args: [],
                }).then(function(result) {
                    // Mettre à jour les options disponibles
                    self._searchCreatePopup("search", false, {});
                });
            }

            this._super.apply(this, arguments);
        },
    });
});
