# -*- coding: utf-8 -*-

from . import controllers
from . import models

from odoo import api, SUPERUSER_ID


def _warehouse_settings(cr, registry):
    """ This hook is used to add a default settings and warehouse two-step receiving method
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    settings = env['res.config.settings']
    settings.write({'group_stock_adv_location': True})
    warehouse_ids = env['stock.warehouse'].search([('active', '=', True)])
    warehouse_ids[0].write({'reception_steps': 'two_steps'})


# def uninstall_hook(cr, registry):
#     cr.execute(
#         "delete from ir_model_data where module = 'pantaq_receive_qc'"
#     )

