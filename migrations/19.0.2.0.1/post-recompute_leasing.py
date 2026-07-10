# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Recalcule les champs leasing stockes apres passage au bareme Super Lease 2026.

    Les coefficients, les frais de dossier (forfait 200) et le retrait de la valeur
    residuelle changent les valeurs calculees ; sans ce recalcul les devis existants
    conservent les montants stockes de l'ancien bareme (octobre 2024).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    orders = env['sale.order'].search([('leasing_enabled', '=', True)])
    if orders:
        orders._compute_leasing()
