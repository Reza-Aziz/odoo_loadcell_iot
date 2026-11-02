from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    iot_net_weight = fields.Float(
        string="Berat Aktual IoT (kg)",
        digits=(16, 3),
        help="Data berat aktual dari simulasi Wokwi/IoT Scale",
        tracking=True,
    )
    iot_latest_weight = fields.Float(
        string="Timbangan Terakhir (kg)", digits=(16, 3),
        compute='_compute_iot_latest', help="Pembacaan terakhir dari MQTT")
    iot_latest_time = fields.Datetime(
        string="Waktu Timbangan", compute='_compute_iot_latest')
    is_iot_verified = fields.Boolean(
        string="Terverifikasi IoT", tracking=True,
        help="True kalau berat IoT sudah dipindah ke quantity lewat tombol.")

    @api.depends()
    def _compute_iot_latest(self):
        reading = self.env['iot.scale.reading'].search([], limit=1)
        for picking in self:
            picking.iot_latest_weight = reading.weight
            picking.iot_latest_time = reading.received_at

    def action_get_iot_weight(self):
        """Ambil pembacaan timbangan terakhir (dari MQTT) dan isi quantity move."""
        reading = self.env['iot.scale.reading'].search([], limit=1)
        for picking in self:
            weight = reading.weight if reading else picking.iot_net_weight
            if weight <= 0:
                if reading:
                    raise UserError(
                        "Berat terbaca %s kg, harus > 0. Kalibrasi/tare timbangan dulu."
                        % weight)
                raise UserError(
                    "Belum ada data timbangan. Pastikan mqtt_bridge.py jalan dan "
                    "sudah ada pesan di topic factory/plant_1/line_1/scale_weight.")
            # ponytail: asumsi 1 baris produk per receipt; perlu logika
            # pembagian kalau nanti receipt multi-produk.
            moves = picking.move_ids
            if len(moves) != 1:
                raise UserError("Isi berat IoT hanya untuk receipt dengan 1 baris produk.")
            picking.iot_net_weight = weight
            picking.is_iot_verified = True
            moves.quantity = weight
        return True
