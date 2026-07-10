# -*- coding: utf-8 -*-
{
    'name': 'Grenke Leasing - Calcul automatique sur devis',
    'version': '19.0.2.0.4',
    'category': 'Sales',
    'summary': 'Calcul Grenke Super Lease et rapport de financement dedie sur les devis Odoo 19',
    'description': """
        Ce module ajoute le calcul du leasing Grenke sur les devis de vente et un
        rapport PDF dedie au dossier de financement.
        - Calcul automatique de la mensualite selon le bareme Grenke Super Lease (janvier 2026)
        - Selection de la duree : 24 / 36 / 48 / 60 mois
        - Frais de dossier : forfait CHF 200.- HT (override manuel possible)
        - Rapport dedie "Devis financement Grenke" : lignes sans prix (description + quantite),
          page de financement (mensualite) et fiche de renseignements Grenke a signer
        - Tranches de montant prises en charge : CHF 1'000 - 99'999 (au-dela : contact Grenke)
    """,
    'author': 'XEFI',
    'website': '',
    'depends': ['sale_management'],
    'data': [
        'views/sale_order_views.xml',
        'report/sale_report_leasing_document.xml',
        'report/sale_report_leasing_actions.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
