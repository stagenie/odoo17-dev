/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { PdfOptionsModal } from "./PdfOptionsModal";

// Messages d'état wkhtmltopdf
const WKHTMLTOPDF_MESSAGES = {
    broken: _t("Votre installation de Wkhtmltopdf semble défectueuse. Le rapport sera affiché en HTML."),
    install: _t("Impossible de trouver Wkhtmltopdf sur ce système. Le rapport sera affiché en HTML."),
    upgrade: _t("Vous devriez mettre à jour votre version de Wkhtmltopdf vers au moins 0.12.0."),
    workers: _t("Vous devez démarrer Odoo avec au moins deux workers pour imprimer une version PDF des rapports.")
};

let iframeForReport = null;
let wkhtmltopdfStateProm = null;

/**
 * Fonction pour imprimer via iframe invisible
 */
function printPdf(url, callback) {
    if (!iframeForReport) {
        iframeForReport = document.createElement('iframe');
        iframeForReport.className = 'o_report_pdf_print_iframe';
        iframeForReport.style.display = 'none';
        iframeForReport.style.position = 'absolute';
        iframeForReport.style.width = '0';
        iframeForReport.style.height = '0';
        document.body.appendChild(iframeForReport);
    }

    iframeForReport.onload = function() {
        setTimeout(function() {
            try {
                iframeForReport.contentWindow.focus();
                iframeForReport.contentWindow.print();
            } catch(err) {
                console.error("Erreur impression:", err);
            }
            if (callback) callback();
        }, 100);
    };

    // Ajouter timestamp pour éviter le cache
    const separator = url.includes('?') ? '&' : '?';
    iframeForReport.src = `${url}${separator}_t=${Date.now()}`;
}

/**
 * Construire l'URL du rapport
 */
function getReportUrl(action, type, env) {
    let url = `/report/${type}/${action.report_name}`;
    const actionContext = action.context || {};

    if (action.data && JSON.stringify(action.data) !== "{}") {
        const options = encodeURIComponent(JSON.stringify(action.data));
        const context = encodeURIComponent(JSON.stringify(actionContext));
        url += `?options=${options}&context=${context}`;
    } else {
        if (actionContext.active_ids) {
            url += `/${actionContext.active_ids.join(",")}`;
        }
        if (type === "html" && env) {
            const userContext = env.services.user.context || {};
            const fullContext = {...userContext, ...actionContext};
            const context = encodeURIComponent(JSON.stringify(fullContext));
            url += `?context=${context}`;
        }
    }

    return url;
}

/**
 * Handler principal avec priorité haute
 */
const pdfReportOptionsHandler = {
    /**
     * ✅ Point d'entrée principal du handler
     */
    async handle(action, options, env) {
        // Ne traiter que les rapports PDF
        if (!action || action.report_type !== "qweb-pdf") {
            return false; // Laisser Odoo gérer
        }

        let { default_print_option } = action;

        // Si download explicite, laisser Odoo gérer
        if (default_print_option === "download") {
            return false;
        }

        // Si pas d'option définie, montrer le modal
        if (!default_print_option) {
            let dialogRemover = null;

            default_print_option = await new Promise((resolve) => {
                dialogRemover = env.services.dialog.add(
                    PdfOptionsModal,
                    {
                        onSelectOption: (option) => {
                            if (dialogRemover) {
                                dialogRemover();
                            }
                            resolve(option);
                        }
                    },
                    {
                        onClose: () => resolve("close")
                    }
                );
            });

            // Si fermeture du modal, annuler l'action
            if (default_print_option === "close") {
                return true; // ✅ Bloquer l'action
            }

            // Si download sélectionné, laisser Odoo gérer
            if (default_print_option === "download") {
                return false;
            }
        }

        // Vérifier wkhtmltopdf une seule fois
        if (!wkhtmltopdfStateProm) {
            wkhtmltopdfStateProm = env.services.rpc("/report/check_wkhtmltopdf");
        }

        const state = await wkhtmltopdfStateProm; // ✅ FIX: await manquant

        // Notification si problème
        if (WKHTMLTOPDF_MESSAGES[state]) {
            env.services.notification.add(WKHTMLTOPDF_MESSAGES[state], {
                type: state === "ok" ? "info" : "warning",
                title: _t("État du générateur PDF")
            });
        }

        // Si wkhtmltopdf n'est pas OK, fallback
        if (!["upgrade", "ok"].includes(state)) {
            // Fallback vers HTML
            const htmlUrl = getReportUrl(action, "html", env);
            window.open(htmlUrl, '_blank');
            return true; // ✅ Action gérée
        }

        // Construire l'URL du PDF
        const pdfUrl = getReportUrl(action, "pdf", env);

        // ✅ GÉRER LES ACTIONS SELON L'OPTION
        switch (default_print_option) {
            case "print":
                // Bloquer UI pendant l'impression
                env.services.ui.block();
                printPdf(pdfUrl, () => {
                    env.services.ui.unblock();
                    env.services.notification.add(
                        _t("Document envoyé à l'imprimante"),
                        { type: "success" }
                    );
                });
                return true; // ✅ BLOQUER LE TÉLÉCHARGEMENT

            case "open":
                // Ouvrir dans nouvel onglet
                const newWindow = window.open(pdfUrl, '_blank');
                if (!newWindow) {
                    env.services.notification.add(
                        _t("Impossible d'ouvrir le rapport. Vérifiez les bloqueurs de popup."),
                        { type: "warning" }
                    );
                    return false; // Fallback au téléchargement
                }
                return true; // ✅ BLOQUER LE TÉLÉCHARGEMENT

            default:
                return false; // Comportement par défaut
        }
    }
};

// ✅ ENREGISTRER LE HANDLER AVEC PRIORITÉ MAXIMALE
registry
    .category("ir.actions.report handlers")
    .add("pdf_report_options_handler", pdfReportOptionsHandler.handle, {
        sequence: 1  // ✅ Priorité maximale pour intercepter avant tout
    });
