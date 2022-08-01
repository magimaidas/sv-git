from odoo import SUPERUSER_ID, _, api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    attachment = fields.Image('Attachment', compute='_compute_attachment',help='Picture of product during return', readonly=True, store=True,copy=False, attachment=True)

    def _compute_attachment(self):
        if self:
            self.ensure_one()
            return_pick = self.env['stock.return.picking.line']
            self.attachment = self.picking_id.attachment
        print(self)

    # @api.onchange('lot_ids')
    # def _onchange_lot_ids(self):
    #     quantity_done = sum(ml.product_uom_id._compute_quantity(ml.qty_done, self.product_uom) for ml in
    #                         self.move_line_ids.filtered(lambda ml: not ml.lot_id and ml.lot_name))
    #     quantity_done += self.product_id.uom_id._compute_quantity(len(self.lot_ids), self.product_uom)
    #     self.update({'quantity_done': quantity_done})
    #     used_lots = self.env['stock.move.line'].search([
    #         ('company_id', '=', self.company_id.id),
    #         ('product_id', '=', self.product_id.id),
    #         ('lot_id', 'in', self.lot_ids.ids),
    #         ('move_id', '!=', self._origin.id),
    #         ('state', '!=', 'cancel')
    #     ])
    #     if used_lots:
    #         return {
    #             'warning': {'title': _('Warning'), 'message': _(
    #                 'Existing Serial numbers (%s). Please correct the serial numbers encoded.') % ','.join(
    #                 used_lots.lot_id.mapped('display_name'))}
    #         }
    #
    # @api.onchange('move_line_ids', 'move_line_nosuggest_ids')
    # def onchange_move_line_ids(self):
    #     if not self.picking_type_id.use_create_lots:
    #         # This onchange manages the creation of multiple lot name. We don't
    #         # need that if the picking type disallows the creation of new lots.
    #         return
    #
    #     breaking_char = '\n'
    #     if self.picking_type_id.show_reserved:
    #         move_lines = self.move_line_ids
    #     else:
    #         move_lines = self.move_line_nosuggest_ids
    #
    #     for move_line in move_lines:
    #         # Look if the `lot_name` contains multiple values.
    #         if breaking_char in (move_line.lot_name or ''):
    #             split_lines = move_line.lot_name.split(breaking_char)
    #             split_lines = list(filter(None, split_lines))
    #             move_line.lot_name = split_lines[0]
    #             move_lines_commands = self._generate_serial_move_line_commands(
    #                 split_lines[1:],
    #                 origin_move_line=move_line,
    #             )
    #             if self.picking_type_id.show_reserved:
    #                 self.update({'move_line_ids': move_lines_commands})
    #             else:
    #                 self.update({'move_line_nosuggest_ids': move_lines_commands})
    #             existing_lots = self.env['stock.production.lot'].search([
    #                 ('company_id', '=', self.company_id.id),
    #                 ('product_id', '=', self.product_id.id),
    #                 ('name', 'in', split_lines),
    #             ])
    #             if existing_lots:
    #                 return {
    #                     'warning': {'title': _('Warning'), 'message': _(
    #                         'Existing Serial Numbers (%s). Please correct the serial numbers encoded.') % ','.join(
    #                         existing_lots.mapped('display_name'))}
    #                 }
    #             break
    #
    # def action_show_details(self):
    #     """ Returns an action that will open a form view (in a popup) allowing to work on all the
    #     move lines of a particular move. This form view is used when "show operations" is not
    #     checked on the picking type.
    #     """
    #     self.ensure_one()
    #
    #     picking_type_id = self.picking_type_id or self.picking_id.picking_type_id
    #
    #     # If "show suggestions" is not checked on the picking type, we have to filter out the
    #     # reserved move lines. We do this by displaying `move_line_nosuggest_ids`. We use
    #     # different views to display one field or another so that the webclient doesn't have to
    #     # fetch both.
    #     if picking_type_id.show_reserved:
    #         view = self.env.ref('stock.view_stock_move_operations')
    #     else:
    #         view = self.env.ref('stock.view_stock_move_nosuggest_operations')
    #
    #     return {
    #         'name': _('Detailed Operations'),
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'res_model': 'stock.move',
    #         'views': [(view.id, 'form')],
    #         'view_id': view.id,
    #         'target': 'new',
    #         'res_id': self.id,
    #         'domain': [('lost_reason', 'in', self.ids)],
    #         'context': dict(
    #             self.env.context,
    #             show_owner=self.picking_type_id.code != 'incoming',
    #             show_lots_m2o=self.has_tracking != 'none' and (
    #                         picking_type_id.use_existing_lots or self.state == 'done' or self.origin_returned_move_id.id),
    #             # able to create lots, whatever the value of ` use_create_lots`.
    #             show_lots_text=self.has_tracking != 'none' and picking_type_id.use_create_lots and not picking_type_id.use_existing_lots and self.state != 'done' and not self.origin_returned_move_id.id,
    #             show_source_location=self.picking_type_id.code != 'incoming',
    #             show_destination_location=self.picking_type_id.code != 'outgoing',
    #             show_package=not self.location_id.usage == 'supplier',
    #             show_reserved_quantity=self.state != 'done' and not self.picking_id.immediate_transfer and self.picking_type_id.code != 'incoming'
    #         ),
    #     }
    #
    # @api.depends('move_line_ids', 'move_line_ids.lot_id', 'move_line_ids.qty_done')
    # def _compute_lot_ids(self):
    #     domain_nosuggest = [('move_id', 'in', self.ids), ('lot_id', '!=', False), '|', ('qty_done', '!=', 0.0),
    #                         ('product_qty', '=', 0.0)]
    #     domain_suggest = [('move_id', 'in', self.ids), ('lot_id', '!=', False), ('qty_done', '!=', 0.0)]
    #     lots_by_move_id_list = []
    #     for domain in [domain_nosuggest, domain_suggest]:
    #         lots_by_move_id = self.env['stock.move.line'].read_group(
    #             domain,
    #             ['move_id', 'lot_ids:array_agg(lot_id)'], ['move_id'],
    #         )
    #         lots_by_move_id_list.append({by_move['move_id'][0]: by_move['lot_ids'] for by_move in lots_by_move_id})
    #     for move in self:
    #         move.lot_ids = lots_by_move_id_list[0 if move.picking_type_id.show_reserved else 1].get(move._origin.id, [])
    #     if self.picking_code == 'outgoing':
    #         so = self.env['sale.order'].search([('name', '=', self.origin)])
    #         po_ids = so.lead_id.purchase_ids.filtered(lambda x: x.state in ('purchase'))
    #         if po_ids:
    #             for po in po_ids:
    #                 move_lines = po.picking_ids.mapped('move_line_ids')
    #                 lot_ids = move_lines.mapped('lot_id')
    #             lot_ids = lot_ids.filtered(lambda m: m.product_qty != 0)
    #             domain = {'move_ids_without_package.lot_id': [('id', 'in', lot_ids.ids)]}
    #             return {'domain': domain}
    #
    #     for res in self:
    #         if res.state not in ('done', 'cancel') and 'Return' in res.display_name:
    #             move_lines = res.picking_id.mapped('move_line_ids')
    #             lot_ids = move_lines.mapped('lot_id')
    #             lot_ids = lot_ids.filtered(lambda m: m.product_qty != 0)
    #             # Das modified here
    #             domain = {'lot_id': [('id', 'in', lot_ids.ids)]}
    #             res.lot_ids = lot_ids.ids
    #             return {'domain': domain}
