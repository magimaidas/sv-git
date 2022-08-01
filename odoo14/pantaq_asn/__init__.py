# -*- coding: utf-8 -*-

from . import models
from odoo import api, fields, models, _
from odoo import api, SUPERUSER_ID
from odoo.exceptions import UserError


def _warehouse_settings(cr, registry):
    """ This hook is used to add a default settings and warehouse two-step receiving method
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    res_config_id = env['res.config.settings'].create({
        'group_stock_adv_location': True,
        'group_stock_production_lot': True,
    })
    res_config_id.execute()
    warehouse_ids = env['stock.warehouse'].search([('active', '=', True)])
    if warehouse_ids:
        warehouse_ids[0].sudo().write({'reception_steps': 'two_steps'})
    else:
        raise UserError(_('No warehouse found! Configure a warehouse to continue...'))

