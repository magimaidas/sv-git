# Copyright 2014 Serv. Tec. Avanzados - Pedro M. Baeza
# Copyright 2014 Oihane Crucelaegui - AvanzOSC
# Copyright 2018 Simone Rubino - Agile Business Group
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Pantaq Stock Quality",
    "version": "14.0.1.0.0",
    "category": "Quality control",
    "license": "AGPL-3",
    "author": "",
    "website": "",
    "depends": ["pantaq_quality_control", "stock"],
    "data": [
        "views/qc_inspection_view.xml",
        "views/stock_picking_view.xml",
        "views/stock_production_lot_view.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": True,
}
