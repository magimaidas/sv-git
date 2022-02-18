# -*- coding: utf-8 -*-
# from odoo import http


# class PantaqWrf(http.Controller):
#     @http.route('/pantaq_wrf/pantaq_wrf/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pantaq_wrf/pantaq_wrf/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pantaq_wrf.listing', {
#             'root': '/pantaq_wrf/pantaq_wrf',
#             'objects': http.request.env['pantaq_wrf.pantaq_wrf'].search([]),
#         })

#     @http.route('/pantaq_wrf/pantaq_wrf/objects/<model("pantaq_wrf.pantaq_wrf"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pantaq_wrf.object', {
#             'object': obj
#         })
