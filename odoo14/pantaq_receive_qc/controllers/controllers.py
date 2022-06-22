# -*- coding: utf-8 -*-
# from odoo import http


# class PantaqReceiveQc(http.Controller):
#     @http.route('/pantaq_receive_qc/pantaq_receive_qc/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pantaq_receive_qc/pantaq_receive_qc/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pantaq_receive_qc.listing', {
#             'root': '/pantaq_receive_qc/pantaq_receive_qc',
#             'objects': http.request.env['pantaq_receive_qc.pantaq_receive_qc'].search([]),
#         })

#     @http.route('/pantaq_receive_qc/pantaq_receive_qc/objects/<model("pantaq_receive_qc.pantaq_receive_qc"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pantaq_receive_qc.object', {
#             'object': obj
#         })
