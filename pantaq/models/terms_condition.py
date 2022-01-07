# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class TermsCondition(models.Model):
    _name = 'terms.condition'

    name = fields.Char(string="Description", compute='_get_terms_conditions')
    terms_condition = fields.Html(string="Terms & Condition")
    company_id = fields.Many2one('res.company', string="Company")

    def _get_terms_conditions(self):
        for firm in self:
            firm.name = "Terms & Condition for " + "'" + firm.company_id.name + "'"
