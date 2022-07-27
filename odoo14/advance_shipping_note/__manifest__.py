# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Shipment',
    'summary': "Create Shipments of Purchase Order and align stock transfer as per shipments",
    'author': "Brain Station 23 LTD",
    'website': "https://www.brainstation-23.com",

    'license': 'OPL-1',
    'category': 'Purchase',
    'version': '14.0.0.1',

    'depends': ['base','purchase','stock'],
    'data': [
        'security/ir.model.access.csv',
        'security/purchase_order_shipment_security.xml',

        'data/data.xml',

        'views/purchase_order.xml',
        'views/purchase_order_shipment.xml',
        'views/stock_picking.xml',
    ],
    'images': ['/static/description/images/banner.gif'],

    'application': True,
    'installable': True,
    'currency': 'USD'
}


