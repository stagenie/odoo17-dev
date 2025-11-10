/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class PdfOptionsModal extends Component {
    static template = "adi_pdf_to_print_options.ButtonOptions"; // ✅ Nom corrigé
    static components = { Dialog };
    static props = {
        onSelectOption: Function,
        close: { type: Function, optional: true }
    };

    setup() {
        this.title = _t("Que souhaitez-vous faire ?");
    }

    executePdfAction(option) {
        // Appeler la callback avec l'option choisie
        this.props.onSelectOption(option);
    }
}
