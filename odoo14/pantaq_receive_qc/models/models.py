# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo import _, _lt, api, fields, models
from odoo.exceptions import UserError


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    def _get_sequence_values(self):
        """ Each picking type is created with a sequence. This method returns
        the sequence values associated to each picking type.
        """
        return {
            'in_type_id': {
                'name': self.name + ' ' + _('Sequence in'),
                'prefix': self.code + '/IN/', 'padding': 5,
                'company_id': self.company_id.id,
            },
            'out_type_id': {
                'name': self.name + ' ' + _('Sequence out'),
                'prefix': self.code + '/OUT/', 'padding': 5,
                'company_id': self.company_id.id,
            },
            'pack_type_id': {
                'name': self.name + ' ' + _('Sequence packing'),
                'prefix': self.code + '/PACK/', 'padding': 5,
                'company_id': self.company_id.id,
            },
            'pick_type_id': {
                'name': self.name + ' ' + _('Sequence picking'),
                'prefix': self.code + '/PICK/', 'padding': 5,
                'company_id': self.company_id.id,
            },
            'int_type_id': {
                'name': self.name + ' ' + _('Sequence internal'),
                'prefix': self.code + '/QC/', 'padding': 5,
                'company_id': self.company_id.id,
            },
        }
