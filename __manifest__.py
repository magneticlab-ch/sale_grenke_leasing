# -*- coding: utf-8 -*-
{
    'name': 'Grenke Leasing - Calcul automatique sur devis',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Integre une section de calcul Grenke Leasing directement dans les devis Odoo 19',
    'description': """
        Ce module ajoute une section dediee au leasing Grenke sur les devis de vente.
        - Calcul automatique de la mensualite selon le bareme Grenke (octobre 2024)
        - Selection de la duree : 24 / 36 / 48 / 60 mois
        - Calcul automatique des frais de dossier
        - Valeur residuelle optionnelle (3%)
        - Affichage recapitulatif dans le PDF du devis
        - Toutes les tranches de montant prises en charge (1'000 - 250'000 CHF)
    """,
    'author': 'XEFI',
    'website': '',
    'depends': ['sale_management'],
    'data': [
        'views/sale_order_views.xml',
        'report/sale_report_leasing.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
