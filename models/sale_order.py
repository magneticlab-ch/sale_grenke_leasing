# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

# ---------------------------------------------------------------------------
#  Bareme Grenke Leasing - octobre 2024
#  Structure : {duree_mois: {(min, max): coefficient_%}}
# ---------------------------------------------------------------------------
GRENKE_RATES = {
    24: {
        (1000,    4999):  4.62,
        (5000,   24999):  4.59,
        (25000,  49999):  4.56,
        (50000,  99999):  4.50,
        (100000, 250000): 4.48,
    },
    36: {
        (1000,    4999):  3.24,
        (5000,   24999):  3.21,
        (25000,  49999):  3.17,
        (50000,  99999):  3.11,
        (100000, 250000): 3.08,
    },
    48: {
        (1000,    4999):  2.54,
        (5000,   24999):  2.52,
        (25000,  49999):  2.48,
        (50000,  99999):  2.41,
        (100000, 250000): 2.39,
    },
    60: {
        (1000,    4999):  2.15,
        (5000,   24999):  2.12,
        (25000,  49999):  2.08,
        (50000,  99999):  2.01,
        (100000, 250000): 1.99,
    },
}


def _get_grenke_rate(amount, duration):
    """Retourne le coefficient (%) Grenke pour un montant et une duree donnes."""
    rates = GRENKE_RATES.get(duration, {})
    for (low, high), rate in rates.items():
        if low <= amount <= high:
            return rate
    return 0.0


