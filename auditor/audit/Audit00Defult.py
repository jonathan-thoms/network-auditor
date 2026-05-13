from auditor.audit.GSAuditBase import GSAuditBase


class Audit00Defult(GSAuditBase):
    def generate_audit_report(self):
        if len([_ for _ in self.usid.sites if len(self.usid.sites.get(_).enb) > 0 or len(self.usid.sites.get(_).gnb) > 0]) > 0:
            self.gs_audit_for_default_mos_with_ids()
            # self.admin_missing_gs_audit_for_default_mos_with_ids()
            self.gs_audit_for_default_mos_without_ids()
            # self.admin_missing_gs_audit_for_default_mos_without_ids()

    def gs_audit_for_default_mos_with_ids(self):
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' in _) and len([moc for moc in self.skip_moc if moc == _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_endstr(site_level_mo):
                    para_dict = site.dcg.get(mo, {})
                    for row_gs in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].itertuples():
                        if self.logic.evaluate(row_gs.Logic, cell=None, site=site.siteid, mo_level='site'):
                            self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def admin_missing_gs_audit_for_default_mos_with_ids(self):
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' in _) and len([moc for moc in self.skip_moc if moc == _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_endstr(site_level_mo):
                    for para in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].Parameter.unique():
                        if F'{mo}.{para}' not in self.process_list:
                            self.r_list_for_missing_gs_para(site.siteid, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)

    def gs_audit_for_default_mos_without_ids(self):
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' not in _) and len([_ for moc in self.skip_moc if moc in _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_moc(moc=site_level_mo):
                    para_dict = site.dcg.get(mo, {})
                    for row_gs in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].itertuples():
                        if self.logic.evaluate(row_gs.Logic, cell=None, site=site.siteid, mo_level='site'):
                            self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def admin_missing_gs_audit_for_default_mos_without_ids(self):
        site_level_mos = list(set([_ for _ in self.df_gs.MOC.unique() if ('=' not in _) and len([_ for moc in self.skip_moc if moc in _]) == 0]))
        for site_key in self.usid.sites:
            site = self.usid.sites.get(site_key)
            for site_level_mo in site_level_mos[:]:
                for mo in site.get_mos_with_moc(moc=site_level_mo):
                    for para in self.df_gs.loc[(self.df_gs.MOC == site_level_mo)].Parameter.unique():
                        if F'{mo}.{para}' not in self.process_list:
                            self.r_list_for_missing_gs_para(site.siteid, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)
