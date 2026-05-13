import pandas as pd
import os
import json
import re
from itertools import chain

plmn = '{"mcc": 310, "mnc": 410, "mncLength": 3}'
add_plmn = '[{"mcc": 310, "mnc": 410, "mncLength": 3}, {"mcc": 313, "mnc": 100, "mncLength": 3}]'


class GSAuditScriptNew:
    def __init__(self, *, usid):
        self.usid = usid
        self.log = self.usid.log
        self.df_s = self.usid.df_report.copy().loc[((~self.usid.df_report.flag) & (self.usid.df_report.Permission != 'Not Auditable'))]
        self.df_s.reset_index(drop=True, inplace=True)
        self.df_s.loc[self.df_s.InitialValue.isnull(), 'InitialValue'] = self.df_s.loc[self.df_s.InitialValue.isnull(), 'GSValue']
        if len(self.df_s.index) == 0:
            self.log.info(F'No Delta Parameters found !!!')
            return
        self.nodes = sorted(list(self.df_s.Site.unique()))
        for row in self.usid.df_script_type.itertuples():
            if row.MO == 'NN':
                self.df_s.loc[((self.df_s.MOC == row.MOC) & (self.df_s.Parameter == row.Parameter)), 'Type'] = row.script_type
            else:
                self.df_s.loc[((self.df_s.MO.str.endswith(row.MO)) & (self.df_s.Parameter == row.Parameter)), 'Type'] = row.script_type
        self.ManagedElement: str = ''
        self.s_dict = {_: {} for _ in self.nodes}
        self.s_dict_filteralgorithm = {_: {} for _ in self.nodes}
        self.write_usid_cli_command_list()
        self.df_s.flag = False
        # self.df_s['attribute'] = self.df_s.apply(lambda x: self.get_attribute_dict(r=x), axis=1)
        # # AlarmPort:filterAlgorithm --- Add Lock and Unlock if filterAlgorithm need to be changed.
        # mask = ((self.df_s.MOC == 'AlarmPort') & (self.df_s.Parameter == 'filterAlgorithm'))
        # if len(self.df_s.loc[mask].index) > 0:
        #     self.df_s.loc[mask, 'attribute'] = self.df_s.loc[mask].apply(lambda x: self.get_filteralgorithm(r=x), axis=1)
        # # lte_nr_special_parameter_for_endc "LTENR_para"
        # ToDo Add missing relations
        # LTE-->LTE, LTE-->NR & NR-->NR missing relations create
        # print(sorted(list(self.df_s.Site.unique())))
        # nodes = sorted(list(self.df_s.Site.unique()))
        # nodes.sort()
        for node in sorted(list(self.df_s.Site.unique())):
            mask = ((self.df_s.Site == node) & (~self.df_s.flag))
            if len(self.df_s.Site.loc[mask].index) == 0:
                continue
            # else:
            #     print(self.df_s.Site.iloc[mask, 'MO'][0])
            #     self.ManagedElement = re.search(r'(.*,ManagedElement=[^,=]*),.*', self.df_s.Site.iloc[mask, 'MO'][0]).group(1)
            self.s_dict[node]['Internal Parameters'] = self.get_internal_command_list(mask=(mask & (self.df_s.Type == 'Internal')))

            self.s_dict[node]['LTE ---> EUtraNetwork'] = self.get_enb_eutrannetwork_mos_dict(node=node)
            self.s_dict[node]['LTE ---> GUtraNetwork'] = self.get_enb_gutrannetwork_mos_dict(node=node)
            self.s_dict[node]['NR ---> NRNetwork'] = self.get_gnb_nrnetwork_mos_dict(node=node)

            self.s_dict[node]['LTE & NR Defult'] = self.get_command_dict(mask=(mask & (self.df_s.Type.isin(['Defult']))))
            self.s_dict[node]['filteralgorithm_unlock'] = self.s_dict_filteralgorithm[node] if node in self.s_dict_filteralgorithm else {}

            self.s_dict[node]['LTE Node'] = self.get_command_dict(mask=(mask & (self.df_s.Type.isin(['LTE']))))
            self.s_dict[node]['LTE RATFreqPrio'] = self.get_command_dict(mask=(mask & (self.df_s.Type.isin(['LTE_RATFreqPrio']))))
            self.s_dict[node]['LTE On-Air Cell'] = self.get_command_dict(mask=(
                    mask & (self.df_s.Type.isin(['LTECell']) & (self.df_s.OnAir.isin([1, '1'])))))
            self.s_dict[node]['LTE Off-Air Cell'] = self.get_command_dict(mask=(
                    mask & (self.df_s.Type.isin(['LTECell']) & (self.df_s.OnAir.isin([0, '0'])))))
            self.s_dict[node]['LTE to LTE Relation'] = self.get_command_dict(mask=(
                    mask & (self.df_s.Type.str.startswith('LTERelation_EUtran', na=False))))
            self.s_dict[node]['LTE to NR Relation'] = self.get_command_dict(mask=(
                    mask & (self.df_s.Type.str.startswith('LTERelation_GUtran', na=False))))
            self.s_dict[node]['ENDC_Parameter'] = self.get_command_dict(mask=(mask & (self.df_s.Type.isin(['LTENR_para']))))

            self.s_dict[node]['NR Node'] = self.get_command_dict(mask=(mask & (self.df_s.Type.isin(['NR']))))
            self.s_dict[node]['NR On-Air Cell'] = self.get_command_dict(
                mask=(mask & (self.df_s.Type.isin(['NRCell'])) & (self.df_s.OnAir.isin([1, '1']))))
            self.s_dict[node]['NR Off-Air Cell'] = self.get_command_dict(
                mask=(mask & (self.df_s.Type.isin(['NRCell'])) & (self.df_s.OnAir.isin([0, '0']))))
            self.s_dict[node]['NR to NR Relation'] = self.get_command_dict(
                mask=(mask & (self.df_s.Type.str.startswith('NRRelation', na=False))))

            self.df_s.loc[(~self.df_s.flag)].reset_index(drop=True, inplace=True)
        # file_name = F'{script_file}_{node}_{self.usid.sw_ver}_{st}.txt'
        # self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)
        # Internal Parameters
        for node in self.nodes:
            if len(self.s_dict[node]['Internal Parameters']) > 0:
                file_name = F'{node}_internalmom_{self.usid.sw_ver}_mos.mos'
                with open(os.path.join(self.usid.outdir, node, file_name), 'a+') as f:
                    f.write('\n'.join(
                        [
                            F'$date = `date +%Y%m%d_%H%M%S`',
                            F'l+ LogFile_{os.path.basename(file_name)[:-4]}_$date.log',
                            F'lt all',
                            F'confbd+',
                            F'',
                            F'####:- NODE NAME -:####',
                            F'pv $nodename',
                            F'if $nodename != {node}',
                            F'print !!! Node Name mismatch.Wrong Node. ABORT !!!',
                            F'l-',
                            F'return',
                            F'fi',
                            F'',
                        ] + self.s_dict[node]['Internal Parameters'] + [
                            F'',
                            F'',
                            # F'commit',
                            F'confbd',
                            F'l-',
                            F'',
                        ]
                    ))

        script_file_dict = {
            'LTE ---> EUtraNetwork': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'LTE_LTE_relation_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'15_lte_lte_relation_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'LTE ---> GUtraNetwork': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'LTE_NR_relation_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'16_lte_nr_relation_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'NR ---> NRNetwork': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'NR_NR_relation_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'24_nr_nr_relation_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'LTE & NR Defult': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'11_usid_lte_nr_default_node_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'11_lte_nr_default_node_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'LTE Node': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'01_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'12_usid_lte_live_node_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'12_lte_live_node_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'LTE RATFreqPrio': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'13_usid_lte_ratfreqprio_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'13_lte_ratfreqprio_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'LTE On-Air Cell': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'01_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'14_usid_lte_live_cell_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'14_lte_live_cell_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'LTE Off-Air Cell': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'15_usid_lte_non_live_cell_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'15_lte_non_live_cell_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'LTE to LTE Relation': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'16_usid_lte_lte_relation_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'16_lte_lte_relation_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'LTE to NR Relation': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'17_usid_lte_nr_relation_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'17_lte_nr_relation_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'ENDC_Parameter': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'18_usid_lte_endc_parameter_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'18_lte_endc_parameter_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'NR Node': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'01_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'21_usid_nr_live_node_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'21_nr_live_node_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'NR On-Air Cell': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'01_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'22_usid_nr_live_cell_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'22_nr_live_cell_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'NR Off-Air Cell': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'23_usid_nr_non_live_cell_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'23_nr_non_live_cell_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },
            'NR to NR Relation': {
                1: F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                2: F'02_non_live_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                3: F'24_usid_nr_nr_relation_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt',
                6: F'24_nr_nr_relation_NODE_SCTYPE_{self.usid.sw_ver}.txt',
            },

            'filteralgorithm_unlock': {

            }
        }
        for sc_type in script_file_dict.keys():
            for node in self.nodes:
                if len(self.s_dict[node][sc_type]) > 0:
                    script_cli = self.get_command_list(mo_dict=self.s_dict[node][sc_type], cli=True)
                    script_cmedit = self.get_command_list(mo_dict=self.s_dict[node][sc_type], cli=False)
                    for i in range(1, 4):
                        print(i)

    @staticmethod
    def write_mos_script_for_node(*, node: str, script_list: list, file_path: str) -> None:
        if len(script_list) > 0:
            with open(file_path, 'a+') as f:
                f.write('\n'.join([
                    F'$date = `date +%Y%m%d_%H%M%S`',
                    F'l+ LogFile_{os.path.basename(file_path)[:-4]}_$date.log',
                    F'lt all',
                    F'confbd+',
                    F'',
                    F'####:- NODE NAME -:####',
                    F'pv $nodename',
                    F'if $nodename != {node}',
                    F'print !!! Node Name mismatch.Wrong Node. ABORT !!!',
                    F'l-',
                    F'return',
                    F'fi',
                    F'',
                ]))
                f.write('\n'.join(script_list))
                f.write('\n'.join([
                    F'',
                    # F'commit',
                    F'confbd',
                    F'l-',
                    F'',
                ]))

    def write_usid_cli_command_list(self) -> None:
        tmp_dict = {}
        for node in self.nodes:
            # Internal Parameter
            mask = ((self.df_s.Site == node) & (~self.df_s.flag) & (self.df_s.Type == 'Internal'))
            if len(self.df_s.loc[mask].index) > 0:
                self.write_mos_script_for_node(node=node, script_list=self.get_internal_command_list(mask=mask),
                                               file_path=os.path.join(self.usid.outdir, F'00_internalmom_{node}_{self.usid.sw_ver}_mos.mos'))
            mask = ((self.df_s.Site == node) & (~self.df_s.flag) & (self.df_s.Type != 'Internal'))
            tmp_dict |= self.get_enb_eutrannetwork_mos_dict(node=node)
            tmp_dict |= self.get_enb_gutrannetwork_mos_dict(node=node)
            tmp_dict |= self.get_gnb_nrnetwork_mos_dict(node=node)
            tmp_dict |= self.get_command_dict(mask=mask)
        if len(tmp_dict) > 0:
            with open(os.path.join(self.usid.outdir, F'00_usid_{self.usid.site_id}_{self.usid.sw_ver}_cli.txt'), 'a+') as f:
                f.write('\n'.join(self.get_command_list(mo_dict=tmp_dict, cli=True)))
                for node in self.s_dict_filteralgorithm.keys():
                    if len(self.s_dict_filteralgorithm[node]) > 0:
                        f.write('\n'.join(self.get_command_list(mo_dict=self.s_dict_filteralgorithm[node], cli=True)))

        # for script_type in ['LTE ---> EUtraNetwork', 'LTE ---> GUtraNetwork', 'NR ---> NRNetwork', ]
        # for node in self.nodes:




        # # TODo : Need Update here
        # df_report[['cli_cmd', 'cmedit_cmd', 'internal_cmd', ]] = df_report.apply(self.get_script_command, axis=1, result_type='expand')
        #
        #
        # mask = ((df_report.MOC == 'AlarmPort') & (df_report.Parameter == 'filterAlgorithm'))
        # if len(df_report.loc[mask].index) > 0:
        #     df_report.loc[mask, 'cli_cmd'] = df_report.loc[mask].apply(lambda x: self.get_filteralgorithm(rr=x, types='cli'), axis=1)
        #     df_report.loc[mask, 'cmedit_cmd'] = df_report.loc[mask].apply(lambda x: self.get_filteralgorithm(rr=x, types='cmedit'), axis=1)
        # df_report.sort_values(by=['Site', 'MO', 'Parameter'], inplace=True)
        # df_report.drop(['flag', 'GSValue', 'CurrentValue'], axis=1, inplace=True)
        #
        #
        # for node in df_report.Site.unique():
        #     df_temp = df_report.loc[df_report.Site == node].copy()
        #     if len(df_temp.index) == 0: continue
        #     sctipt_dict = {
        #         '05_lte_nr_live_defult': df_temp.loc[(df_temp.Type.isin(['Defult']))],
        #         '11_lte_live_node': df_temp.loc[(df_temp.Type.isin(['LTE']))],
        #         '12_lte_live_cell': df_temp.loc[((df_temp.Type.isin(['LTECell'])) & (df_temp.OnAir.isin([1])))],
        #         '13_lte_non_live_cell': df_temp.loc[((df_temp.Type.isin(['LTECell'])) & (df_temp.OnAir.isin([0])))],
        #         '14_lte_ratfreqprio': df_temp.loc[(df_temp.Type.isin(['LTE_RATFreqPrio']))],
        #         '15_lte_lte_umts_relation': df_temp.loc[((df_temp.Type.str.startswith('LTERelation_EUtran', na=False)) |
        #                                                  (df_temp.Type.str.startswith('LTERelation_Utran', na=False)))],
        #         '16_lte_nr_relation': df_temp.loc[(df_temp.Type.str.startswith('LTERelation_GUtran', na=False))],
        #         # '15_lte_lte_umts_relation': df_temp.loc[df_temp.Type.isin(['LTERelation_EUtranFrequency', 'LTERelation_EUtranFreqRelation',
        #         #                                                            'LTERelation_EUtranCellRelation', 'LTERelation_UtranFreqRelation'])],
        #         # '16_lte_nr_relation': df_temp.loc[df_temp.Type.isin(['LTERelation_GUtranSyncSignalFrequency', 'LTERelation_GUtranFreqRelation',
        #         #                                                      'LTERelation_GUtranCellRelation'])],
        #         '19_lte_nr_parameter_for_endc': df_temp.loc[(df_temp.Type.isin(['LTENR_para']))],
        #
        #         '21_nr_live_node': df_temp.loc[(df_temp.Type.isin(['NR']))],
        #         '22_nr_live_cell': df_temp.loc[((df_temp.Type.isin(['NRCell'])) & (df_temp.OnAir.isin([1])))],
        #         '23_nr_non_live_cell': df_temp.loc[((df_temp.Type.isin(['NRCell'])) & (df_temp.OnAir.isin([0])))],
        #         '24_nr_nr_relation': df_temp.loc[(df_temp.Type.str.startswith('NRRelation', na=False))],
        #     }
        #
        #     # ecolumns = ['OnAir', 'Site', 'MO', 'Parameter', 'InitialValue', 'Permission', 'Suffix', 'Type', 'MOC', 'mos_MO']
        #     for script_file in sctipt_dict.keys():
        #         df_tmp = sctipt_dict[script_file].copy()
        #         if len(df_tmp.index) == 0: continue
        #         for st in ['cli', 'cmedit']:
        #             lines = list(chain(*df_tmp.loc[(df_tmp.Permission == 'Internal')][F'internal_cmd']))
        #             if len(lines) > 0:
        #                 file_name = F'internalmom_{script_file}_{node}_{self.usid.sw_ver}_mos.mos'
        #                 self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, 'mos', node)
        #             lines = list(chain(*df_tmp.loc[(df_tmp.Permission != 'Internal')][F'{st}_cmd']))
        #             if len(lines) > 0:
        #                 file_name = F'{script_file}_{node}_{self.usid.sw_ver}_{st}.txt'
        #                 self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)
        #
        # # End Update

    def get_command_list(self, *, mo_dict: dict, cli: bool = True) -> list:
        script = []
        for mo in mo_dict.keys():
            self.ManagedElement = re.search(r'(.*,ManagedElement=[^,=]*),.*', mo).group(1)
            script += self.cmedit_cli_mo_form_dict(mo=mo, para_dict=mo_dict[mo], cli_flag=cli)
        return script

    def get_internal_command_list(self, *, mask) -> list:
        tmp_list = []
        for r in self.df_s.loc[mask].itertuples():
            tmp_list.append(F"seti {r.MO.str.extract(r'.*,ManagedElement=[^,]*,(.*)')}$ {r.Parameter} "
                            F"{self.mos_normalize_gs_parameter(gs_val=r.InitialValue)}")
        self.df_s.loc[mask, 'flag'] = True
        return tmp_list

    def special_methond_for_AlarmPort_filterAlgorithm(self, *, mo: str, mask: pd.arrays) -> dict:
        tmp_dict = {}
        if re.match(',AlarmPort=[^,=]*$', mo):
            for r in self.df_s.loc[(mask & (self.df_s.MO == mo))].itertuples():
                if r.Parameter == 'filterAlgorithm' and \
                        self.usid.sites.get('site_' + str(r.Site)).get_mo_para(mo=r.MO, para='administrativeState')[0] == '1':
                    tmp_dict = {'administrativeState': '0 (LOCKED)'}
                    if r.MO not in self.s_dict_filteralgorithm[r.Site].keys(): self.s_dict_filteralgorithm[r.Site][r.MO] = {}
                    self.s_dict_filteralgorithm[r.Site][r.MO] |= {'attributes': {'xc:operation': 'update'}, 'administrativeState': '1 (UNLOCKED)'}
        return tmp_dict

    def get_command_dict(self, *, mask) -> dict:
        tmp_dict = {}
        for mo in sorted(self.df_s.loc[(mask & (~self.df_s.flag))].MO.unique()):
            # self.ManagedElement = re.search(r'(.*,ManagedElement=[^,=]*),.*', mo).group(1)
            tmp_dict[mo] = {'attributes': {'xc:operation': 'update'}}
            tmp_dict[mo] |= self.special_methond_for_AlarmPort_filterAlgorithm(mo=mo, mask=mask)
            for r in self.df_s.loc[(mask & (self.df_s.MO == mo))].itertuples():
                tmp_dict[mo] |= {r.Parameter: r.InitialValue}
        self.df_s.loc[mask, 'flag'] = True
        return tmp_dict

    def get_attribute_dict_for_mo_with_create_flag(self, *, node: str, mo: str) -> dict:
        # 'attributes', 'xc:operation' 'create', 'update', 'delete'
        tmp_dict = {'attributes': {'xc:operation': 'create'}}
        mask = ((self.df_s.Site == node) & (self.df_s.MO == mo) & (~self.df_s.flag))
        for r in self.df_s.loc[mask].itertuples():
            tmp_dict |= {r.Parameter: r.InitialValue}
        self.df_s.loc[mask, 'flag'] = True
        return tmp_dict

    def get_enb_eutrannetwork_mos_dict(self, *, node: str) -> dict:
        s_dict = {}
        df_new = self.usid.df_lte_crel.loc[((self.usid.df_lte_crel.site == node) & (~self.usid.df_lte_crel.flag) &
                                            (self.usid.df_lte_crel.cr_flag))].copy()
        if len(df_new.index) == 0: return s_dict
        site = self.usid.sites.get(F'site_{node}')
        # EUtraNetwork is systemCreated MOs
        # EUtranFrequency
        for r in self.usid.df_lte_freq.loc[((self.usid.df_lte_freq.site == node) & (~self.usid.df_lte_freq.flag))].itertuples():
            s_dict[r.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r.fdn)
            s_dict[r.fdn] |= {'arfcnValueEUtranDl': r.earfcn}
        # EUtranFreqRelation
        mask = ((self.usid.df_lte_rel.site == node) & (~self.usid.df_lte_rel.flag) & (self.usid.df_lte_rel.cr_flag))
        for r in self.usid.df_lte_rel.loc[mask].itertuples():
            s_dict[r.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r.fdn)
            s_dict[r.fdn] |= {'eutranFrequencyRef': F'{site.enb_enw},EUtranFrequency={r.freq}'}
        # ExternalENodeBFunction, TermPointToENB, ExternalEUtranCellFDD, EUtranCellRelation
        for nodeid in sorted(df_new.nodeid.unique()):
            if site.enodeb_id == nodeid:
                # for t_cell in df_new.loc[df_new.nodeid == nodeid].t_cell.unique():
                for r_c in df_new.loc[(df_new.nodeid == nodeid)].itertuples():
                    s_dict[r_c.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r_c.fdn)
                    s_dict[r_c.fdn] |= {'isRemoveAllowed': 'false', 'neighborCellRef': F'{site.enb},EUtranCellFDD={r_c.t_cell}'}
            else:
                # ExternalENodeBFunction, TermPointToENB
                ext_mo_flag, ext_mo = True, F'{site.enb_enw},ExternalENodeBFunction=310410-{nodeid}'
                for mo in site.get_mos_with_parent_moc(parent=site.enb_enw, moc='ExternalENodeBFunction'):
                    if site.get_mo_para(mo, 'eNBId') == nodeid:
                        ext_mo = mo
                        ext_mo_flag = False
                        break
                if ext_mo_flag:
                    s_dict[ext_mo] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=ext_mo)
                    s_dict[ext_mo] |= {'eNBId': nodeid, 'eNodeBPlmnId': plmn, 'eSCellCapacityScaling': '100', 'mfbiSupport': 'true'}
                if len(site.get_mos_with_parent_moc(parent=ext_mo, moc='TermPointToENB')) == 0:
                    tpt_ext_mo = F'{ext_mo},TermPointToENB=310410-{nodeid}'
                    s_dict[tpt_ext_mo] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=tpt_ext_mo)
                    s_dict[tpt_ext_mo] |= {'administrativeState': '1 (UNLOCKED)', 'ipAddress': '0.0.0.0', 'ipv6Address': '::'}
                # ExternalEUtranCellFDD
                for r in df_new.loc[(df_new.nodeid == nodeid)].drop_duplicates().groupby([
                    'site', 'nodeid', 'cellid', 'relid', 'pci', 'tac', 'freq'], sort=False, as_index=False).head(1).itertuples():
                    ext_fdd_mo_flag, ext_fdd_mo = True, F'{ext_mo},ExternalEUtranCellFDD=310410-{nodeid}-{r.cellid}'
                    for mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalEUtranCellFDD'):
                        if site.get_mo_para(mo, 'localCellId') == r.cellid:
                            ext_fdd_mo = mo
                            ext_fdd_mo_flag = False
                            break
                    if ext_fdd_mo_flag:
                        s_dict[ext_fdd_mo] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=ext_fdd_mo)
                        s_dict[ext_fdd_mo] |= {
                            'localCellId': F'{r.cellid}', 'eutranFrequencyRef': F'{site.enb_enw},EUtranFrequency={r.freq}',
                            'activePlmnList': add_plmn, 'endcAllowedPlmnList': plmn, 'noOfTxAntennas': '2',
                            'physicalLayerCellIdGroup': int(r.pci) // 3, 'physicalLayerSubCellId': int(r.pci) % 3, 'tac': r.tac
                        }
                    # EUtranCellRelation
                    for r_c in df_new.loc[(df_new.nodeid == nodeid) & (df_new.cellid == r.cellid)].itertuples():
                        s_dict[r_c.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r_c.fdn)
                        s_dict[r_c.fdn] |= {'isRemoveAllowed': 'false', 'neighborCellRef': ext_fdd_mo}
        return s_dict

    def get_enb_gutrannetwork_mos_dict(self, *, node: str) -> dict:
        # GUtraNetwork, ExternalGNodeBFunction, ExternalGUtranCell, TermPointToGNB, GUtranSyncSignalFrequency, GUtranFreqRelation, GUtranCellRelation
        s_dict = {}
        mask = (self.usid.df_lte_nr_crel.site == node) & (~self.usid.df_lte_nr_crel.flag)
        df_new = self.usid.df_lte_nr_crel.copy().loc[mask]
        if len(df_new.index) == 0:
            return s_dict
        site = self.usid.sites.get(F'site_{node}')
        # GUtraNetwork
        if site.enb_gnw not in site.mo_list:
            s_dict[site.enb_gnw] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=site.enb_gnw)
        # GUtranSyncSignalFrequency
        mask = ((self.usid.df_lte_nr_freq.site == node) & (~self.usid.df_lte_nr_freq.flag))
        for r in self.usid.df_lte_nr_freq.loc[mask].itertuples():
            s_dict[r.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r.fdn)
            s_dict[r.fdn] |= {'arfcn': r.ssbfreq, 'smtcDuration': r.duration, 'smtcOffset': r.offset, 'smtcPeriodicity': r.periodicity,
                              'smtcScs': r.scc, 'band': [self.usid.param_dict["ssbfreq"][r.ssbfreq]["band"]]}
        # GUtranFreqRelation
        mask = ((self.usid.df_lte_nr_rel.site == node) & (~self.usid.df_lte_nr_rel.flag))
        for r in self.usid.df_lte_nr_rel.loc[mask].itertuples():
            s_dict[r.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r.fdn)
            s_dict[r.fdn] |= {'gUtranSyncSignalFrequencyRef': F'{site.enb_gnw},GUtranSyncSignalFrequency={r.freq}'}
        # ExternalGNodeBFunction, TermPointToGNB
        for row_ext_gnb in df_new.groupby(['nodeid'], sort=False, as_index=False).head(1).itertuples():
            ext_mo_flag, ext_mo = True, F'{site.enb_gnw},ExternalGNodeBFunction={row_ext_gnb.ext_node}'
            for mo in site.get_mos_with_parent_moc(parent=site.enb_gnw, moc='ExternalGNodeBFunction'):
                if site.get_mo_para(mo, 'gNodeBId') == row_ext_gnb.nodeid:
                    ext_mo = mo
                    ext_mo_flag = False
                    break
            if ext_mo_flag:
                s_dict[ext_mo] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=ext_mo)
                s_dict[ext_mo] |= {'gNodeBId': row_ext_gnb.nodeid, 'gNodeBPlmnId': plmn, 'gNodeBIdLength': row_ext_gnb.nodeid_len}
            if len(site.get_mos_with_parent_moc(parent=ext_mo, moc='TermPointToGNB')) == 0:
                tpt_ext_mo = F'{ext_mo},TermPointToGNB={row_ext_gnb.ext_node}'
                s_dict[tpt_ext_mo] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=tpt_ext_mo)
                s_dict[tpt_ext_mo] |= {'administrativeState': '1 (UNLOCKED)', 'ipAddress': '0.0.0.0', 'upIpAddress': '::'}
            # ExternalEUtranCellFDD
            for r in df_new.loc[df_new.nodeid == row_ext_gnb.nodeid].drop_duplicates().groupby(
                    ['site', 't_site', 't_cell'], sort=False, as_index=False).head(1).itertuples():
                ext_fdd_mo_flag, ext_fdd_mo = True, F'{ext_mo},ExternalGUtranCell=310410-000000{r.nodeid}-{r.cellid}'
                for mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalGUtranCell'):
                    if site.get_mo_para(mo, 'localCellId') == r.cellid:
                        ext_fdd_mo = mo
                        ext_fdd_mo_flag = False
                        break
                if ext_fdd_mo_flag:
                    s_dict[ext_fdd_mo] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=ext_fdd_mo)
                    s_dict[ext_fdd_mo] |= {
                        'localCellId': F'{r.cellid}', 'gUtranSyncSignalFrequencyRef': F'{site.enb_gnw},GUtranSyncSignalFrequency={r.freq}',
                        'physicalLayerCellIdGroup': int(r.pci) // 3, 'physicalLayerSubCellId': int(r.pci) % 3,
                        'plmnIdList': add_plmn, 'isRemoveAllowed': 'false', 'nRTAC': -1,
                    }
                # GUtranCellRelation
                for r_c in df_new.loc[(df_new.nodeid == r.nodeid) & (df_new.cellid == r.cellid)].itertuples():
                    s_dict[r_c.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r_c.fdn)
                    s_dict[r_c.fdn] |= {'isRemoveAllowed': 'false', 'neighborCellRef': ext_fdd_mo}
        return s_dict

    def get_gnb_nrnetwork_mos_dict(self, node):
        # NRNetwork, NRFrequency, NRFreqRelation, ExternalGNBCUCPFunction, ExternalNRCellCU, NRCellRelation
        # McpcPSCellNrFreqRelProfile, UeMCNrFreqRelProfile, McpcPCellNrFreqRelProfile, TrStSaNrFreqRelProfile
        s_dict = {}
        mask = ((self.usid.df_nr_crel.site == node) & (~self.usid.df_nr_crel.flag))
        df_new = self.usid.df_nr_crel.copy()
        df_new = self.usid.df_nr_crel.copy().loc[mask]
        if len(df_new.index) == 0:
            return s_dict
        site = self.usid.sites.get(F'site_{node}')
        # NRNetwork
        if site.gnb_nnw != '' and site.gnb_nnw not in site.mo_list:
            s_dict[site.gnb_nnw] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=site.gnb_nnw)
        # NRFrequency
        mask = ((self.usid.df_nr_freq.site == node) & (~self.usid.df_nr_freq.flag))
        for r in self.usid.df_nr_freq.loc[mask].itertuples():
            s_dict[r.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r.fdn)
            s_dict[r.fdn] |= {'arfcnValueNRDl': r.ssbfreq, 'smtcScs': r.scc, 'smtcDuration': r.duration,
                              'smtcOffset': r.offset, 'smtcPeriodicity': r.periodicity}
        # McpcPSCellNrFreqRelProfile, UeMCNrFreqRelProfile, McpcPCellNrFreqRelProfile, TrStSaNrFreqRelProfile
        mask = ((self.usid.df_nr_rel.site == node) & (~self.usid.df_nr_rel.flag))
        for ssbfreq in self.usid.df_nr_rel.loc[mask].ssbfreq.unique():
            mos_list = self.get_nr_freq_rel_id_n_profile_mos(ssbfreq=ssbfreq)
            relid = self.usid.df_nr_rel.loc[(mask & self.usid.df_nr_rel.ssbfreq == ssbfreq), 'relid'].iloc[0]
            for mos in mos_list:
                if len(mos) == 0:
                    continue
                ext_mo = F'{site.gnb_cucp},{mos[0]}=1,{mos[1]}={relid}'
                if ext_mo not in site.get_mos_with_parent_moc(parent=F'{site.gnb_cucp},{mos[0]}=1', moc=mos[1]):
                    s_dict[ext_mo] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=ext_mo)
                    s_dict[ext_mo] |= {'ueConfGroupType': '0 (UE_MOBILITY_GROUP)'}
        # NRFreqRelation
        for r in self.usid.df_nr_rel.loc[mask].itertuples():
            s_dict[r.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r.fdn)
            s_dict[r.fdn] |= {'nRFrequencyRef': F'{site.gnb_nnw},NRFrequency={r.freq}'}
        # ExternalGNBCUCPFunction, ExternalNRCellCU, NRCellRelation
        for nodeid in sorted(df_new.nodeid.unique()):
            if site.gnodeb_id == nodeid:
                # NRCellRelation
                for r_c in df_new.loc[(df_new.nodeid == nodeid)].itertuples():
                    s_dict[r_c.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r_c.fdn)
                    s_dict[r_c.fdn] |= {'isRemoveAllowed': 'false', 'nRCellRef': F'{site.gnb_cucp},NRCellCU={r_c.t_cell}',
                                        'nRFreqRelationRef': F'{site.gnb_cucp},NRCellCU={r_c.cell},NRFreqRelation={r_c.relid}'}
            else:
                row_ext = df_new.loc[(df_new.nodeid == nodeid)].head(1).iloc[0]
                ext_mo_flag, ext_mo = True, F'{site.gnb_nnw},ExternalGNBCUCPFunction={row_ext.get("t_site")}'
                for mo in site.get_mos_with_parent_moc(parent=site.gnb_nnw, moc='ExternalGNBCUCPFunction'):
                    if site.get_mo_para(mo, 'gNBId') == nodeid:
                        ext_mo_flag, ext_mo = False, mo
                        break
                if ext_mo_flag:
                    s_dict[ext_mo] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=ext_mo)
                    s_dict[ext_mo] |= {'gNBId': row_ext.get("nodeid"), 'gNBIdLength': row_ext.get("nodeid_len"), 'pLMNId': '{"mcc": 310, "mnc": 410}'}
                # ExternalNRCellCU
                for r in df_new.loc[df_new.nodeid == nodeid].groupby([
                        'site', 'nodeid', 'cellid', 'relid', 'pci', 'tac', 'freq'], sort=False, as_index=False).head(1).itertuples():
                    ext_fdd_mo_flag, ext_fdd_mo = True, F'{ext_mo},ExternalNRCellCU={r.t_cell}'
                    for mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalNRCellCU'):
                        if site.get_mo_para(mo, 'cellLocalId') == r.cellid:
                            ext_fdd_mo_flag, ext_fdd_mo = False, mo
                            break
                    if ext_fdd_mo_flag:
                        s_dict[ext_fdd_mo] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=ext_fdd_mo)
                        s_dict[ext_fdd_mo] |= {'cellLocalId': r.cellid, 'nRPCI': r.pci, 'nRTAC': r.tac,
                                               'plmnIdList': '[{"mcc": 310, "mnc": 410}, {"mcc": 313, "mnc": 100}]',
                                               'nRFrequencyRef': F'{site.gnb_nnw},NRFrequency={r.freq}'}
                    # NRCellRelation
                    for r_c in df_new.loc[(df_new.nodeid == nodeid) & (df_new.cellid == r.cellid)].itertuples():
                        s_dict[r_c.fdn] = self.get_attribute_dict_for_mo_with_create_flag(node=node, mo=r_c.fdn)
                        s_dict[r_c.fdn] |= {'isRemoveAllowed': 'false', 'nRCellRef': ext_fdd_mo,
                                            'nRFreqRelationRef': F'{site.gnb_cucp},NRCellCU={r_c.cell},NRFreqRelation={r_c.relid}'}
        return s_dict


    def get_nr_freq_rel_id_n_profile_mos(self, *, ssbfreq: str) -> list:
        band = self.usid.get('ssbfreq').get(ssbfreq, {}).get('band', '5')
        mos_list = [
            ('Mcpc', 'McpcPCellNrFreqRelProfile', 'McpcPCellNrFreqRelProfileUeCfg'),
            ('Mcpc', 'McpcPSCellNrFreqRelProfile', 'McpcPSCellNrFreqRelProfileUeCfg'),
            ('UeMC', 'UeMCNrFreqRelProfile', 'UeMCNrFreqRelProfileUeCfg'),
        ]
        if band in ['260', '261', '258']:
            mos_list = []
        elif band in ['77']:
            mos_list += [('TrafficSteering', 'TrStSaNrFreqRelProfile', 'TrStSaNrFreqRelProfileUeCfg')]
        return mos_list

    def mos_normalize_parameter(self, *, val: str or list or dict or int or bool) -> str:
        if type(val) is dict: return ','.join([F"{key}={self.mos_normalize_parameter(val=val.get(key))}" for key in val])
        elif type(val) is list:
            if sum([type(_) is dict for _ in val]) == 0: return ' '.join([self.mos_normalize_parameter(val=_) for _ in val])
            else: return ';'.join([self.mos_normalize_parameter(val=_) for _ in val])
        elif val in [None, 'None', '', '""']: return ''
        elif 'ManagedElement' in val: return re.search(r'.*ManagedElement=[^,]*,(.*)', val).group(1)
        elif re.match('(.*)\s\((.*)\)$', val): return re.match('(.*)\s\((.*)\)$', val).group(1)
        else: return val.strip('"')

    def mos_normalize_gs_parameter(self, *, gs_val):
        if gs_val.startswith('[') or gs_val.startswith('{'):
            try: gs_val = json.loads(gs_val)
            except:
                self.log.info('Not Able to Convert to JSON. Please check value', gs_val)
                gs_val = {'Error': 'CHECK GS SHEET'}
        return self.cli_normalize_parameter(val=gs_val)
        #
        # if pd.isnull(gs_val) or not (gs_val.startswith('[') or gs_val.startswith('{')) or (gs_val == ''):
        #     return self.mos_normalize_parameter(val=gs_val)
        # else:
        #     try: json_gold_val = json.loads(gs_val)
        #     except:
        #         self.log.info('Not Able to Convert to JSON. Please check value', gs_val)
        #         json_gold_val = {'ERROR': 'CHECK GS SHEET'}
        #     return self.mos_normalize_parameter(val=json_gold_val)

    @staticmethod
    def get_moc_mocid_moidval_from_fdn(mo):
        moc = re.search(r'.*,(.*)=.*', mo).group(1)
        mo_id_val = re.search(r'.*=(.*)$', mo).group(1)
        return moc, moc[0].lower() + moc[1:] + 'Id', mo_id_val

    def cli_normalize_parameter(self, *, val: str or list or dict or int or bool) -> str:
        """
        Special Character --- *()[]\+<>= and space
        Special characters are any characters other than the supported characters.
        These characters must be wrapped in quotes to be accepted in the scope name or attribute value part of the command.
        *()[]\+<>= and space - Special C
        :rtype: str
        """
        val_type = type(val)
        if val_type in [int, bool]: val = str(val).lower()
        elif val_type is str and len(val) == 0: pass
        elif val in ['null', 'empty']: val = F'<{val}>'
        elif val_type in [dict, list] and len(val) == 0: val = '<empty>'
        elif val_type == list: val = '[' + ', '.join([self.cli_normalize_parameter(val=_) for _ in val]) + ']'
        elif val_type == dict:
            if val.get('attributes', {}).get('xc:operation', '') == 'delete': val = '<empty>'
            else: val = '{' + ', '.join([F"{key}={self.cli_normalize_parameter(val=val.get(key))}" for key in val]) + '}'
        elif len([_ for _ in ['{', '[', '('] if str(val).startswith(_)]) > 0: val = val
        elif re.match('(.*)\s\((.*)\)$', val): val = re.match('(.*)\s\((.*)\)$', val).group(2)
        elif re.match('(.*),(.*)=(.*)$', val) and 'ManagedElement=' not in val: val = F'"{self.ManagedElement},{val}"'
        elif re.match('(.*),(.*)=(.*)$', val) and 'SubNetwork=' not in val and 'ManagedElement=' in val:
            val = F'"{self.ManagedElement},{re.match(".*ManagedElement=([^,]*),(.*)$", val).group(2)}"'
        elif len([_ for _ in ['*', '(', ')', '[', ']', '\\', '+', '<', '>', '=', ' ', ',', ':'] if _ in str(val)]) > 0:
            val = F'"{val}"'
        return val

    def cli_normalize_gs_parameter(self, *, gs_val: str) -> str:
        if gs_val.startswith('[') or gs_val.startswith('{'):
            try: gs_val = json.loads(gs_val)
            except:
                self.log.info('Not Able to Convert to JSON. Please check value', gs_val)
                gs_val = {'Error': 'CHECK GS SHEET'}
        return self.cli_normalize_parameter(val=gs_val)

    @staticmethod
    def validate_null_value(*, val: str) -> bool:
        return val in [None, 'None', 'null', '', [], {}]

    def create_script_from_dict(self, mo, mo_dict, script_type):
        script_list = []
        if len(mo) == 0: return script_list
        moc, moid, moidval = self.get_moc_mocid_moidval_from_fdn(mo)
        self.ManagedElement = re.search(r'(.*,ManagedElement=[^,=]*),.*', mo).group(1)
        if moidval != mo_dict.get(moid):
            self.log(F'ID Mismatch for MO {mo}')
            self.log(F'{moc}--{moid}--{moidval}----{mo_dict.get(moid)}')
        if script_type == 'mos':
            mo_ldn = re.search(r'.*ManagedElement=[^,]*,(.*)', mo).group(1) if 'ManagedElement=' in mo else mo
            if len(mo_ldn) > 0:
                script_list.append(F'crn {mo_ldn}')
                for key in mo_dict:
                    if str(key).lower() == str(moid).lower() or self.validate_null_value(val=mo_dict[key]): continue
                    script_list.append(F'{key} {self.mos_normalize_gs_parameter(gs_val=mo_dict[key])}')
                script_list.extend(['end', ''])
        elif script_type == 'cli':
            script_list.extend([F'create', F'FDN : {mo}', F'{moid} : {moidval}'])
            for key in mo_dict:
                if str(key).lower() == str(moid).lower() or self.validate_null_value(val=mo_dict[key]): continue
                script_list.append(F'{key} : {self.cli_normalize_gs_parameter(gs_val=mo_dict.get(key))}')
            script_list.append('')
        elif script_type == 'cmedit':
            script_str = F'cmedit create {mo} {moid}={moidval};'
            for key in mo_dict:
                if str(key).lower() == str(moid).lower() or self.validate_null_value(val=mo_dict[key]): continue
                script_str += F'{key}={self.cli_normalize_gs_parameter(gs_val=mo_dict.get(key))};'
            script_list.append(script_str[:-1])
        return script_list

    def get_end_mocid_moid(self, *, mo: str) -> tuple:
        return mo.split(',')[-1].split('=')[0], mo.split('=')[-1]

    def cmedit_cli_mo_form_dict(self, *, mo: str, para_dict: dict, cli_flag: bool) -> list:
        # cli_flag ----> True: cli, False: cmedit
        script = []
        if 'attributes' not in para_dict.keys(): return [F'#### Error in Parameters {mo}', '']
        s_type = para_dict.get('attributes').get('xc:operation')
        if s_type == 'update': s_type = 'set'
        moc, moid = mo.split(',')[-1].split('=')[0], mo.split('=')[-1]
        mocid = moc[0].lower() + moc[1:] + 'Id'
        parameter_list = [_ for _ in para_dict.keys() if _ not in ['attributes', mocid] and para_dict[_] not in [None, 'None', '', [], {}]]
        if s_type == 'set' and len(parameter_list) == 0: pass
        elif cli_flag:
            script += [s_type, F'FDN : {mo}']
            if s_type in ['create', 'set']:
                if s_type == 'create': script += [F'{mocid} : {moid}']
                for key in parameter_list:
                    script.append(F'{key} : {self.cli_normalize_gs_parameter(gs_val=para_dict.get(key))}')
            script.append('')
        else:
            script_str = F'cmedit {s_type} {mo} '
            if s_type == 'delete': script_str += '-ALL --force'
            else:
                if s_type == 'create': script_str += F'{mocid}:{moid}; '
                for key in parameter_list:
                    script_str += F'{key}:{self.cli_normalize_gs_parameter(gs_val=para_dict.get(key))}; '
                script_str = script_str[:-2]
                if s_type == 'set':  script_str += ' --force'
            script.append(script_str)
        return script

    def write_scripts_to_file(self, *, aa: str) -> None:
        pass
        # for node in self.s_dict.keys():
        #     if not os.path.exists(os.path.dirname(file_name)):
        #         os.makedirs(os.path.dirname(file_name))
        #     with open(file_name, 'a') as f:
        #         f.write('\n'.join(script_list))


    @staticmethod
    def write_script_to_file(file_name, script_list, s_type, node):
        if s_type == 'mos':
            script_list = [
                              F'$date = `date +%Y%m%d_%H%M%S`',
                              F'l+ LogFile_{os.path.basename(file_name)[:-4]}_$date.log',
                              F'lt all',
                              F'confbd+',
                              F'',
                              F'####:- NODE NAME -:####',
                              F'pv $nodename',
                              F'if $nodename != {node}',
                              F'print !!! Node Name mismatch.Wrong Node. ABORT !!!',
                              F'l-',
                              F'return',
                              F'fi',
                              F'',
                          ] + script_list + [
                              F'',
                              F'',
                              # F'commit',
                              F'confbd',
                              F'l-',
                              F'',
                          ]
        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))
        with open(file_name, 'a') as f:
            f.write('\n'.join(script_list))



    # def get_script_command(self, rr):
    #     # /cm/internalmomwrite
    #     return [
    #         self.script_list_cli(rr, 'cli'),
    #         self.script_list_cli(rr, 'cmedit'),
    #         [F"seti {rr.MO.str.extract(r'.*,ManagedElement=[^,]*,(.*)')}$ {rr.Parameter} {self.mos_norm_gold_val(rr.InitialValue)}"]
    #     ]
    # def script_list_cli(self, x, script_type='cli'):
    #     val = self.cli_normalize_gs_parameter(val=x.InitialValue)
    #     if script_type == 'cli':
    #         return [
    #             F'set',
    #             F'FDN : {x.MO}',
    #             F'{x.Parameter} : {val}',
    #             F'',
    #         ]
    #     elif script_type == 'cmedit':
    #         return [F"cmedit set {x.MO} {x.Parameter}:{val}"]