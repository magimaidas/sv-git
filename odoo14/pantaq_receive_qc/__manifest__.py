# -*- coding: utf-8 -*-
{
    'name': "pantaq_receive_qc",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Systems Valley Pvt. Ltd.",
    'website': "http://www.systemsvalley.co.in",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','pantaq','purchase','purchase_stock','delivery','stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'data/data.xml',
        'views/templates.xml',
        'data/data.xml',
        'views/purchase_order.xml',
        'views/inventory_asn_menu.xml',
        'views/stock_picking.xml',
        'views/lot_filtering.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1,
    'post_init_hook': '_warehouse_settings',
}