def _get_dossier_fee_rate(amount):
    """
    Retourne le taux des frais de dossier Grenke :
      2%  jusqu'a  24'999 CHF
      1%  jusqu'a  49'999 CHF
      0.5% des     50'000 CHF
    Minimum : 200 CHF
    """
    if amount < 25000:
        return 2.0
    elif amount < 50000:
        return 1.0
    else:
        return 0.5


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # -- Activation --------------------------------------------------------
    leasing_enabled = fields.Boolean(
        string='Proposer une option leasing Grenke',
        default=False,
        help="Cochez pour afficher la section de calcul leasing dans ce devis.",
    )

    # -- Parametres modifiables par le commercial --------------------------
    leasing_amount = fields.Float(
        string='Montant a financer HT (CHF)',
        digits=(10, 2),
        help="Montant net HT de l'equipement/logiciel a soumettre au leasing.",
    )
    leasing_duration = fields.Selection(
        selection=[
            ('24', '24 mois'),
            ('36', '36 mois'),
            ('48', '48 mois'),
            ('60', '60 mois'),
        ],
        string='Duree du leasing',
        default='36',
        help="Duree souhaitee du contrat de leasing.",
    )
    leasing_residual_value_enabled = fields.Boolean(
        string='Valeur residuelle optionnelle (3%)',
        default=True,
        help="Activer la valeur residuelle de rachat a 3% en fin de contrat.",
    )
    leasing_dossier_fee_override = fields.Boolean(
        string='Modifier manuellement les frais de dossier',
        default=False,
    )
    leasing_dossier_fee_manual = fields.Float(
        string='Frais de dossier manuels (CHF)',
        digits=(10, 2),
        help="Laissez vide pour utiliser le calcul automatique Grenke.",
    )

    # -- Champs calcules (lecture seule) -----------------------------------
    leasing_rate = fields.Float(
        string='Coefficient Grenke (%)',
        compute='_compute_leasing',
        store=True,
        digits=(5, 2),
    )
    leasing_monthly = fields.Float(
        string='Mensualite HT (CHF)',
        compute='_compute_leasing',
        store=True,
        digits=(10, 2),
    )
    leasing_total_rent = fields.Float(
        string='Total loyers HT (CHF)',
        compute='_compute_leasing',
        store=True,
        digits=(10, 2),
    )
    leasing_residual_amount = fields.Float(
        string='Valeur residuelle (CHF)',
        compute='_compute_leasing',
        store=True,
        digits=(10, 2),
    )
    leasing_dossier_fee = fields.Float(
        string='Frais de dossier HT (CHF)',
        compute='_compute_leasing',
        store=True,
        digits=(10, 2),
    )
    leasing_dossier_fee_rate_display = fields.Float(
        string='Taux frais de dossier (%)',
        compute='_compute_leasing',
        store=True,
        digits=(5, 2),
    )
    leasing_grand_total = fields.Float(
        string='Cout total financement (CHF)',
        compute='_compute_leasing',
        store=True,
        digits=(10, 2),
    )
    leasing_overcost = fields.Float(
        string='Surcout vs achat comptant (CHF)',
        compute='_compute_leasing',
        store=True,
        digits=(10, 2),
    )
    leasing_overcost_pct = fields.Float(
        string='Surcout (%)',
        compute='_compute_leasing',
        store=True,
        digits=(5, 2),
    )
    leasing_tranche_label = fields.Char(
        string='Tranche Grenke',
        compute='_compute_leasing',
        store=True,
    )
    leasing_duration_int = fields.Integer(
        string='Duree (entier)',
        compute='_compute_leasing',
        store=True,
    )

    # -- Methode de calcul principale --------------------------------------
    @api.depends(
        'leasing_enabled',
        'leasing_amount',
        'leasing_duration',
        'leasing_residual_value_enabled',
        'leasing_dossier_fee_override',
        'leasing_dossier_fee_manual',
    )
    def _compute_leasing(self):
        for order in self:
            if not order.leasing_enabled or not order.leasing_amount:
                order.leasing_rate = 0.0
                order.leasing_monthly = 0.0
                order.leasing_total_rent = 0.0
                order.leasing_residual_amount = 0.0
                order.leasing_dossier_fee = 0.0
                order.leasing_dossier_fee_rate_display = 0.0
                order.leasing_grand_total = 0.0
                order.leasing_overcost = 0.0
                order.leasing_overcost_pct = 0.0
                order.leasing_tranche_label = ''
                order.leasing_duration_int = 0
                continue

            amount = order.leasing_amount
            duration = int(order.leasing_duration or '36')

            # Coefficient Grenke
            rate = _get_grenke_rate(amount, duration)
            order.leasing_rate = rate
            order.leasing_duration_int = duration

            # Mensualite
            monthly = amount * rate / 100.0
            order.leasing_monthly = monthly

            # Total loyers
            total_rent = monthly * duration
            order.leasing_total_rent = total_rent

            # Valeur residuelle
            residual = amount * 0.03 if order.leasing_residual_value_enabled else 0.0
            order.leasing_residual_amount = residual

            # Frais de dossier
            if order.leasing_dossier_fee_override and order.leasing_dossier_fee_manual:
                fee = order.leasing_dossier_fee_manual
                fee_rate = (fee / amount * 100.0) if amount else 0.0
            else:
                fee_rate = _get_dossier_fee_rate(amount)
                fee = max(amount * fee_rate / 100.0, 200.0)

            order.leasing_dossier_fee = fee
            order.leasing_dossier_fee_rate_display = fee_rate

            # Grand total et surcout
            grand_total = total_rent + residual + fee
            order.leasing_grand_total = grand_total
            order.leasing_overcost = grand_total - amount
            order.leasing_overcost_pct = (
                (grand_total - amount) / amount * 100.0
            ) if amount else 0.0

            # Label de tranche
            rates_for_duration = GRENKE_RATES.get(duration, {})
            tranche_label = ''
            for (low, high), _r in rates_for_duration.items():
                if low <= amount <= high:
                    tranche_label = "CHF %s - %s" % (
                        f"{low:,.0f}".replace(',', "'"),
                        f"{high:,.0f}".replace(',', "'"),
                    )
                    break
            order.leasing_tranche_label = tranche_label

    @api.constrains('leasing_amount')
    def _check_leasing_amount(self):
        for order in self:
            if order.leasing_enabled and order.leasing_amount:
                if order.leasing_amount < 1000 or order.leasing_amount > 250000:
                    raise ValidationError(
                        "Le montant a financer doit etre compris entre "
                        "CHF 1'000 et CHF 250'000 selon le bareme Grenke Leasing."
                    )

    @api.onchange('leasing_enabled')
    def _onchange_leasing_enabled(self):
        """Pre-remplit le montant a financer avec le total HT du devis."""
        if self.leasing_enabled and not self.leasing_amount and self.amount_untaxed:
            self.leasing_amount = self.amount_untaxed
