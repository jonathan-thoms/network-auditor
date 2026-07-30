from auditor.audit.GSAuditBase import GSAuditBase


class Audit13NRRelation(GSAuditBase):
    def generate_audit_report(self):
        if len([_ for _ in self.usid.sites if len(self.usid.sites.get(_).gnb_cucp) > 0]) > 0:
            self.nrcellrelation_ref = {'caFreqRelMeasProfileRef', 'intraFreqMCFreqRelProfileRef', 'mcpcPCellNrFreqRelProfileRef',
                                       'mcpcPSCellNrFreqRelProfileRef', 'trStSaNrFreqRelProfileRef', 'ueMCNrFreqRelProfileRef'}
            self.audit_report_for_nrfrequency()
            self.admin_missing_gs_audit_for_nrfrequency()
            self.gs_audit_for_nrfreqrelation()
            self.admin_missing_gs_audit_for_nrfreqrelation()
            self.audit_report_for_nrcellrelation()
            self.admin_missing_gs_audit_for_nrcellrelation()

    def audit_report_for_nrfrequency(self):
        df_gs_rel = self.df_gs.copy().loc[(self.df_gs.MOC == 'NRFrequency')]
        for r in self.usid.df_nr_freq.itertuples():
            for row_gs in df_gs_rel.itertuples():
                if F'{r.fdn}.{row_gs.Parameter}' in self.process_list: continue
                elif self.logic.evaluate(row_gs.Logic, cell=r.ssbfreq, site=None, mo_level='ssbfreq'):
                    self.r_list_for_gs_para(r.site, r.fdn, self.usid.sites[F'site_{r.site}'].dcg.get(r.fdn, {}).get(row_gs.Parameter, 'N/F'), row_gs)

    def admin_missing_gs_audit_for_nrfrequency(self):
        df_gs_rel = self.df_gs.copy().loc[(self.df_gs.MOC == 'NRFrequency')]
        for r in self.usid.df_nr_freq.itertuples():
            for para in df_gs_rel.Parameter.unique():
                if F'{r.fdn}.{para}' not in self.process_list:
                    self.r_list_for_missing_gs_para(r.site, r.fdn, self.usid.sites.get(F'site_{r.site}').dcg.get(r.fdn, {}).get(para, 'N/F'), para)

    def gs_audit_for_nrfreqrelation(self):
        for r in self.usid.df_nr_rel.itertuples():
            site = self.usid.sites.get(F'site_{r.site}')
            c_mos = [r.fdn]
            ref_mos = []
            # NRFreqRelation ref MOS additions
            for para_ref in self.nrcellrelation_ref:
                if site.get_mo_para(r.fdn, para_ref) != 'N/F':
                    ref_mo = site.get_first_mo_from_ref_parameter(site.get_mo_para(r.fdn, para_ref))
                    if ref_mo in [None, 'N/F', '', []]: continue
                    ref_mos += site.get_mos_and_its_child_with_mo(ref_mo)
            # c_mos += ref_mos
            c_mos = list(set(c_mos + ref_mos))
            for mo in c_mos:
                para_dict = site.dcg.get(mo, {})
                df_gs = self.df_gs.copy().loc[(self.df_gs.MOC == mo.split(',')[-1].split('=')[0])]
                df_gs['GSValue'] = df_gs.GSValue.str.replace(r'NR__FREQ__ID$', mo.split('=')[-1], regex=True)
                for row_gs in df_gs.itertuples():
                    if F'{mo}.{row_gs.Parameter}' in self.process_list: continue
                    logic_flag = True if row_gs.Logic in ['', None, 'None'] else False
                    if not logic_flag:
                        suffix_mapped = [_.strip() for _ in row_gs.Logic.split('|')]
                        for cond in suffix_mapped:
                            if cond.strip() in ('OWNFREQ', 'INTERFREQ'): continue
                            else:
                                source_cond, target_cond = self.split_source_target(cond)
                                logic_flag = logic_flag or (self.logic.evaluate(source_cond, cell=r.cell, site=r.site, mo_level='cell') and
                                                            self.logic.evaluate(target_cond, cell=r.ssbfreq, site=None, mo_level='ssbfreq'))
                                if logic_flag: break
                        if len([_ for _ in suffix_mapped if _ in ('OWNFREQ', 'INTERFREQ')]) > 0:
                            if len(suffix_mapped) == 1: logic_flag = True
                            cell_ssbfreq = self.usid.param_dict['sites'][r.site]['cells'][r.cell]['ssbfreq']
                            if 'OWNFREQ' in suffix_mapped: logic_flag = logic_flag and (str(cell_ssbfreq) == str(r.ssbfreq))
                            if 'INTERFREQ' in suffix_mapped: logic_flag = logic_flag and (str(cell_ssbfreq) != str(r.ssbfreq))
                    if logic_flag: self.r_list_for_gs_para(site.siteid, mo, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)
    
    def admin_missing_gs_audit_for_nrfreqrelation(self):
        for r in self.usid.df_nr_rel.itertuples():
            site = self.usid.sites.get(F'site_{r.site}')
            c_mos = [r.fdn]
            ref_mos = []
            # NRFreqRelation ref MOS additions
            for para_ref in self.nrcellrelation_ref:
                if site.get_mo_para(r.fdn, para_ref) != 'N/F':
                    ref_mo = site.get_first_mo_from_ref_parameter(site.get_mo_para(r.fdn, para_ref))
                    if ref_mo in [None, 'N/F', '', []]: continue
                    ref_mos += site.get_mos_and_its_child_with_mo(ref_mo)
            c_mos = list(set(c_mos + ref_mos))
            for mo in c_mos:
                for para in self.df_gs.copy().loc[(self.df_gs.MOC == mo.split(',')[-1].split('=')[0])].Parameter.unique():
                    if F'{mo}.{para}' not in self.process_list:
                        self.r_list_for_missing_gs_para(r.site, mo, site.dcg.get(mo, {}).get(para, 'N/F'), para)

    def audit_report_for_nrcellrelation(self):
        df_gs_rel = self.df_gs.copy().loc[(self.df_gs.MOC == 'NRCellRelation')]
        for r in self.usid.df_nr_crel.itertuples():
            for row_gs in df_gs_rel.itertuples():
                if F'{r.fdn}.{row_gs.Parameter}' in self.process_list: continue
                logic_flag = True if row_gs.Logic in ['', None, 'None'] else False
                if not logic_flag:
                    suffix_mapped = [_.strip() for _ in row_gs.Logic.split('|')]
                    for cond in suffix_mapped:
                        if cond in ('COSECTOR', 'SAME_SEF', 'INTRA_USID'): continue
                        source_cond, target_cond = self.split_source_target(cond)
                        logic_flag = logic_flag or (self.logic.evaluate(source_cond, cell=r.cell, site=r.site, mo_level='cell') and
                                                    self.logic.evaluate(target_cond, cell=r.t_cell, site=r.t_site, mo_level='cell'))
                        if logic_flag: break
                    if len([_ for _ in suffix_mapped if _ in ('COSECTOR', 'SAME_SEF', 'INTRA_USID')]) > 0:
                        if len(suffix_mapped) == 1: logic_flag = True
                        if 'COSECTOR' in suffix_mapped: logic_flag = logic_flag and self.usid.get_co_sector_for_nr_cell(r.cell, r.t_cell)
                        if 'SAME_SEF' in suffix_mapped:
                            logic_flag = logic_flag and self.usid.get_same_sef_for_nr_cell(r.site, r.cell, r.t_site, r.t_cell)
                        if 'INTRA_USID' in suffix_mapped:
                            logic_flag = logic_flag and (r.site == r.t_site)
                if logic_flag:
                    self.r_list_for_gs_para(r.site, r.fdn, self.usid.sites[F'site_{r.site}'].dcg.get(r.fdn, {}).get(row_gs.Parameter, 'N/F'), row_gs)

    def admin_missing_gs_audit_for_nrcellrelation(self):
        df_gs_rel = self.df_gs.copy().loc[(self.df_gs.MOC == 'NRCellRelation')]
        for r in self.usid.df_nr_crel.itertuples():
            for para in df_gs_rel.Parameter.unique():
                if F'{r.fdn}.{para}' not in self.process_list:
                    self.r_list_for_missing_gs_para(r.site, r.fdn, self.usid.sites.get(F'site_{r.site}').dcg.get(r.fdn, {}).get(para, 'N/F'), para)
