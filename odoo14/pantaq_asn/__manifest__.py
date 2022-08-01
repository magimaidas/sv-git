# -*- coding: utf-8 -*-
{
    'name': 'Advance shipping note',
    'summary': "Create ASN of Purchase Order and align stock transfer as per shipments",
    'author': "Systems Valley",
    'website': 'https://www.pantaq.com',
    'category': 'Logistics and Supply Chain',
    'category': 'Purchase',
    'version': '14.0.0.1',
    'depends': ['base','purchase','stock','pantaq'],
    'data': [
        'security/ir.model.access.csv',
        'security/purchase_order_shipment_security.xml',
        'data/data.xml',
        'views/purchase_order.xml',
        'views/purchase_order_shipment.xml',
        'views/stock_picking.xml',
        'views/stock_scrap.xml',
    ],

    'application': True,
    'installable': True,
    'post_init_hook': '_warehouse_settings',
    'sequence': 1,

}


