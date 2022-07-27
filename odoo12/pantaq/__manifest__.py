# -*- coding: utf-8 -*-
{
    'name': "Pantaq",
    'summary': "Module created for Pantaq to handle Procurement process",
    'author': 'Systems Valley Ltd.,',
    'license' : 'OPL-1',
    'maintainer':'Systems Valley Pvt Ltd.,',
    'description': """
Pantaq
====================
Handles Logistics and Supply Chain process to aid Procurement specialists,
who help companies achieve substantial cost savings on any area of spend.

    """,
    'website': 'https://www.pantaq.com',
    'category': 'Logistics and Supply Chain',
    'version': '1.1',
    'depends': ['base', 'crm', 'sale_crm', 'uom', 'purchase', 'hr', 'delivery_hs_code', 'stock', 'web'],

    'data': [
        'data/data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/crm_stage_data.xml',
        'data/email_templates.xml',
        'data/procurement_email_templates.xml',
        'wizard/wizard_view.xml',
        'wizard/wizard_response_confirmation_view.xml',
        'views/config_view.xml',
        'views/crm_views.xml',
        'views/purchase_views.xml',
        'views/internal_quotation_view.xml',
        'views/terms_condition_view.xml',
        'views/sale_views.xml',
        'views/templates.xml',
        'views/account_invoice_view.xml',
        'views/product_template_views.xml',
        'report/report_layout.xml',
        'report/purchase_order_templates.xml',
        'report/purchase_quotation_templates.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'uninstall_hook': 'delete_group',
    'sequence':1,
}
