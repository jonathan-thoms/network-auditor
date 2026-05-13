from auditor.audit.GSAuditBase import GSAuditBase


class Audit01LTE(GSAuditBase):
    def generate_audit_report(self):
        if len([_ for _ in self.usid.sites if len(self.usid.sites.get(_).enb) > 0]) > 0:
            self.gs_audit_for_lte_mos_with_ids()
            # self.admin_missing_gs_audit_for_lte_mos_with_ids()
            self.gs_audit_for_lte_mos_without_ids()
            # self.admin_missing_gs_audit_for_lte_mos_without_ids()
            self.gs_audit_for_lte_sctp()
            # self.admin_missing_gs_audit_for_lte_sctp()

    def gs_audit_for_lte_mos_with_ids(self):
        skip_moc = ['GNBCUCPFunction', 'GNBDUFunction', 'GNBCUUPFunction', 'SctpProfile', 'SctpEndpoint']
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' in _) and len([i for i in skip_moc if F'{i}=' in _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if site.enb == '':
                continue
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_endstr(site_level_mo):
                    if len([_ for _ in skip_moc if F',{_}=' in mo]) > 0:
                        continue
                    para_dict = site.dcg.get(mo, {})
                    for row_gs in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].itertuples():
                        if F'{mo}.{row_gs.Parameter}' in self.process_list: continue
                        # if self.logic.evaluate(row_gs.Logic, cell=None, site=site.siteid, mo_level='site'):
                        if self.logic.evaluate(row_gs.Logic, site=site.siteid, mo_level='site'):
                            self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def admin_missing_gs_audit_for_lte_mos_with_ids(self):
        skip_moc = ['GNBCUCPFunction', 'GNBDUFunction', 'GNBCUUPFunction', 'SctpProfile', 'SctpEndpoint']
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' in _) and len([i for i in skip_moc if F'{i}=' in _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if site.enb == '': continue
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_endstr(site_level_mo):
                    if len([_ for _ in skip_moc if F',{_}=' in mo]) > 0:
                        continue
                    for para in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].Parameter.unique():
                        if F'{mo}.{para}' not in self.process_list:
                            self.r_list_for_missing_gs_para(site.siteid, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)

    def gs_audit_for_lte_mos_without_ids(self):
        skip_moc = ['GNBCUCPFunction', 'GNBDUFunction', 'GNBCUUPFunction', 'SctpProfile', 'SctpEndpoint']
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' not in _) and len([i for i in skip_moc if i == _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if site.enb == '': continue
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_moc(moc=site_level_mo):
                    if len([_ for _ in skip_moc if F',{_}=' in mo]) > 0:
                        continue
                    para_dict = site.dcg.get(mo, {})
                    for row_gs in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].itertuples():
                        if F'{mo}.{row_gs.Parameter}' in self.process_list: continue
                        if self.logic.evaluate(row_gs.Logic, cell=None, site=site.siteid, mo_level='site'):
                            self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def admin_missing_gs_audit_for_lte_mos_without_ids(self):
        skip_moc = ['GNBCUCPFunction', 'GNBDUFunction', 'GNBCUUPFunction', 'SctpProfile', 'SctpEndpoint']
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' not in _) and len([i for i in skip_moc if i == _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if site.enb == '': continue
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_moc(moc=site_level_mo):
                    if len([_ for _ in skip_moc if F',{_}=' in mo]) > 0:
                        continue
                    for para in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].Parameter.unique():
                        if F'{mo}.{para}' not in self.process_list:
                            self.r_list_for_missing_gs_para(site.siteid, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)

    def gs_audit_for_lte_sctp(self):
        # skip_moc += ['SctpProfile=LTE_ID_VAL', 'SctpEndpoint=LTE_ID_VAL', ',SctpProfile=LTE_ID_VAL', ',SctpEndpoint=LTE_ID_VAL']
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if site.enb == '':
                continue
            df_gs = self.df_gs.copy().loc[self.df_gs.MOC.str.contains('SctpEndpoint=|SctpProfile=')]
            sctp_mos = []
            sctpendpoint_mo = site.get_first_mo_from_ref_parameter(site.get_mo_data(site.enb).get('sctpRef'))
            if len(sctpendpoint_mo) > 0:
                sctp_mos.append(sctpendpoint_mo)
                df_gs['MOC'] = df_gs.MOC.replace({"SctpEndpoint=LTE_ID_VAL": F'{sctpendpoint_mo.split(",")[-1]}'})
                sctpprofile_mo = site.get_first_mo_from_ref_parameter(site.get_mo_data(sctpendpoint_mo).get('sctpProfile'))
                if len(sctpprofile_mo) > 0:
                    df_gs['MOC'] = df_gs.MOC.replace({"SctpProfile=LTE_ID_VAL": F'{sctpprofile_mo.split(",")[-1]}'})
                    df_gs['GSValue'] = df_gs.GSValue.replace({"Transport=1,SctpProfile=LTE_ID_VAL": F'Transport=1,{sctpprofile_mo.split(",")[-1]}'})
                sctp_mos.append(sctpprofile_mo)
            for mo in sctp_mos:
                para_dict = site.dcg.get(mo, {})
                for row_gs in df_gs.loc[(df_gs.MOC == mo.split('=')[-1])].itertuples():
                    if F'{mo}.{row_gs.Parameter}' in self.process_list: continue
                    if self.logic.evaluate(row_gs.Logic, cell=None, site=site.siteid, mo_level='site'):
                        self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def admin_missing_gs_audit_for_lte_sctp(self):
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if site.enb == '':
                continue
            df_gs = self.df_gs.copy().loc[self.df_gs.MOC.str.contains('SctpEndpoint=|SctpProfile=')]
            sctp_mos = []
            sctpendpoint_mo = site.get_first_mo_from_ref_parameter(site.get_mo_data(site.enb).get('sctpRef'))
            if len(sctpendpoint_mo) > 0:
                df_gs.MOC.replace({"SctpEndpoint=LTE_ID_VAL": F'{sctpendpoint_mo.split(",")[-1]}'}, inplace=True)
                sctp_mos.append(sctpendpoint_mo)
                sctpprofile_mo = site.get_first_mo_from_ref_parameter(site.get_mo_data(sctpendpoint_mo).get('sctpProfile'))
                if len(sctpprofile_mo) > 0:
                    df_gs.MOC.replace({"SctpProfile=LTE_ID_VAL": F'{sctpprofile_mo.split(",")[-1]}'}, inplace=True)
                    df_gs.GSValue.replace({"Transport=1,SctpProfile=LTE_ID_VAL": F'Transport=1,{sctpprofile_mo.split(",")[-1]}'}, inplace=True)
                sctp_mos.append(sctpprofile_mo)
            for mo in sctp_mos:
                for para in df_gs.loc[(df_gs.MOC == mo.split('=')[-1])].Parameter.unique():
                    if F'{mo}.{para}' not in self.process_list:
                        self.r_list_for_missing_gs_para(site.siteid, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)
