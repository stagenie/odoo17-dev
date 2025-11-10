/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class TracabiliteWidget extends Component {
    static template = "adi_gecafle_statistiques.TracabiliteWidget";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            selectedLineId: null,
            ventes: []
        });
    }

    async onLineClick(lineId) {
        // Mettre à jour la ligne sélectionnée
        this.state.selectedLineId = lineId;

        // Charger les ventes pour cette ligne
        const ventes = await this.orm.searchRead(
            "gecafle.details_ventes",
            [
                ["detail_reception_id", "=", lineId],
                ["vente_id.state", "=", "valide"]
            ],
            ["vente_id", "date_vente", "client_id", "nombre_colis", "poids_net"]
        );

        this.state.ventes = ventes;
    }
}

registry.category("view_widgets").add("tracabilite_widget", TracabiliteWidget);
