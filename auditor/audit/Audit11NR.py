from auditor.audit.GSAuditBase import GSAuditBase


class Audit11NR(GSAuditBase):
    def generate_audit_report(self):
        if len([_ for _ in self.usid.sites if len(self.usid.sites.get(_).gnb) > 0]) > 0:
            self.skip_moc = ['ENodeBFunction']   # , 'SctpEndpoint', 'SctpProfile'
            self.gs_audit_for_nr_mos_with_ids()
            self.gs_audit_for_nr_mos_without_ids()
            # self.admin_missing_gs_audit_for_nr_mos_with_ids()
            # self.admin_missing_gs_audit_for_nr_mos_without_ids()
            # self.gs_audit_for_nr_sctp()
            # self.admin_missing_gs_audit_for_nr_sctp()
           
    def gs_audit_for_nr_mos_with_ids(self):
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' in _) and len([i for i in self.skip_moc if F'{i}=' in _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if site.gnb == '': continue
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_endstr(site_level_mo):
                    if len([_ for _ in self.skip_moc if F',{_}=' in mo]) > 0: continue
                    para_dict = site.dcg.get(mo, {})
                    for row_gs in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].itertuples():
                        if F'{mo}.{row_gs.Parameter}' in self.process_list: continue
                        if self.logic.evaluate(row_gs.Logic, cell=None, site=site.siteid, mo_level='site'):
                            self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def gs_audit_for_nr_mos_without_ids(self):
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' not in _) and len([i for i in self.skip_moc if i == _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            if site.gnb == '': continue
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_moc(site_level_mo):
                    if len([_ for _ in self.skip_moc if F',{_}=' in mo]) > 0: continue
                    para_dict = site.dcg.get(mo, {})
                    for row_gs in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].itertuples():
                        if F'{mo}.{row_gs.Parameter}' in self.process_list: continue
                        if self.logic.evaluate(row_gs.Logic, cell=None, site=site.siteid, mo_level='site'):
                            self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    # def admin_missing_gs_audit_for_nr_mos_with_ids(self):
    #     site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' in _) and len([i for i in self.skip_moc if F'{i}=' in _]) == 0]))
    #     for site_key in self.usid.sites:
    #         site = self.usid.sites.get(site_key)
    #         if site.gnb == '': continue
    #         for site_level_mo in site_level_mos[:]:
    #             for mo in site.get_mos_with_endstr(site_level_mo):
    #                 if len([_ for _ in self.skip_moc if F',{_}=' in mo]) > 0: continue
    #                 for para in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].Parameter.unique():
    #                     if F'{mo}.{para}' not in self.process_list:
    #                         self.r_list_for_missing_gs_para(site.siteid, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)
    #
    # def admin_missing_gs_audit_for_nr_mos_without_ids(self):
    #     site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' not in _) and len([i for i in self.skip_moc if i == _]) == 0]))
    #     for site_key in self.usid.sites:
    #         site = self.usid.sites.get(site_key)
    #         if site.gnb == '':
    #             continue
    #         for site_level_mo in site_level_mos[:]:
    #             for mo in site.get_mos_with_moc(site_level_mo):
    #                 if len([_ for _ in self.skip_moc if F',{_}=' in mo]) > 0:
    #                     continue
    #                 for para in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].Parameter.unique():
    #                     if F'{mo}.{para}' not in self.process_list:
    #                         self.r_list_for_missing_gs_para(site.siteid, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)
    #
    # def gs_audit_for_nr_sctp(self):
    #     for site_key in self.usid.sites:
    #         site = self.usid.sites.get(site_key)
    #         if site.gnb_cucp == '': continue
    #         df_gs = self.df_gs.copy().loc[self.df_gs.MOC.str.contains('SctpEndpoint=NR|SctpProfile=NR')]
    #         sctp_mos = []
    #         end_point_cucp = site.get_mos_with_parent_moc(parent=site.gnb_cucp, moc='EndpointResource')
    #         if len(end_point_cucp) > 0:
    #             end_point_cucp = end_point_cucp[0]
    #             localsctpendpoints = site.get_mos_with_parent_moc(parent=end_point_cucp, moc='LocalSctpEndpoint')
    #             for local_sctpend_pt in localsctpendpoints:
    #                 local_sctpend_pt_data = site.dcg.get(local_sctpend_pt, {})
    #                 for val in ['4', '6', '7']:
    #                     if local_sctpend_pt_data.get('interfaceUsed', 'NA')[0] == val:
    #                         sctp_end_mo = site.get_first_mo_from_ref_parameter(local_sctpend_pt_data.get('sctpEndpointRef'))
    #                         if len(sctp_end_mo) > 0:
    #                             df_gs.MOC.replace({F"SctpEndpoint=NR_ID_{val}_VAL": F'{sctp_end_mo.split(",")[-1]}'}, inplace=True)
    #                             sctp_mos.append(sctp_end_mo)
    #                             sctp_profile_mo = site.get_first_mo_from_ref_parameter(site.get_mo_data(sctp_end_mo).get('sctpProfile'))
    #                             if len(sctp_profile_mo) > 0:
    #                                 df_gs.MOC.replace({F"SctpProfile=NR_ID_{val}_VAL": F'{sctp_profile_mo.split(",")[-1]}'}, inplace=True)
    #                                 sctp_mos.append(sctp_profile_mo)
    #                         break
    #         for mo in set(sctp_mos):
    #             para_dict = site.dcg.get(mo, {})
    #             for para in df_gs.loc[(df_gs.MOC == mo.split('=')[-1])].Parameter.unique():
    #                 if F'{mo}.{para}' in self.process_list: continue
    #                 for row in df_gs.loc[(df_gs.MOC == mo.split('=')[-1]) & (df_gs.Parameter == para)].itertuples():
    #                     if self.logic.evaluate(row.Logic, cell=None, site=site.siteid, mo_level='site'):
    #                         self.r_list.append([0, site.siteid, mo, para, para_dict.get(para, 'N/F'), row.GSValue, row.InitialValue, row.Permission,
    #                                             row.Suffix, self.s_type, self.compare_values(para_dict.get(para, 'N/F'), row.GSValue)])
    #                         self.process_list.append(F'{mo}.{para}')
    #                         break
    #                 if F'{mo}.{para}' not in self.process_list:
    #                     self.r_list.append([0, site.siteid, mo, para, para_dict.get(para), 'N/F', 'N/F', 'Not Auditable', 'N/F', False])
    #                     self.process_list.append(F'{mo}.{para}')
    #
    # def admin_missing_gs_audit_for_nr_sctp(self):
    #     pass