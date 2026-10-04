from auditor.audit.GSAuditBase import GSAuditBase
import pandas as pd


class Audit12NRCell(GSAuditBase):
    def generate_audit_report(self):
        if len([_ for _ in self.usid.sites if len(self.usid.sites.get(_).gnb) > 0 or len(self.usid.sites.get(_).gnb_cucp) > 0]) > 0:
            self.nrcell_dict = {
                'NRCellDU_skip_moc': ['GNBCUCPFunction', 'GNBCUUPFunction', 'ENodeBFunction'],
                'NRCellCU_skip_moc': ['EUtranCellRelation', 'EUtranFreqRelation', 'NRCellRelation', 'NRFreqRelation', 'GNBDUFunction',
                                      'GNBCUUPFunction', 'ENodeBFunction'],
                'NRCellDU_ref': [
                    'bWPRef', 'bWPSetRef', 'caSCellHandlingRef', 'cellPriorityShiftRef', 'cellResourceMappingRef', 'drxProfileRef', 'endcCgSwitchRef',
                    'endcUlCgSwitchRef', 'extCaPriorityRef', 'nRSectorCarrierRef', 'nrdcCgSwitchRef', 'nrdcUlCgSwitchRef', 'pdcchReuseForPdschRef',
                    'rachRef', 'resourceAllocTypeDlRef', 'rimAggressorRSSetRef', 'rimVictimRSSetRef', 'srPeriodicityPoolSetRef', 'srPeriodicityRef',
                    'ueBbProfileRef'
                ],
                'NRCellCU_ref': [
                    'caCellMeasProfileRef', 'caCellProfileRef', 'intraFreqMCCellProfileRef', 'mcfbCellProfileRef', 'mcpcNrdcPSCellProfileRef',
                    'mcpcPCellProfileRef', 'mcpcPSCellProfileRef', 'mdtCellProfileRef', 'nrdcMnCellProfileRef', 'pmUeIntraFreqCellProfileRef',
                    'trStPSCellProfileRef', 'trStSaCellProfileRef', 'ueMCCellProfileRef'
                ],
            }
            self.gs_audit_for_nrcell()
            # self.admin_missing_gs_audit_for_nrcell()

    def gs_audit_for_nrcell(self):
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if len(site.gnb) == 0: continue
            for moc in ['NRCellDU', 'NRCellCU']:
                parent = site.gnb if moc == 'NRCellDU' else site.gnb_cucp
                cells = site.get_mos_with_parent_moc(parent=parent, moc=moc)
                for cell_mo in cells[:]:
                    cell = cell_mo.split('=')[-1]
                    if cell not in self.usid.param_dict['sites'][site.siteid]['cells'].keys():
                        continue
                    self.air = 1 if self.usid.param_dict['sites'][site.siteid]['cells'][cell]['OnAir'] else 0
                    c_mos = [_ for _ in site.mo_list if _.startswith(cell_mo)]
                    # ref MOS additions
                    for para_ref in self.nrcell_dict[F'{moc}_ref']:
                        ref_mo = site.get_first_mo_from_ref_parameter(site.get_mo_para(cell_mo, para_ref))
                        if ref_mo not in [None, 'N/F', '', []]:
                            c_mos += site.get_mos_and_its_child_with_mo(ref_mo)
                            if moc == 'NRCellDU' and para_ref in ['endcCgSwitchRef', 'nrdcCgSwitchRef']:
                                for c_c_mo in [_ for _ in site.get_mos_and_its_child_with_mo(ref_mo) if ',CgSwitchUeCfg=' in _]:
                                    ref_mo_c = site.get_first_mo_from_ref_parameter(site.get_mo_para(c_c_mo, 'cgSwitchCfgRef'))
                                    if ref_mo_c not in [None, 'N/F', '', []]:
                                        c_mos += site.get_mos_and_its_child_with_mo(ref_mo_c)
                            if moc == 'NRCellDU' and para_ref in ['endcUlCgSwitchRef', 'nrdcUlCgSwitchRef']:
                                for c_c_mo in [_ for _ in site.get_mos_and_its_child_with_mo(ref_mo) if ',UlCgSwitchUeCfg=' in _]:
                                    ref_mo_c = site.get_first_mo_from_ref_parameter(site.get_mo_para(c_c_mo, 'ulCgSwitchCfgRef'))
                                    if ref_mo_c not in [None, 'N/F', '', []]:
                                        c_mos += site.get_mos_and_its_child_with_mo(ref_mo_c)

                    c_mos = [_ for _ in c_mos if len([_ for val in self.nrcell_dict[F'{moc}_skip_moc'] if F',{val}=' in _]) == 0]
                    for mo in c_mos:
                        para_dict = site.dcg.get(mo, {})
                        mo_no_id = mo.rsplit('=', 1)[0]
                        mo_last_moc = mo.split(',')[-1].split('=')[0]
                        mask = self.df_gs["MOC"].apply(lambda x: (
                            mo.endswith(x) or
                            mo_no_id == x or
                            mo_no_id.endswith(',' + x) or
                            x == mo_last_moc
                        ))
                        df_gs = self.df_gs.loc[mask].copy()
                        df_gs['GSValue'] = df_gs.GSValue.str.replace(r'NR__CELL__NAME$', cell, regex=True)
                        for row_gs in df_gs.itertuples():
                            if F'{mo}.{row_gs.Parameter}' in self.process_list: continue
                            if self.logic.evaluate(row_gs.Logic, cell=cell, site=site.siteid, mo_level='cell'):
                                self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def admin_missing_gs_audit_for_nrcell(self):
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if len(site.gnb_cucp) == 0:
                continue
            for moc in ['NRCellDU', 'NRCellCU']:
                parent = site.gnb if moc == 'NRCellDU' else site.gnb_cucp
                cells = site.get_mos_with_parent_moc(parent=parent, moc=moc)
                for cell_mo in cells[:]:
                    cell = cell_mo.split('=')[-1]
                    if cell not in self.usid.param_dict["sites"][site.siteid]["cells"].keys():
                        continue
                    self.air = 1 if self.usid.param_dict['sites'][site.siteid]['cells'][cell]['OnAir'] else 0
                    c_mos = [_ for _ in site.mo_list if _.startswith(cell_mo)]
                    for para_ref in self.nrcell_dict[F'{moc}_ref']:
                        ref_mo = site.get_first_mo_from_ref_parameter(site.get_mo_para(cell_mo, para_ref))
                        if ref_mo not in [None, 'N/F', '', []]:
                            c_mos += site.get_mos_and_its_child_with_mo(ref_mo)
                            if moc == 'NRCellDU' and para_ref in ['endcCgSwitchRef', 'nrdcCgSwitchRef']:
                                for c_c_mo in [_ for _ in site.get_mos_and_its_child_with_mo(ref_mo) if ',CgSwitchUeCfg=' in _]:
                                    ref_mo_c = site.get_first_mo_from_ref_parameter(site.get_mo_para(c_c_mo, 'cgSwitchCfgRef'))
                                    if ref_mo_c not in [None, 'N/F', '', []]:
                                        c_mos += site.get_mos_and_its_child_with_mo(ref_mo_c)
                            if moc == 'NRCellDU' and para_ref in ['endcUlCgSwitchRef', 'nrdcUlCgSwitchRef']:
                                for c_c_mo in [_ for _ in site.get_mos_and_its_child_with_mo(ref_mo) if ',UlCgSwitchUeCfg=' in _]:
                                    ref_mo_c = site.get_first_mo_from_ref_parameter(site.get_mo_para(c_c_mo, 'ulCgSwitchCfgRef'))
                                    if ref_mo_c not in [None, 'N/F', '', []]:
                                        c_mos += site.get_mos_and_its_child_with_mo(ref_mo_c)
                    c_mos = [_ for _ in c_mos if len([_ for val in self.nrcell_dict[F'{moc}_skip_moc'] if F',{val}=' in _]) == 0]
                    for mo in c_mos:
                        mo_no_id = mo.rsplit('=', 1)[0]
                        mo_last_moc = mo.split(',')[-1].split('=')[0]
                        mask = self.df_gs["MOC"].apply(lambda x: (
                            mo.endswith(x) or
                            mo_no_id == x or
                            mo_no_id.endswith(',' + x) or
                            x == mo_last_moc
                        ))
                        for para in self.df_gs.loc[mask].Parameter.unique():
                            if F'{mo}.{para}' not in self.process_list:
                                self.r_list_for_missing_gs_para(site.siteid, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)
