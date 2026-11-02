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
        """Ambil pembacaan timbangan terakhir (dari MQTT) dan isi quantity move."""
        reading = self.env['iot.scale.reading'].search([], limit=1)
        for picking in self:
            weight = reading.weight if reading else picking.iot_net_weight
            if weight <= 0:
                raise UserError(
                    "Belum ada data timbangan. Pastikan subscriber MQTT jalan dan "
                    "sudah ada pesan di topic factory/plant_1/line_1/scale_weight."
                )
            # ponytail: asumsi 1 baris produk per receipt; perlu logika
            # pembagian kalau nanti receipt multi-produk.
            moves = picking.move_ids
            if len(moves) != 1:
                raise UserError("Isi berat IoT hanya untuk receipt dengan 1 baris produk.")
            picking.iot_net_weight = weight
            moves.quantity = weight
        return True
