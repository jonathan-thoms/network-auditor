from auditor.audit.GSAuditBase import GSAuditBase
from collections import namedtuple
import json
import re


class Audit03LTERelation(GSAuditBase):
    def generate_audit_report(self):
        if len([_ for _ in self.usid.sites if len(self.usid.sites.get(_).enb) > 0]) > 0:
            self.gs_audit_for_lte_eutranfrequency()
            self.gs_audit_for_eutranfreqrelation()
            self.admin_missing_gs_audit_for_same_type_dataframes_relation(
                self.usid.df_lte_rel.loc[self.usid.df_lte_rel.flag | self.usid.df_lte_rel.cr_flag], 'EUtranFreqRelation')
            self.gs_audit_for_eutrancellrelation()
            self.admin_missing_gs_audit_for_same_type_dataframes_relation(
                self.usid.df_lte_crel.loc[self.usid.df_lte_crel.flag | self.usid.df_lte_crel.cr_flag], 'EUtranCellRelation')
            # Special Method to Audit EUtranCellRelation.isHoAllowedBr for Non_Co_Site_Cell_Relations to false --- No Logic/hard Codded
            self.gs_audit_for_eutrancellrelation_ishoallowedbr()

            self.gs_audit_for_gutransyncsignalfrequency()
            self.gs_audit_for_gutranfreqrelation()
            self.admin_missing_gs_audit_for_same_type_dataframes_relation(self.usid.df_lte_nr_rel, 'GUtranFreqRelation')
            # self.gs_audit_for_utranfreqrelation()
            # self.admin_missing_gs_audit_for_same_type_dataframes_relation(
            #     self.usid.df_lte_umts_rel.loc[self.usid.df_lte_umts_rel.flag], 'UtranFreqRelation')

    def admin_missing_gs_audit_for_same_type_dataframes_relation(self, df_rel, moc):
        for row_rel in df_rel.itertuples():
            for para in self.df_gs.loc[(self.df_gs.MOC == moc)].Parameter.unique():
                if F'{row_rel.fdn}.{para}' not in self.process_list:
                    site_val = self.usid.sites.get(F'site_{row_rel.site}').dcg.get(row_rel.fdn, {}).get(para, 'N/F')
                    self.r_list_for_missing_gs_para(row_rel.site, row_rel.fdn, site_val, para)
                
    def gs_audit_for_lte_eutranfrequency(self):
        df_gs_rel = self.df_gs.loc[(self.df_gs.MOC == 'EUtranFrequency')]
        for r in self.usid.df_lte_freq.itertuples():
            para_dict = self.usid.sites.get(F'site_{r.site}').dcg.get(r.fdn, {})
            earfcndl = self.usid.sites.get(F'site_{r.site}').get_mo_para(r.fdn, 'arfcnValueEUtranDl')
            earfcndl = r.earfcn if earfcndl == 'N/F' else earfcndl
            assert self.usid.param_dict.get('earfcn').get(earfcndl) is not None, F"Could not find Frequency: {earfcndl} in LTE_LTE_Bandlayer"
            for para in df_gs_rel.Parameter.unique():
                if F'{r.fdn}.{para}' in self.process_list: continue
                for row_gs in df_gs_rel.loc[(df_gs_rel.Parameter == para)].itertuples():
                    if para == 'excludeAdditionalFreqBandList':
                        logic_flag = True if row_gs.Logic in ['', None, 'None'] else False
                        logic_val = row_gs.Logic
                        if not logic_flag:
                            start, end = 0, 0
                            if re.match('>=\s?(\d+)\sand\s<=\s?(\d+)', logic_val):
                                start = int(re.match('>=\s?(\d+)\sand\s<=\s?(\d+)', logic_val).group(1))
                                end = int(re.match('>=\s?(\d+)\sand\s<=\s?(\d+)', logic_val).group(2))
                            elif ',' in logic_val: logic_val = logic_val.split(',')
                            else: start, end = int(logic_val), int(logic_val)
                            if (type(logic_val) == list) and (earfcndl in logic_val): logic_flag = True
                            elif start <= int(earfcndl) <= end: logic_flag = True
                        if logic_flag:
                            gs_val = json.loads(row_gs.GSValue)
                            gs_val = [_ for _ in gs_val if _ in para_dict.get('additionalFreqBandList', [])]
                            exclude_val = para_dict.get('excludeAdditionalFreqBandList', [])
                            self.r_list.append([0, r.site, r.fdn, para, para_dict.get(para, 'N/F'), row_gs.GSValue, json.dumps(gs_val),
                                                row_gs.Permission, row_gs.Suffix, all([_ in exclude_val for _ in gs_val])])
                            self.process_list.append(F'{r.fdn}.{para}')
                            break
                    elif self.logic.evaluate(row_gs.Logic, cell=earfcndl, site=r.site, mo_level='earfcn'):
                        self.r_list_for_gs_para(r.site, r.fdn, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)
                        break
    
    def gs_audit_for_eutranfreqrelation(self):
        df_gs_rel = self.df_gs.loc[(self.df_gs.MOC == 'EUtranFreqRelation')]
        for r in self.usid.df_lte_rel.copy().loc[self.usid.df_lte_rel.flag | self.usid.df_lte_rel.cr_flag].itertuples():
            para_dict = self.usid.sites.get(F'site_{r.site}').dcg.get(r.fdn, {})
            for row_gs in df_gs_rel.itertuples():
                if F'{r.fdn}.{row_gs.Parameter}' in self.process_list: continue
                logic_flag = True if row_gs.Logic in ['', None, 'None'] else False
                if not logic_flag:
                    suffix_mapped = [_.strip() for _ in row_gs.Logic.split('|')]
                    for cond in suffix_mapped:
                        if cond.strip() in ('OWNFREQ', 'INTERFREQ'): continue
                        else:
                            source_cond, target_cond = self.split_source_target(cond)
                            logic_flag = logic_flag or (self.logic.evaluate(source_cond, cell=r.cell, site=r.site, mo_level='cell') and
                                                        self.logic.evaluate(target_cond, cell=r.earfcn, site=None, mo_level='earfcn'))
                            if logic_flag: break
                    if len([_ for _ in suffix_mapped if _ in ('OWNFREQ', 'INTERFREQ')]) > 0:
                        if len(suffix_mapped) == 1: logic_flag = True
                        cell_earfcn = self.usid.param_dict['sites'][r.site]['cells'][r.cell]['earfcndl']
                        if 'OWNFREQ' in suffix_mapped: logic_flag = logic_flag and (str(cell_earfcn) == str(r.earfcn))
                        if 'INTERFREQ' in suffix_mapped: logic_flag = logic_flag and (str(cell_earfcn) != str(r.earfcn))
                if logic_flag: self.r_list_for_gs_para(r.site, r.fdn, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def gs_audit_for_eutrancellrelation(self):
        df_gs_rel = self.df_gs.loc[(self.df_gs.MOC == 'EUtranCellRelation')]
        for r in self.usid.df_lte_crel.loc[self.usid.df_lte_crel.flag | self.usid.df_lte_crel.cr_flag].itertuples():
            para_dict = self.usid.sites.get(F'site_{r.site}').dcg.get(r.fdn, {})
            for row_gs in df_gs_rel.itertuples():
                if F'{r.fdn}.{row_gs.Parameter}' in self.process_list: continue
                logic_flag = True if row_gs.Logic in ['', None, 'None'] else False
                if not logic_flag:
                    suffix_mapped = [_.strip() for _ in row_gs.Logic.split('|')]
                    for cond in suffix_mapped:
                        if cond in ('COSECTOR', 'non_COSECTOR', 'CARRIERAGG_COSECTOR', 'INTRA_USID'): continue
                        else:
                            source_cond, target_cond = self.split_source_target(cond)
                            logic_flag = logic_flag or (self.logic.evaluate(source_cond, cell=r.cell, site=r.site) and
                                                        self.logic.evaluate(target_cond, cell=r.t_cell, site=r.t_site))
                            if logic_flag: break
                    if len([_ for _ in suffix_mapped if _ in ('COSECTOR', 'non_COSECTOR', 'CARRIERAGG_COSECTOR', 'INTRA_USID')]) > 0:
                        if len(suffix_mapped) == 1: logic_flag = True
                        if 'COSECTOR' in suffix_mapped: logic_flag = logic_flag and self.usid.get_co_sector_for_lte_cell(r.cell, r.t_cell)
                        if 'non_COSECTOR' in suffix_mapped: logic_flag = logic_flag and (not self.usid.get_co_sector_for_lte_cell(r.cell, r.t_cell))
                        if 'CARRIERAGG_COSECTOR' in suffix_mapped: logic_flag = logic_flag and \
                                                                                self.usid.check_carrier_agg_flag(r.site, r.cell, r.t_site, r.t_cell)
                        if 'INTRA_USID' in suffix_mapped: logic_flag = logic_flag and (r.site == r.t_site)
                if logic_flag: self.r_list_for_gs_para(r.site, r.fdn, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def gs_audit_for_eutrancellrelation_ishoallowedbr(self):
        """
        This method is defined and is hard codded to set values isHoAllowedBr to false for non-cosite relations
        :return:
        """
        if len(self.df_gs.loc[((self.df_gs.MOC == 'EUtranCellRelation') & (self.df_gs.Parameter == 'isHoAllowedBr') &
                               (self.df_gs.Suffix == 'Non_Co_Site_Cell_Relations'))].index) == 0:
            return
        gsaudit_row = namedtuple('gsaudit_row', ['MOC', 'Parameter', 'Suffix', 'Logic', 'GSValue', 'InitialValue', 'Permission'])
        row_gs = gsaudit_row('EUtranCellRelation', 'isHoAllowedBr', 'Non_Co_Site_Cell_Relations', None, 'false', None, 'Global')
        for r in self.usid.df_lte_rel.copy().loc[self.usid.df_lte_rel.flag | self.usid.df_lte_rel.cr_flag].itertuples():
            for mo_fdn in self.usid.sites.get(F'site_{r.site}').get_mos_with_parent_moc(parent=r.fdn, moc='EUtranCellRelation'):
                para_val = self.usid.sites.get(F'site_{r.site}').dcg.get(mo_fdn, {}).get('isHoAllowedBr')
                if F'{mo_fdn}.isHoAllowedBr' in self.process_list: continue
                if para_val is not None and para_val == 'false':
                    self.r_list_for_gs_para(r.site, mo_fdn, para_val, row_gs)

    def gs_audit_for_gutransyncsignalfrequency(self):
        df_gs_rel = self.df_gs.loc[(self.df_gs.MOC == 'GUtranSyncSignalFrequency')]
        # self.df_lte_nr_freq = pd.DataFrame([], columns=['site', 'freq', 'fdn', 'flag', 'ssbfreq', 'scc', 'duration', 'offset', 'periodicity'])
        for r in self.usid.df_lte_nr_freq.itertuples():
            para_dict = self.usid.sites.get(F'site_{r.site}').dcg.get(r.fdn, {})
            ssbfreq = self.usid.sites.get(F'site_{r.site}').get_mo_para(r.fdn, 'arfcn')
            ssbfreq = r.ssbfreq if ssbfreq == 'N/F' else ssbfreq
            assert self.usid.param_dict.get('ssbfreq').get(ssbfreq) is not None, F"Could not find Frequency: {ssbfreq} in LTE_NR_Table"
            for para in df_gs_rel.Parameter.unique():
                if F'{r.fdn}.{para}' in self.process_list: continue
                for row_gs in df_gs_rel.loc[(df_gs_rel.Parameter == para)].itertuples():
                    if self.logic.evaluate(row_gs.Logic, cell=r.ssbfreq, site=r.site, mo_level='ssbfreq'):
                        self.r_list_for_gs_para(r.site, r.fdn, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)
                        break

    def gs_audit_for_gutranfreqrelation(self):
        df_gs_rel = self.df_gs.loc[(self.df_gs.MOC == 'GUtranFreqRelation')]
        for r in self.usid.df_lte_nr_rel.itertuples():
            para_dict = self.usid.sites.get(F'site_{r.site}').dcg.get(r.fdn, {})
            for row_gs in df_gs_rel.itertuples():
                if F'{r.fdn}.{row_gs.Parameter}' in self.process_list: continue
                logic_flag = True if row_gs.Logic in ['', None, 'None'] else False
                if not logic_flag:
                    suffix_mapped = [_.strip() for _ in row_gs.Logic.split('|')]
                    for cond in suffix_mapped:
                        source_cond, target_cond = self.split_source_target(cond)
                        logic_flag = logic_flag or (self.logic.evaluate(source_cond, cell=r.cell, site=r.site, mo_level='cell') and
                                                    self.logic.evaluate(target_cond, cell=r.ssbfreq, site=None, mo_level='ssbfreq'))
                        if logic_flag: break
                if logic_flag: self.r_list_for_gs_para(r.site, r.fdn, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

    def gs_audit_for_utranfreqrelation(self):
        df_gs_rel = self.df_gs.loc[(self.df_gs.MOC == 'UtranFreqRelation')]
        for r in self.usid.df_lte_umts_rel.loc[(self.usid.df_lte_umts_rel.flag == True)].itertuples():
            para_dict = self.usid.sites.get(F'site_{r.site}').dcg.get(r.fdn, {})
            for row_gs in df_gs_rel.itertuples():
                if F'{r.fdn}.{row_gs.Parameter}' in self.process_list: continue
                logic_flag = True if row_gs.Logic in ['', None, 'None'] else False
                if not logic_flag:
                    suffix_mapped = [_.strip() for _ in row_gs.Logic.split('|')]
                    for cond in suffix_mapped:
                        source_cond, target_cond = self.split_source_target(cond)
                        logic_flag = logic_flag or (self.logic.evaluate(source_cond, cell=r.cell, site=r.site) and
                                                    self.logic.evaluate(target_cond, cell=r.arfcn, site=None, mo_level='uarfcn'))
                        if logic_flag: break
                if logic_flag: self.r_list_for_gs_para(r.site, r.fdn, para_dict.get(row_gs.Parameter, 'N/F'), row_gs)

