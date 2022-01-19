# -*- coding: utf-8 -*-
{
    'name': "Pantaq",
    'summary': "Module created for Pantaq to handle Procurement process",
    'sequence': 55,
    'author': 'Systems Valley Ltd.,',
    'description': """
Pantaq
====================
Handles Logistics and Supply Chain process to aid Procurement specialists,
who help companies achieve substantial cost savings on any area of spend.


    """,
    'website': 'https://www.pantaq.com',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Logistics and Supply Chain',
    'version': '1.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm', 'sale_crm', 'uom', 'purchase', 'hr', 'delivery_hs_code', 'stock', 'web'],

    # always loaded
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
        # 'views/enquiry_assets.xml',

        'report/report_layout.xml',
        'report/purchase_order_templates.xml',
        'report/purchase_quotation_templates.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'uninstall_hook': 'delete_group',
    'sequence': 1,
}
