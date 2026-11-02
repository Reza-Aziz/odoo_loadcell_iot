from odoo import fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    iot_net_weight = fields.Float(
        string="Berat Aktual IoT (kg)",
        digits=(16, 2),
        help="Data berat aktual dari simulasi Wokwi/IoT Scale",
        tracking=True,
    )

    def action_get_iot_weight(self):
        """Salin iot_net_weight ke quantity detail move."""
        for picking in self:
            if picking.iot_net_weight <= 0:
                continue
            moves = picking.move_ids
            # ponytail: asumsi 1 baris produk per receipt; perlu logika
            # pembagian kalau nanti receipt multi-produk.
            if len(moves) != 1:
                raise UserError("Isi berat IoT hanya untuk receipt dengan 1 baris produk.")
            moves.quantity = picking.iot_net_weight
        return True
