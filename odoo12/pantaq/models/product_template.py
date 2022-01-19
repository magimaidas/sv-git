# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools import pycompat
from odoo.tools.float_utils import float_round
from datetime import datetime



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    asin_number = fields.Char(string="ASIN")
    part_number = fields.Char(string="Part Number")
    sku_number = fields.Char(string="SKU")
    upc_number = fields.Char(string="UPC")