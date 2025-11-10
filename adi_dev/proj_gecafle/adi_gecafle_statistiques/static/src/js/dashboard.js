/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class GecafleDashboard extends Component {
    static template = "adi_gecafle_statistiques.Dashboard";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");

        this.state = useState({
            period: 'month', // month, week, year
            dateFrom: null,
            dateTo: null,
            topProducts: [],
            salesByProduct: [],
            salesByProducer: [],
            isLoading: true,
            totals: {
                totalSales: 0,
                totalCommission: 0,
                totalWeight: 0,
                totalTransactions: 0
            }
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.isLoading = true;

        try {
            const data = await this.rpc("/gecafle/dashboard/data", {
                period: this.state.period,
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
            });

            this.state.topProducts = data.top_products || [];
            this.state.salesByProduct = data.sales_by_product || [];
            this.state.salesByProducer = data.sales_by_producer || [];
            this.state.totals = data.totals || this.state.totals;

        } catch (error) {
            console.error("Erreur lors du chargement des données:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    onPeriodChange(period) {
        this.state.period = period;
        this.loadDashboardData();
    }

    async onRefresh() {
        await this.loadDashboardData();
    }

    openDetailedReport(type) {
        let action_name = '';

        switch(type) {
            case 'product':
                action_name = 'adi_gecafle_statistiques.action_stat_produit';
                break;
            case 'producer':
                action_name = 'adi_gecafle_statistiques.action_stat_producteur';
                break;
            case 'period':
                action_name = 'adi_gecafle_statistiques.action_stat_periode';
                break;
        }

        if (action_name) {
            this.action.doAction(action_name);
        }
    }
}

GecafleDashboard.props = {};

registry.category("actions").add("gecafle_dashboard", GecafleDashboard);
