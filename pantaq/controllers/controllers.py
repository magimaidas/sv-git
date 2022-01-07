# -*- coding: utf-8 -*-
from odoo import http

# class Pantaq(http.Controller):
#     @http.route('/pantaq_old/pantaq_old/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pantaq_old/pantaq_old/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pantaq_old.listing', {
#             'root': '/pantaq_old/pantaq_old',
#             'objects': http.request.env['pantaq_old.pantaq_old'].search([]),
#         })

#     @http.route('/pantaq_old/pantaq_old/objects/<model("pantaq_old.pantaq_old"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pantaq_old.object', {
#             'object': obj
#         })