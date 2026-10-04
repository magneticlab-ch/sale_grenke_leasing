# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    grenke_leasing_enabled = fields.Boolean(
        string='Leasing Grenke sur les devis',
        default=False,
        help="Affiche l'onglet « Leasing Grenke » et le rapport « Devis financement Grenke » "
             "sur les devis de cette société. Activé pour XEFI uniquement.",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    grenke_leasing_enabled = fields.Boolean(
        related='company_id.grenke_leasing_enabled', readonly=False,
        string='Leasing Grenke sur les devis',
    )
