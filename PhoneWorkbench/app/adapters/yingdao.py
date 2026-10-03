class YingdaoAdapter:
    """Integration boundary. No undocumented Yingdao API is assumed."""

    def health(self):
        return {
            'connected': False,
            'mode': 'not_configured',
            'message': '影刀尚未接入；设备连接状态待确认',
            'capabilities': [],
        }

    def inspect_device(self, serial):
        raise NotImplementedError('请先核实影刀版本、套餐及连接手机指令')
