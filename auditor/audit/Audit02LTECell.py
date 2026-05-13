from auditor.audit.GSAuditBase import GSAuditBase


class Audit02LTECell(GSAuditBase):
    def generate_audit_report(self):
        if len([_ for _ in self.usid.sites if len(self.usid.sites.get(_).enb) > 0]) > 0:
            self.gs_audit_for_lte_cell()
            # self.admin_missing_gs_audit_for_lte_cell()
    
    def gs_audit_for_lte_cell(self):
        skip_moc = [
            'GNBCUCPFunction', 'GNBDUFunction', 'GNBCUUPFunction', 'Cdma20001xRttBandRelation', 'Cdma2000FreqBandRelation',
            'EUtranFreqRelation', 'EUtranFreqRelationUnlicensed', 'GUtranFreqRelation', 'GeranFreqGroupRelation', 'UtranFreqRelation',
            'UtranTDDFreqRelation'
        ]
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if len(site.enb) == 0: continue
            all_cell_mo = site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellFDD') + site.get_mos_with_parent_moc(
                parent=site.enb, moc='EUtranCellTDD') + site.get_mos_with_parent_moc(parent=site.enb, moc='NbIotCell')
            for cell_mo in all_cell_mo[:]:
                cell = cell_mo.split('=')[-1]
                self.air = 1 if self.usid.param_dict['sites'][site.siteid]['cells'][cell]['OnAir'] else 0
                c_mos = [_ for _ in site.mo_list if _.startswith(cell_mo) and len([i for i in skip_moc if F',{skip_moc}=' in _]) == 0]
                sec_mo = self.usid.param_dict.get('sites').get(site.siteid).get('cells').get(cell).get('sec_mo')
                if sec_mo not in ['', None, 'None']: c_mos += sec_mo
                for mo in c_mos:
                    para_dict = site.dcg.get(mo, {})
                    for row_gs in self.df_gs.loc[(self.df_gs.MOC == mo.split(',')[-1].split('=')[0])].itertuples():
                        if F'{mo}.{row_gs.Parameter}' in self.process_list: continue
                        if self.logic.evaluate(row_gs.Logic, cell=cell, site=site.siteid, mo_level='cell'):
                            self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)
    
    def admin_missing_gs_audit_for_lte_cell(self):
        skip_moc = [
            'GNBCUCPFunction', 'GNBDUFunction', 'GNBCUUPFunction', 'Cdma20001xRttBandRelation', 'Cdma2000FreqBandRelation',
            'EUtranFreqRelation', 'EUtranFreqRelationUnlicensed', 'GUtranFreqRelation', 'GeranFreqGroupRelation', 'UtranFreqRelation',
            'UtranTDDFreqRelation'
        ]
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if len(site.enb) == 0: continue
            all_cell_mo = site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellFDD') + site.get_mos_with_parent_moc(
                parent=site.enb, moc='EUtranCellTDD') + site.get_mos_with_parent_moc(parent=site.enb, moc='NbIotCell')
            for cell_mo in all_cell_mo[:]:
                cell = cell_mo.split('=')[-1]
                self.air = 1 if self.usid.param_dict['sites'][site.siteid]['cells'][cell]['OnAir'] else 0
                c_mos = [_ for _ in site.mo_list if _.startswith(cell_mo) and len([i for i in skip_moc if F',{skip_moc}=' in _]) == 0]
                sec_mo = self.usid.param_dict.get('sites').get(site.siteid).get('cells').get(cell).get('sec_mo')
                if sec_mo not in ['', None, 'None']: c_mos += sec_mo
                for mo in c_mos:
                    for para in self.df_gs.loc[(self.df_gs.MOC == mo.split(',')[-1].split('=')[0])].Parameter.unique():
                        if F'{mo}.{para}' not in self.process_list:
                            self.r_list_for_missing_gs_para(site.siteid, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)
