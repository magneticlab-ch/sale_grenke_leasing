# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

# ---------------------------------------------------------------------------
#  Bareme Grenke "Super Lease" - etabli janvier 2026
#  Calcul du loyer : montant HT x coefficient % = mensualite
#  Tranches par seuil : borne basse incluse, borne haute exclue (robuste aux
#  montants a virgule, ex. 4999.50). Au-dela de 100'000 : hors bareme.
# ---------------------------------------------------------------------------
GRENKE_TRANCHES = [
    (1000,   5000,   "1'000 - 4'999"),
    (5000,   25000,  "5'000 - 24'999"),
    (25000,  50000,  "25'000 - 49'999"),
    (50000,  100000, "50'000 - 99'999"),
]

GRENKE_RATES = {
    24: [4.59, 4.54, 4.49, 4.43],
    36: [3.21, 3.16, 3.11, 3.04],
    48: [2.52, 2.47, 2.40, 2.35],
    60: [2.12, 2.07, 2.00, 1.95],
}

# Frais de dossier : versement unique forfaitaire (Super Lease janvier 2026)
GRENKE_DOSSIER_FEE = 200.0

# Bornes de financement du bareme
GRENKE_MIN_AMOUNT = 1000
GRENKE_MAX_AMOUNT = 99999


def _get_grenke_tranche(amount):
    """Retourne (index, label) de la tranche Grenke pour un montant, ou (None, '')."""
    for index, (low, high, label) in enumerate(GRENKE_TRANCHES):
        if low <= amount < high:
            return index, label
    return None, ''


def _get_grenke_rate(amount, duration):
    """Retourne le coefficient (%) Grenke pour un montant et une duree donnes."""
    index, _label = _get_grenke_tranche(amount)
    rates = GRENKE_RATES.get(duration)
    if index is None or not rates:
        return 0.0
    return rates[index]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # -- Disponibilite par societe (XEFI uniquement) ------------------------
    grenke_company_enabled = fields.Boolean(
        related='company_id.grenke_leasing_enabled',
        string='Leasing Grenke disponible pour la société',
    )

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
        help="Montant net HT a soumettre au leasing. Rempli automatiquement avec "
             "le total HT du devis, sauf si la saisie manuelle est activee.",
    )
    leasing_amount_override = fields.Boolean(
        string='Saisir manuellement le montant a financer',
        default=False,
        help="Si coche, le montant a financer n'est plus synchronise "
             "automatiquement avec le total HT du devis.",
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
    leasing_dossier_fee_override = fields.Boolean(
        string='Modifier manuellement les frais de dossier',
        default=False,
    )
    leasing_dossier_fee_manual = fields.Float(
        string='Frais de dossier manuels (CHF)',
        digits=(10, 2),
        help="Utilise a la place du forfait de CHF 200.- si la saisie manuelle "
             "est activee (0 autorise).",
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
    leasing_dossier_fee = fields.Float(
        string='Frais de dossier HT (CHF)',
        compute='_compute_leasing',
        store=True,
        digits=(10, 2),
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
        'amount_untaxed',
        'leasing_amount',
        'leasing_amount_override',
        'leasing_duration',
        'leasing_dossier_fee_override',
        'leasing_dossier_fee_manual',
    )
    def _compute_leasing(self):
        for order in self:
            # Auto-sync du montant a financer avec le total HT du devis,
            # sauf si le commercial a active la saisie manuelle.
            if (order.leasing_enabled
                    and not order.leasing_amount_override
                    and order.amount_untaxed):
                order.leasing_amount = order.amount_untaxed

            if not order.leasing_enabled or not order.leasing_amount:
                order.leasing_rate = 0.0
                order.leasing_monthly = 0.0
                order.leasing_total_rent = 0.0
                order.leasing_dossier_fee = 0.0
                order.leasing_grand_total = 0.0
                order.leasing_overcost = 0.0
                order.leasing_overcost_pct = 0.0
                order.leasing_tranche_label = ''
                order.leasing_duration_int = 0
                continue

            amount = order.leasing_amount
            duration = int(order.leasing_duration or '36')

            # Coefficient et tranche Grenke (une seule recherche)
            index, label = _get_grenke_tranche(amount)
            rate = _get_grenke_rate(amount, duration)
            order.leasing_rate = rate
            order.leasing_duration_int = duration
            order.leasing_tranche_label = label

            # Mensualite et total loyers
            monthly = amount * rate / 100.0
            order.leasing_monthly = monthly
            total_rent = monthly * duration
            order.leasing_total_rent = total_rent

            # Frais de dossier : forfait CHF 200.- ou saisie manuelle (0 autorise)
            if order.leasing_dossier_fee_override:
                fee = order.leasing_dossier_fee_manual
            else:
                fee = GRENKE_DOSSIER_FEE
            order.leasing_dossier_fee = fee

            # Cout total et surcout (usage interne ; absents du rapport client)
            grand_total = total_rent + fee
            order.leasing_grand_total = grand_total
            order.leasing_overcost = grand_total - amount
            order.leasing_overcost_pct = (
                (grand_total - amount) / amount * 100.0
            ) if amount else 0.0

    @api.constrains('leasing_amount', 'leasing_enabled')
    def _check_leasing_amount(self):
        for order in self:
            if order.leasing_enabled and order.leasing_amount:
                if (order.leasing_amount < GRENKE_MIN_AMOUNT
                        or order.leasing_amount > GRENKE_MAX_AMOUNT):
                    raise ValidationError(
                        "Au-dela de CHF 100'000, contactez votre interlocuteur "
                        "Grenke. Le montant a financer doit etre compris entre "
                        "CHF 1'000 et CHF 99'999 selon le bareme Super Lease."
                    )

    @api.constrains('leasing_dossier_fee_manual')
    def _check_leasing_dossier_fee_manual(self):
        for order in self:
            if order.leasing_dossier_fee_manual < 0:
                raise ValidationError(
                    "Les frais de dossier ne peuvent pas etre negatifs."
                )

    # -- Rapport dedie (bouton, visible seulement si la societe a le leasing) --
    def action_print_grenke_report(self):
        self.ensure_one()
        if not self.company_id.grenke_leasing_enabled:
            raise ValidationError("Le financement Grenke n'est pas disponible pour la société %s." % self.company_id.name)
        if not self.leasing_enabled:
            raise ValidationError("Active d'abord l'option leasing Grenke sur ce devis.")
        return self.env.ref('sale_grenke_leasing.action_report_saleorder_leasing').report_action(self)
