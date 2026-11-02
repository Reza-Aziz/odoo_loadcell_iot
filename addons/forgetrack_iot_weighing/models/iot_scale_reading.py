from odoo import fields, models


class IotScaleReading(models.Model):
    _name = 'iot.scale.reading'
    _description = 'Pembacaan Timbangan IoT'
    _order = 'received_at desc, id desc'

    topic = fields.Char(string="Topic MQTT", required=True, index=True)
    weight = fields.Float(string="Berat (kg)", digits=(16, 2))
    received_at = fields.Datetime(string="Diterima", default=fields.Datetime.now, required=True)
