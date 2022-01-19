# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class Partner(models.Model):
    _inherit = 'res.partner'

    @api.depends('company_type','child_ids', 'parent_id')
    def _get_attention(self):
        """
        In Company: set the first Child Contact as Attention Partner
        """
        for case in self:
            if case.company_type == 'company':
                for c in case.child_ids:
                    case.attn_contact = c.name
                    break

            elif case.parent_id:
                case.parent_id.attn_contact = case.name

    vendor_type = fields.Selection([('manufacturer', 'Manufacturer'), ('reseller', 'Reseller')], string="Vendor Type", default='reseller')
    taxin_cost  = fields.Boolean('Include Tax in Cost', help='Set True, to add supplier taxes from RFQ to the Cost of IQ')
    attn_contact = fields.Char('Attention Contact', compute='_get_attention' )

    @api.model
    def default_get(self, fields):
        res = super(Partner, self).default_get(fields)
        res.update({'is_company': True}) # Setting partner type as company by default.
        return res

class Message(models.Model):
    _inherit = ['mail.message']

    @api.one
    @api.depends('author_id')
    def _get_UserGroups(self):

        AuthUser = self.env['res.users'].search([('partner_id', '=', self.author_id.id)])
        PurchaseGrp = self.sudo(AuthUser.id).user_has_groups('purchase.group_purchase_user')
        SalesGrp = self.sudo(AuthUser.id).user_has_groups('sales_team.group_sale_salesman')

        self.is_purchasegroup = True if (PurchaseGrp and not SalesGrp) else False

    is_purchasegroup = fields.Boolean(compute='_get_UserGroups', string='By Purchase Group', store=True)
    force_display = fields.Boolean('Force Display', default=False,
                                   help='Make it visible to both Sales & Purchase, overridding Domain')


class Company(models.Model):
    _inherit = 'res.company'

    include_tax_iq = fields.Boolean('Tax in Internal Quotation', help='Set True, to consider RFQ Taxes while creating an Internal Quotation from RFQ')
    code = fields.Char("Company Code", help="Specify 2 letter code of the company, the same will be considered for Reference Numbers")



    # Overridden:
    @api.onchange('report_footer', 'company_registry', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id')
    def onchange_footer(self):
        if not self.report_footer:
            # first line (notice that missing elements are filtered out before the join)
            res = ''
            res += '. '.join(filter(bool, [self.company_registry and '%s: %s ' % (_('Company Registration No'), self.company_registry)
                       ]))

            res += ', '.join(filter(bool, [
                self.street           and '%s: %s' % (_('Registered Office'), self.street),
                self.street2          and '%s' % (self.street2),
                self.city             and '%s' % (self.city),
                self.state_id         and '%s' % (self.state_id.name),
                self.zip              and '%s' % (self.zip),
                self.country_id       and '%s' % (self.country_id.name),
            ]))
            self.rml_footer_readonly = res
            self.rml_footer = res

class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_description = fields.Text('Product Description')