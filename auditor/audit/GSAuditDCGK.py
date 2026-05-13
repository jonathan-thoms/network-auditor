import re
import sys


class GSAuditDCGK:
    def __init__(self, siteid, merged_dict):
        self.dnprefix = ''
        self.siteid = siteid
        self.dcg = merged_dict
        self.mo_list = sorted([_ for _ in self.dcg.keys()])
        if len(self.dcg) < 1 or len(self.mo_list) < 1:
            sys.exit(1)

        self.equipment_type, self.audit_type_str, self.equipment_name = 'BB', 'G3', '6648'
        self.set_equipment_type_audit_type()

        self.enb, self.enodeb_id, self.enb_enw, self.enb_gnw = '', '', '', ''
        enb = self.get_mos_with_moc(moc='ENodeBFunction')
        if len(enb) > 0:
            self.enb = enb[0]
            self.enodeb_id = self.get_mo_data(self.enb).get('eNBId', '')
            nw_mo = self.get_mos_with_parent_moc(parent=self.enb, moc='EUtraNetwork')
            self.enb_enw = nw_mo[0] if len(nw_mo) > 0 else F'{self.enb},EUtraNetwork=1'
            nw_mo = self.get_mos_with_parent_moc(parent=self.enb, moc='GUtraNetwork')
            self.enb_gnw = nw_mo[0] if len(nw_mo) > 0 else F'{self.enb},GUtraNetwork=1'

        self.gnb, self.gnodeb_id, self.gnodeb_length, self.gnb_cucp = '', '', '', ''
        self.gnb_enw, self.gnb_nnw = '', ''
        gnb = self.get_mos_with_moc(moc='GNBDUFunction')
        if len(gnb) > 0:
            self.gnb = gnb[0]
            self.gnodeb_id = self.get_mo_data(self.gnb).get('gNBId', '')
            self.gnodeb_length = self.get_mo_data(self.gnb).get('gNBIdLength', '')
            if len(self.get_mos_with_moc(moc='GNBCUCPFunction')) > 0:
                self.gnb_cucp = self.get_mos_with_moc(moc='GNBCUCPFunction')[0]
                nw_mo = self.get_mos_with_parent_moc(parent=self.gnb_cucp, moc='EUtraNetwork')
                self.gnb_enw = nw_mo[0] if len(nw_mo) > 0 else F'{self.gnb_cucp},EUtraNetwork=1'
                nw_mo = self.get_mos_with_parent_moc(parent=self.gnb_cucp, moc='NRNetwork')
                self.gnb_nnw = nw_mo[0] if len(nw_mo) > 0 else F'{self.gnb_cucp},NRNetwork=1'
                
        if len(self.enb) > 0:
            self.dnprefix = self.enb.split(',ENodeBFunction=')[0]
        elif len(self.gnb) > 0:
            self.dnprefix = self.gnb.split(',GNBDUFunction=')[0]

    def set_equipment_type_audit_type(self):
        self.equipment_type = 'BB' if len([_ for _ in self.mo_list if ('FieldReplaceableUnit=' in _)]) > 0 else 'DUS'
        equipment_moc = 'FieldReplaceableUnit' if self.equipment_type == 'BB' else 'Slot'
        mos = self.get_mos_with_moc(moc=equipment_moc)
        if len(mos) == 0: return None, None
        for mo in mos:
            equipment_name = self.dcg.get(mo).get('productData', {}).get('productName', '')
            if equipment_name is not None:
                if '5216' in equipment_name:  self.equipment_name, self.audit_type_str = '5216', 'G2'
                elif '6630' in equipment_name: self.equipment_name, self.audit_type_str = '6630', 'G2'
                elif '6648' in equipment_name: self.equipment_name, self.audit_type_str = '6648', 'G3'
                elif '6651' in equipment_name: self.equipment_name, self.audit_type_str = '6651', 'G3'
                elif '6672' in equipment_name: self.equipment_name, self.audit_type_str = '6672', 'G4'
                elif 'DUS' in equipment_name: self.equipment_name, self.audit_type_str = 'DUS', 'G1'
                elif 'DUL' in equipment_name: self.equipment_name, self.audit_type_str = 'DUL', 'G1'
                if self.equipment_name is not None: break

    def get_mo_data(self, mo): return self.dcg.get(mo, {})
    def get_mo_para(self, mo, para): return self.dcg.get(mo, {}).get(para, 'N/F')

    def get_mos_with_moc(self, moc): return [_ for _ in self.mo_list if re.match(F'.*,{moc}=[^,=]*$', _)]
    def get_mos_with_moc_moid(self, mo, moid): return [_ for _ in self.mo_list if re.match(F'.*,{mo}={moid}$', _)]
    def get_mos_with_parent_moc(self, parent='', moc=''): return [_ for _ in self.mo_list if re.match(F'{parent},{moc}=[^,=]*$', _)]
    def get_mos_with_parent_moc_moid(self, parent='', moc='', moid=''): return [_ for _ in self.mo_list if re.match(F'{parent},{moc}={moid}$', _)]
    def get_mos_with_endstr(self, end_str): return [_ for _ in self.mo_list if _.endswith(F',{end_str}')]
    def get_mos_and_its_child_with_mo(self, mo): return [mo] + [_ for _ in self.mo_list if re.match(F'{mo},', _)] if len(mo) > 0 else []

    def get_first_mo_from_ref_parameter(self, mo):
        if mo in [None, 'None', '', 'N/F', [], {}]: mo = ''
        elif type(mo) == str: mo = [_ for _ in self.mo_list if _.endswith(mo)][0]
        elif (type(mo) == list) and (len(mo) > 0): return [_ for _ in self.mo_list if _.endswith(mo[0])][0]
        return '' if mo in [None, 'None', '', [], {}] else mo

    def get_berrer_info(self): pass
