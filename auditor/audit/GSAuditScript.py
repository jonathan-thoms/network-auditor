import pandas as pd
import os
import json
import re
from itertools import chain


class GSAuditScript:
    def __init__(self, usid):
        self.usid = usid
        self.log = self.usid.log
        # self.df_script = pd.DataFrame([], columns=['Site', 'MO', 'MOC', 'Parameter', 'InitialValue', 'Permission', 'Type', 'cmd', 'OnAir'])
        # self.usid_script_dict = {}
        df_report = self.usid.df_report.copy()
        df_report = df_report.loc[((~df_report.flag) & (df_report.Permission != 'Not Auditable'))].reset_index(drop=True, inplace=False)
        if len(df_report.index) == 0:
            return
        df_report.loc[df_report.InitialValue.isnull(), 'InitialValue'] = df_report.loc[df_report.InitialValue.isnull(), 'GSValue']
        df_report['mos_MO'] = df_report.MO
        df_report.mos_MO = df_report.mos_MO.str.extract(r'.*,ManagedElement=[^,]*,(.*)').squeeze()
        df_report[['cli_cmd', 'cmedit_cmd', 'internal_cmd', ]] = df_report.apply(self.get_script_command, axis=1, result_type='expand')
        # AlarmPort:filterAlgorithm --- Add Lock and Unlock if filterAlgorithm need to be changed.
        mask = ((df_report.MOC == 'AlarmPort') & (df_report.Parameter == 'filterAlgorithm'))
        if len(df_report.loc[mask].index) > 0:
            df_report.loc[mask, 'cli_cmd'] = df_report.loc[mask].apply(lambda x: self.get_filteralgorithm(rr=x, types='cli'), axis=1)
            df_report.loc[mask, 'cmedit_cmd'] = df_report.loc[mask].apply(lambda x: self.get_filteralgorithm(rr=x, types='cmedit'), axis=1)
        df_report.sort_values(by=['Site', 'MO', 'Parameter'], inplace=True)
        df_report.drop(['flag', 'GSValue', 'CurrentValue'], axis=1, inplace=True)

        # lte_nr_special_parameter_for_endc
        for row in self.usid.df_script_type.itertuples():
            if row.MO == 'NN':
                df_report.loc[((df_report.MOC == row.MOC) & (df_report.Parameter == row.Parameter)), 'Type'] = row.script_type
            else:
                df_report.loc[((df_report.MO.str.endswith(row.MO)) & (df_report.Parameter == row.Parameter)), 'Type'] = row.script_type

        for node in df_report.Site.unique():
            # LTE ---> LTE Relations
            nw_dict = self.get_eutran_network_mos_dict_to_be_created(node)
            for st in ['cli', 'cmedit']:
                lines = []
                file_name = F'01_lte_lte_eutran_rel_cr_{node}_{self.usid.sw_ver}_{st}.txt'
                for mo_fdn in nw_dict.keys():
                    lines += self.create_script_from_dict(mo_fdn, nw_dict.get(mo_fdn), st)
                if len(lines) > 0:
                    self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)
            # LTE ---> NR Relations
            nw_dict = self.get_gutran_network_mos_dict_to_be_created(node)
            for st in ['cli', 'cmedit']:
                lines = []
                file_name = F'02_lte_nr_gutran_rel_cr_{node}_{self.usid.sw_ver}_{st}.txt'
                for mo_fdn in nw_dict.keys():
                    lines += self.create_script_from_dict(mo_fdn, nw_dict.get(mo_fdn), st)
                if len(lines) > 0:
                    self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)
            # NR ---> NR Relations
            nw_dict = self.get_nr_network_mos_dict_to_be_created(node)
            for st in ['cli', 'cmedit']:
                lines = []
                file_name = F'03_nr_nr_nrnetwork_rel_cr_{node}_{self.usid.sw_ver}_{st}.txt'
                for mo_fdn in nw_dict.keys():
                    lines += self.create_script_from_dict(mo_fdn, nw_dict.get(mo_fdn), st)
                if len(lines) > 0:
                    self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)

            df_temp = df_report.loc[df_report.Site == node].copy()
            if len(df_temp.index) == 0:
                continue
            sctipt_dict = {
                '00_enb_gnb_on_air_defult': df_temp.loc[(df_temp.Type.isin(['Defult']))],
                '01_enb_on_air_node': df_temp.loc[(df_temp.Type.isin(['LTE']))],
                '02_enb_on_air_cell': df_temp.loc[((df_temp.Type.isin(['LTECell'])) & (df_temp.OnAir.isin([1])))],
                '03_enb_off_air_cell': df_temp.loc[((df_temp.Type.isin(['LTECell'])) & (df_temp.OnAir.isin([0])))],
                '04_enb_ratfreqprio': df_temp.loc[(df_temp.Type.isin(['LTE_RATFreqPrio']))],
                '05_enb_lte_relation': df_temp.loc[(df_temp.Type.str.startswith('LTERelation_EUtran', na=False))],
                '06_enb_nr_relation': df_temp.loc[(df_temp.Type.str.startswith('LTERelation_GUtran', na=False))],
                '07_enb_gnb_parameter_for_endc': df_temp.loc[(df_temp.Type.isin(['LTENR_para']))],

                '08_gnb_on_air_node': df_temp.loc[(df_temp.Type.isin(['NR']))],
                '09_gnb_on_air_cell': df_temp.loc[((df_temp.Type.isin(['NRCell'])) & (df_temp.OnAir.isin([1])))],
                '10_gnb_off_air_cell': df_temp.loc[((df_temp.Type.isin(['NRCell'])) & (df_temp.OnAir.isin([0])))],
                '11_gnb_nr_relation': df_temp.loc[(df_temp.Type.str.startswith('NRRelation', na=False))],
            }

            # ecolumns = ['OnAir', 'Site', 'MO', 'Parameter', 'InitialValue', 'Permission', 'Suffix', 'Type', 'MOC', 'mos_MO']
            for script_file in sctipt_dict.keys():
                df_tmp = sctipt_dict[script_file].copy()
                if len(df_tmp.index) == 0: continue
                for st in ['cli', 'cmedit']:
                    lines = list(chain(*df_tmp.loc[(df_tmp.Permission == 'Internal')][F'internal_cmd']))
                    if len(lines) > 0:
                        file_name = F'internalmom_{script_file}_{node}_{self.usid.sw_ver}_mos.mos'
                        self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, 'mos', node)
                    lines = list(chain(*df_tmp.loc[(df_tmp.Permission != 'Internal')][F'{st}_cmd']))
                    if len(lines) > 0:
                        file_name = F'{script_file}_{node}_{self.usid.sw_ver}_{st}.txt'
                        self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)

    def get_script_command(self, rr):
        # /cm/internalmomwrite
        return [
            self.script_list_cli(rr, 'cli'),
            self.script_list_cli(rr, 'cmedit'),
            [F'seti {rr.mos_MO}$ {rr.Parameter} {self.mos_norm_gold_val(rr.InitialValue)}']
        ]

    def get_filteralgorithm(self, rr, types='cli'):
        # if rr.MOC == 'AlarmPort' and rr.Parameter == 'filterAlgorithm':
        val = self.cmedit_norm_gold_val(rr.InitialValue, re.search(r'(.*,ManagedElement=[^,=]*),.*', rr.MO).group(1))
        if self.usid.sites.get('site_' + str(rr.Site)).get_mo_para(mo=rr.MO, para='administrativeState')[0] == '1':
            if types == 'cli':
                return [F'set', F'FDN : {rr.MO}', F'administrativeState: LOCKED', F'{rr.Parameter} : {val}', F'',
                        F'set', F'FDN : {rr.MO}', F'administrativeState: UNLOCKED', F'']
            elif types == 'cmedit':
                return [F"cmedit set {rr.MO} administrativeState:LOCKED,{rr.Parameter}:{val}", F"cmedit set {rr.MO} administrativeState:UNLOCKED"]
        return rr.get(F'{types}_cmd', [])

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

    def mos_norm_gold_val_json(self, val):
        if type(val) is dict:
            return ','.join([F"{key}={self.mos_norm_gold_val_json(val.get(key))}" for key in val])
        elif type(val) is list:
            if sum([type(_) is dict for _ in val]) == 0:
                return ' '.join([self.mos_norm_gold_val_json(_) for _ in val])
            else:
                return ';'.join([self.mos_norm_gold_val_json(_) for _ in val])
        elif val in [None, 'None', '', '""']:
            return ''
        elif 'ManagedElement' in val:
            return self.get_ldn_from_fdn(val)
        elif re.match(r'(.*)\s\((.*)\)$', val):
            return re.match(r'(.*)\s\((.*)\)$', val).group(1)
        else:
            return val.strip('"')

    def mos_norm_gold_val(self, gs_val):
        if pd.isnull(gs_val) or not (gs_val.startswith('[') or gs_val.startswith('{')) or (gs_val == ''):
            return self.mos_norm_gold_val_json(gs_val)
        else:
            try:
                json_gold_val = json.loads(gs_val)
            except:
                self.log.info('Not Able to Convert to JSON. Please check value', gs_val)
                json_gold_val = {'XXXXXX': 'CHECK GS SHEET'}
            return self.mos_norm_gold_val_json(json_gold_val)

    @staticmethod
    def get_moc_mocid_moidval_from_fdn(mo_fdn):
        moc = re.search(r'.*,(.*)=.*', mo_fdn).group(1)
        mo_id_val = re.search(r'.*=(.*)$', mo_fdn).group(1)
        return moc, moc[0].lower() + moc[1:] + 'Id', mo_id_val

    # @staticmethod
    # def get_ldn_from_fdn(fdn_mo):
    #     return re.search(r'.*ManagedElement=\w+,(.*)', fdn_mo).group(1) if 'ManagedElement=' in fdn_mo else fdn_mo

    @staticmethod
    def get_ldn_from_fdn(fdn_mo):
        return re.search(r'.*ManagedElement=[^,]*,(.*)', fdn_mo).group(1) if 'ManagedElement=' in fdn_mo else fdn_mo

    def cmedit_norm_gold_val(self, gs_val, dnprefix=''):
        if pd.isnull(gs_val) or not (gs_val.startswith('[') or gs_val.startswith('{')) or gs_val == '':
            return self.cmedit_norm_gold_val_json(gs_val, dnprefix)
        else:
            try:
                gs_val = json.loads(gs_val)
            except:
                self.log.info('Not Able to Convert to JSON. Please check value', gs_val)
                gs_val = {'Error': 'CHECK GS SHEET'}
            return self.cmedit_norm_gold_val_json(gs_val, dnprefix)

    def cmedit_norm_gold_val_json(self, gs_val, dnprefix=''):
        """
        Special Character --- *()[]+<>= and space and backward slashes
        Special characters are any characters other than the supported characters.
        These characters must be wrapped in quotes to be accepted in the scope name or attribute value part of the command.
        *()[]+<>= and space backward slashes - Special C
        """
        if type(gs_val) == list and len(gs_val) == 0:
            return "[]"
        elif type(gs_val) == dict and len(gs_val) == 0:
            return "{}"
        elif type(gs_val) not in [dict, list] and len(gs_val) == 0:
            return '<empty>'
        elif gs_val in ['null', 'empty']:
            return F'<{gs_val}>'
        elif type(gs_val) == dict:
            return '{' + ', '.join([F"{key}={self.cmedit_norm_gold_val_json(gs_val.get(key), dnprefix)}" for key in gs_val]) + '}'
        elif type(gs_val) == list:
            return '[' + ', '.join([self.cmedit_norm_gold_val_json(_, dnprefix) for _ in gs_val]) + ']'
        elif gs_val in [None, 'None', '']:
            return '<empty>'
        elif len([_ for _ in ['{', '[', '('] if str(gs_val).startswith(_)]) > 0:
            return gs_val
        elif re.match(r'(.*)\s\((.*)\)$', gs_val):
            return re.match(r'(.*)\s\((.*)\)$', gs_val).group(2)
        elif re.match(r'(.*),(.*)=(.*)$', gs_val) and 'ManagedElement=' not in gs_val and len(dnprefix) > 0:
            return F'"{dnprefix},{gs_val}"'
        elif re.match(r'(.*),(.*)=(.*)$', gs_val) and 'SubNetwork=' not in gs_val and 'ManagedElement=' in gs_val and len(dnprefix) > 0:
            return '"' + dnprefix + re.match('.*ManagedElement=([^,]*),(.*)$', gs_val).group(2) + '"'
        elif len([_ for _ in ['*', '(', ')', '[', ']', '\\', '+', '<', '>', '=', ' ', ',', ':'] if _ in str(gs_val)]) > 0:
            return F'"{gs_val}"'
        else:
            return gs_val

    def script_list_cli(self, x, script_type='cli'):
        val = self.cmedit_norm_gold_val(x.InitialValue, re.search(r'(.*,ManagedElement=[^,=]*),.*', x.MO).group(1))
        if script_type == 'cli':
            return [
                F'set',
                F'FDN : {x.MO}',
                F'{x.Parameter} : {val}',
                F'',
            ]
        elif script_type == 'cmedit':
            return [F"cmedit set {x.MO} {x.Parameter}:{val}"]

    def create_script_from_dict(self, mo_fdn, mo_dict, script_type):
        script_list = []
        if len(mo_fdn) == 0: return script_list
        moc, moid, moidval = self.get_moc_mocid_moidval_from_fdn(mo_fdn)
        dnprefix = re.search(r'(.*,ManagedElement=[^,=]*),.*', mo_fdn).group(1)
        if moidval != mo_dict.get(moid):
            self.log(F'ID Mismatch for MO {mo_fdn}')
            self.log(F'{moc}--{moid}--{moidval}----{mo_dict.get(moid)}')
        if script_type == 'mos':
            mo_ldn = self.get_ldn_from_fdn(mo_fdn)
            if len(mo_ldn) > 0:
                script_list.append(F'crn {mo_ldn}')
                for key in mo_dict:
                    if str(key).lower() == str(moid).lower() or mo_dict[key] in [None, 'None', 'null', '', [], {}]: continue
                    script_list.append(F'{key} {self.mos_norm_gold_val(mo_dict[key])}')
                script_list.extend(['end', ''])
        elif script_type == 'cli':
            script_list.extend([F'create', F'FDN : {mo_fdn}', F'{moid} : {moidval}'])
            for key in mo_dict:
                if str(key).lower() == str(moid).lower() or mo_dict[key] in [None, 'None', 'null', '', [], {}]: continue
                script_list.append(F'{key} : {self.cmedit_norm_gold_val(mo_dict.get(key), dnprefix)}')
            script_list.append('')
        elif script_type == 'cmedit':
            script_str = F'cmedit create {mo_fdn} {moid}={moidval};'
            for key in mo_dict:
                if str(key).lower() == str(moid).lower() or mo_dict[key] in [None, 'None', 'null', '', [], {}]: continue
                script_str += F'{key}={self.cmedit_norm_gold_val(mo_dict.get(key), dnprefix)};'
            script_list.append(script_str[:-1])
        return script_list

    def get_mocid_and_its_value_for_fdn(self, mo_fdn):
        moc = re.search(r'.*,(.*)=.*', mo_fdn).group(1)
        return {moc[0].lower() + moc[1:] + 'Id': re.search(r'.*=(.*)$', mo_fdn).group(1)}

    def get_eutran_network_mos_dict_to_be_created(self, node):
        s_dict = {}
        df_new = self.usid.df_lte_crel.copy()
        df_new = df_new.loc[((df_new.site == node) & (~df_new.flag) & (df_new.cr_flag))]
        if len(df_new.index) == 0: return s_dict
        site = self.usid.sites.get(F'site_{node}')
        # EUtraNetwork, EUtranFrequency, EUtranFreqRelation
        if site.enb_enw != '' and site.enb_enw not in site.mo_list:
            s_dict[site.enb_enw] = self.get_mocid_and_its_value_for_fdn(site.enb_enw)
        for row in self.usid.df_lte_freq.loc[((self.usid.df_lte_freq.site == node) & (~self.usid.df_lte_freq.flag))].itertuples():
            s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
            s_dict[row.fdn] |= {'arfcnValueEUtranDl': row.earfcn}
        for row in self.usid.df_lte_rel.loc[((self.usid.df_lte_rel.site == node) & (~self.usid.df_lte_rel.flag) &
                                             (self.usid.df_lte_rel.cr_flag))].itertuples():
            s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
            s_dict[row.fdn] |= {'cellReselectionPriority': '2', 'allowedMeasBandwidth': '25',
                                'eutranFrequencyRef': F'{site.enb_enw},EUtranFrequency={row.freq}'}

        # ExternalENodeBFunction, TermPointToENB, ExternalEUtranCellFDD, EUtranCellRelation
        for nodeid in df_new.nodeid.unique():
            if site.enodeb_id == nodeid:
                # for t_cell in df_new.loc[df_new.nodeid == nodeid].t_cell.unique():
                for row_c in df_new.loc[(df_new.nodeid == nodeid)].itertuples():
                    s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
                    s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'neighborCellRef': F'{site.enb},EUtranCellFDD={row_c.t_cell}'}
            else:
                ext_mo_flag, ext_mo = True, F'{site.enb_enw},ExternalENodeBFunction=310410-{nodeid}'
                for mo in site.get_mos_with_parent_moc(parent=site.enb_enw, moc='ExternalENodeBFunction'):
                    if site.get_mo_para(mo, 'eNBId') == nodeid:
                        ext_mo = mo
                        ext_mo_flag = False
                        break
                if ext_mo_flag:
                    s_dict[ext_mo] = self.get_mocid_and_its_value_for_fdn(ext_mo)
                    s_dict[ext_mo] |= {'eNBId': nodeid, 'eNodeBPlmnId': '{"mcc": "310", "mnc": "410", "mncLength": "3"}',
                                       'eSCellCapacityScaling': '100', 'mfbiSupport': 'true'}
                if len(site.get_mos_with_parent_moc(parent=ext_mo, moc='TermPointToENB')) == 0:
                    tpt_ext_mo = F'{ext_mo},TermPointToENB=310410-{nodeid}'
                    s_dict[tpt_ext_mo] = self.get_mocid_and_its_value_for_fdn(tpt_ext_mo)
                    s_dict[tpt_ext_mo] |= {'administrativeState': '1 (UNLOCKED)', 'ipAddress': '0.0.0.0', 'ipv6Address': '::'}

                # ExternalEUtranCellFDD
                for row in df_new.loc[df_new.nodeid == nodeid].drop_duplicates().groupby([
                    'site', 'nodeid', 'cellid', 'relid', 'pci', 'tac', 'freq'], sort=False, as_index=False).head(1).itertuples():
                    ext_fdd_mo_flag, ext_fdd_mo = True, F'{ext_mo},ExternalEUtranCellFDD=310410-{nodeid}-{row.cellid}'
                    for mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalEUtranCellFDD'):
                        if site.get_mo_para(mo, 'localCellId') == row.cellid:
                            ext_fdd_mo = mo
                            ext_fdd_mo_flag = False
                            break
                    if ext_fdd_mo_flag:
                        s_dict[ext_fdd_mo] = self.get_mocid_and_its_value_for_fdn(ext_fdd_mo)
                        s_dict[ext_fdd_mo] |= {
                            'activePlmnList': '[{"mcc": "310", "mnc": "410", "mncLength": "3"}, {"mcc": "313", "mnc": "100", "mncLength": "3"}]',
                            'endcAllowedPlmnList': '{"mcc": "310", "mnc": "410", "mncLength": "3"}', 'noOfTxAntennas': '2',
                            'eutranFrequencyRef': F'{site.enb_enw},EUtranFrequency={row.freq}', 'localCellId': F'{row.cellid}',
                            'physicalLayerCellIdGroup': F'{int(row.pci) // 3}', 'physicalLayerSubCellId': F'{int(row.pci) % 3}', 'tac': F'{row.tac}'
                        }
                    for row_c in df_new.loc[(df_new.nodeid == nodeid) & (df_new.cellid == row.cellid)].itertuples():
                        s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
                        s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'neighborCellRef': ext_fdd_mo}
        return s_dict

    def get_gutran_network_mos_dict_to_be_created(self, node):
        s_dict = {}
        df_new = self.usid.df_lte_nr_crel.copy()
        df_new = df_new.loc[(df_new.site == node) & (~df_new.flag)]
        if len(df_new.index) == 0: return s_dict
        site = self.usid.sites.get(F'site_{node}')
        # GUtraNetwork, ExternalGNodeBFunction, ExternalGUtranCell, TermPointToGNB, GUtranSyncSignalFrequency, GUtranFreqRelation, GUtranCellRelation
        if site.enb_gnw not in site.mo_list:
            s_dict[site.enb_gnw] = self.get_mocid_and_its_value_for_fdn(site.enb_gnw)
        for row in self.usid.df_lte_nr_freq.loc[(self.usid.df_lte_nr_freq.site == node) & (~self.usid.df_lte_nr_freq.flag)].itertuples():
            s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
            s_dict[row.fdn] |= {'arfcn': row.ssbfreq, 'smtcDuration': row.duration, 'smtcOffset': row.offset, 'smtcPeriodicity': row.periodicity,
                                'smtcScs': row.scc, 'band': F'["{self.usid.param_dict["ssbfreq"][row.ssbfreq]["band"]}"]'}

        for row in self.usid.df_lte_nr_rel.loc[(self.usid.df_lte_nr_rel.site == node) & (~self.usid.df_lte_nr_rel.flag)].itertuples():
            s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
            s_dict[row.fdn] |= {
                'cellReselectionPriority': '7',
                'gUtranSyncSignalFrequencyRef': F'{site.enb_gnw},GUtranSyncSignalFrequency={row.freq}',
                'allowedPlmnList': '[{"mcc": "310", "mnc": "410", "mncLength": "3"}, {"mcc": "313", "mnc": "100", "mncLength": "3"}]',
                'anrMeasOn': 'true',
                'connectedModeMobilityPrio': '6',
                # 'endcB1MeasPriority': '-1',
                'qOffsetFreq': '0',
                'qQualMin': '-30',
                'qRxLevMin': '-104',
                'threshXHigh': '4',
                'threshXHighQ': '0',
                'threshXLow': '0',
                'threshXLowQ': '0',
                'timeToTriggerB1Override': '-1000',
                'triggerQuantityGUtraOverride': '0',
            }
        # ExternalGNodeBFunction, ExternalGUtranCell, TermPointToGNB,  GUtranFreqRelation, GUtranCellRelation
        for row_ext_gnb in df_new.groupby(['nodeid'], sort=False, as_index=False).head(1).itertuples():
            ext_mo_flag, ext_mo = True, F'{site.enb_gnw},ExternalGNodeBFunction={row_ext_gnb.ext_node}'
            for mo in site.get_mos_with_parent_moc(parent=site.enb_gnw, moc='ExternalGNodeBFunction'):
                if site.get_mo_para(mo, 'gNodeBId') == row_ext_gnb.nodeid:
                    ext_mo = mo
                    ext_mo_flag = False
                    break
            if ext_mo_flag:
                s_dict[ext_mo] = self.get_mocid_and_its_value_for_fdn(ext_mo)
                s_dict[ext_mo] |= {'gNodeBId': row_ext_gnb.nodeid, 'gNodeBPlmnId': '{"mcc": "310", "mnc": "410", "mncLength": "3"}',
                                   'gNodeBIdLength': row_ext_gnb.nodeid_len}
            if len(site.get_mos_with_parent_moc(parent=ext_mo, moc='TermPointToGNB')) == 0:
                tpt_ext_mo = F'{ext_mo},TermPointToGNB={row_ext_gnb.ext_node}'
                s_dict[tpt_ext_mo] = self.get_mocid_and_its_value_for_fdn(tpt_ext_mo)
                s_dict[tpt_ext_mo] |= {'administrativeState': '1 (UNLOCKED)', 'ipAddress': '0.0.0.0', 'upIpAddress': '::'}

            # ExternalEUtranCellFDD
            for row in df_new.loc[df_new.nodeid == row_ext_gnb.nodeid].drop_duplicates().groupby(['site', 't_site', 't_cell'],
                                                                                                 sort=False, as_index=False).head(1).itertuples():
                ext_fdd_mo_flag, ext_fdd_mo = True, F'{ext_mo},ExternalGUtranCell=310410-000000{row.nodeid}-{row.cellid}'
                for mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalGUtranCell'):
                    if site.get_mo_para(mo, 'localCellId') == row.cellid:
                        ext_fdd_mo = mo
                        ext_fdd_mo_flag = False
                        break
                if ext_fdd_mo_flag:
                    s_dict[ext_fdd_mo] = self.get_mocid_and_its_value_for_fdn(ext_fdd_mo)
                    s_dict[ext_fdd_mo] |= {
                        'localCellId': F'{row.cellid}',
                        'physicalLayerCellIdGroup': F'{int(row.pci) // 3}', 'physicalLayerSubCellId': F'{int(row.pci) % 3}',
                        'gUtranSyncSignalFrequencyRef': F'{site.enb_gnw},GUtranSyncSignalFrequency={row.freq}',
                        'plmnIdList': '[{"mcc": "310", "mnc": "410", "mncLength": "3"}, {"mcc": "313", "mnc": "100", "mncLength": "3"}]',
                        'isRemoveAllowed': 'false',
                        'nRTAC': '-1',
                    }
                for row_c in df_new.loc[(df_new.nodeid == row.nodeid) & (df_new.cellid == row.cellid)].itertuples():
                    s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
                    s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'neighborCellRef': ext_fdd_mo}
        return s_dict

    def get_nr_network_mos_dict_to_be_created(self, node):
        s_dict = {}
        df_new = self.usid.df_nr_crel.copy()
        df_new = df_new.loc[((df_new.site == node) & (~df_new.flag))]

        if len(df_new.index) == 0: return s_dict
        site = self.usid.sites.get(F'site_{node}')
        # NRFrequency, NRFreqRelation, NRFreqRelation
        if site.gnb_nnw != '' and site.gnb_nnw not in site.mo_list:
            s_dict[site.gnb_nnw] = self.get_mocid_and_its_value_for_fdn(site.gnb_nnw)
        for row in self.usid.df_nr_freq.loc[((self.usid.df_nr_freq.site == node) & (~self.usid.df_nr_freq.flag))].itertuples():
            s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
            s_dict[row.fdn] |= {'arfcnValueNRDl': row.ssbfreq, 'smtcScs': row.scc, 'smtcDuration': row.duration, 'smtcOffset': row.offset,
                                'smtcPeriodicity': row.periodicity}
            # # McpcPSCellNrFreqRelProfile, UeMCNrFreqRelProfile, McpcPCellNrFreqRelProfile, TrStSaNrFreqRelProfile
            # _, _, mos_list = self.get_nr_freq_rel_id_n_profile_mos(row)
            # for moc in mos_list:
            #     mos_ldn_dict[moc[1]] = F'GNBCUCPFunction=1,{moc[0]}=1,{moc[1]}={row.relid}'
            #     if mos_ldn_dict[moc[1]] in mo_list: pass
            #     if self.no_eq_change_with_dcgk_flag and len(self.site.get_mos_w_end_str(mos_ldn_dict[moc[1]])) > 0:
            #         mo_list += [mos_ldn_dict[moc[1]]]
            #     else:
            #         mo_list += [mos_ldn_dict[moc[1]]]
            #         tmp_dict = self.get_mo_dict_from_moc_node_fdn_moid(moc[1], None, None, row.relid)
            #         tmp_dict |= {self.get_moc_id(moc[1]): row.relid}
            #         if len(moc) == 3:
            #             tmp_dict[moc[2]] = self.get_mo_dict_from_moc_node_fdn_moid(moc[2], None, None, 'Base')
            #             tmp_dict[moc[2]] |= {'attributes': {'xc:operation': 'update'}}
            #             tmp_dict |= self.update_rel_cug_profile(row.freqband, moc[2], tmp_dict)
            #         mo_dict = copy.deepcopy(me_dict)
            #         mo_dict['GNBCUCPFunction'][moc[0]] = {self.get_moc_id(moc[0]): '1', moc[1]: tmp_dict}
            #         self.mo_dict[mos_ldn_dict[moc[1]]] = copy.deepcopy(mo_dict)

        for row in self.usid.df_nr_rel.loc[((self.usid.df_nr_rel.site == node) & (~self.usid.df_nr_rel.flag))].itertuples():
            s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
            s_dict[row.fdn] |= {'cellReselectionPriority': '7', 'nRFrequencyRef': F'{site.gnb_nnw},NRFrequency={row.freq}'}

        # ExternalENodeBFunction, TermPointToENB, ExternalEUtranCellFDD, EUtranCellRelation
        for nodeid in df_new.nodeid.unique():
            if site.gnodeb_id == nodeid:
                for row_c in df_new.loc[(df_new.nodeid == nodeid)].itertuples():
                    s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
                    s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'nRCellRef': F'{site.gnb_cucp},NRCellCU={row_c.t_cell}',
                                          'nRFreqRelationRef': F'{site.gnb_cucp},NRCellCU={row_c.cell},NRFreqRelation={row_c.relid}'}
            else:
                row_ext = df_new.loc[(df_new.nodeid == nodeid)].head(1).iloc[0]
                ext_mo_flag, ext_mo = True, F'{site.gnb_nnw},ExternalGNBCUCPFunction={row_ext.get("t_site")}'
                for mo in site.get_mos_with_parent_moc(parent=site.gnb_nnw, moc='ExternalGNBCUCPFunction'):
                    if site.get_mo_para(mo, 'gNBId') == nodeid:
                        ext_mo_flag, ext_mo = False, mo
                        break
                if ext_mo_flag:
                    s_dict[ext_mo] = self.get_mocid_and_its_value_for_fdn(ext_mo)
                    s_dict[ext_mo] |= {'gNBId': row_ext.get("nodeid"), 'gNBIdLength': row_ext.get("nodeid_len"),
                                       'pLMNId': '{"mcc": "310", "mnc": "410"}'}
                # ExternalNRCellCU
                for row in df_new.loc[df_new.nodeid == nodeid].groupby([
                    'site', 'nodeid', 'cellid', 'relid', 'pci', 'tac', 'freq'], sort=False, as_index=False).head(1).itertuples():
                    ext_fdd_mo_flag, ext_fdd_mo = True, F'{ext_mo},ExternalNRCellCU={row.t_cell}'
                    for mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalNRCellCU'):
                        if site.get_mo_para(mo, 'cellLocalId') == row.cellid:
                            ext_fdd_mo_flag, ext_fdd_mo = False, mo
                            break
                    if ext_fdd_mo_flag:
                        s_dict[ext_fdd_mo] = self.get_mocid_and_its_value_for_fdn(ext_fdd_mo)
                        s_dict[ext_fdd_mo] |= {'cellLocalId': row.cellid, 'nRPCI': row.pci, 'nRTAC': row.tac,
                                               'plmnIdList': '[{"mcc": "310", "mnc": "410"}, {"mcc": "313", "mnc": "100"}]',
                                               'nRFrequencyRef': F'{site.gnb_nnw},NRFrequency={row.freq}'}
                    for row_c in df_new.loc[(df_new.nodeid == nodeid) & (df_new.cellid == row.cellid)].itertuples():
                        s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
                        s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'nRCellRef': ext_fdd_mo,
                                              'nRFreqRelationRef': F'{site.gnb_cucp},NRCellCU={row_c.cell},NRFreqRelation={row_c.relid}'}
        return s_dict

    def get_nr_freq_rel_id_n_profile_mos(self, freq: object) -> tuple:
        """ :rtype: tuple """
        freqband = str(freq.freqband).upper()
        freq_id = F'{freq.ssbfrequency}-{freq.ssbsubcarrierspacing}'
        freq_mo_id = F'{freq.ssbfrequency}-{freq.ssbsubcarrierspacing}-{freq.ssbperiodicity}-{freq.ssboffset}-{freq.ssbduration}'
        mos_list = [
            ('Mcpc', 'McpcPCellNrFreqRelProfile', 'McpcPCellNrFreqRelProfileUeCfg'),
            ('Mcpc', 'McpcPSCellNrFreqRelProfile', 'McpcPSCellNrFreqRelProfileUeCfg'),
            ('UeMC', 'UeMCNrFreqRelProfile', 'UeMCNrFreqRelProfileUeCfg'),
        ]
        if freqband in ["N260", "N261", "N258"]:
            mos_list = []
        elif freqband in ['N077']:
            mos_list += [('TrafficSteering', 'TrStSaNrFreqRelProfile', 'TrStSaNrFreqRelProfileUeCfg')]
        return freq_id, freq_mo_id, mos_list

# class GSAuditScript:
#     def __init__(self, usid):
#         self.usid = usid
#         self.log = self.usid.log
#         # self.df_script = pd.DataFrame([], columns=['Site', 'MO', 'MOC', 'Parameter', 'InitialValue', 'Permission', 'Type', 'cmd', 'OnAir'])
#         # self.usid_script_dict = {}
#         df_report = self.usid.df_report.copy()
#         df_report = df_report.loc[((~df_report.flag) & (df_report.Permission != 'Not Auditable'))].reset_index(drop=True, inplace=False)
#         if len(df_report.index) == 0: return
#         df_report.loc[df_report.InitialValue.isnull(), 'InitialValue'] = df_report.loc[df_report.InitialValue.isnull(), 'GSValue']
#         df_report['mos_MO'] = df_report.MO
#         df_report.mos_MO = df_report.mos_MO.str.extract(r'.*,ManagedElement=[^,]*,(.*)').squeeze()
#         df_report[['mos_cmd', 'cli_cmd', 'cmedit_cmd', 'internal_cmd', ]] = df_report.apply(self.get_script_command, axis=1, result_type='expand')
#         df_report.sort_values(by=['Site', 'MO', 'Parameter'], inplace=True)
#         df_report.drop(['flag', 'GSValue', 'CurrentValue'], axis=1, inplace=True)
#
#         # lte_nr_special_parameter_for_endc
#         for row in self.usid.df_script_type.itertuples():
#             if row.MO == 'NN':
#                 df_report.loc[((df_report.MOC == row.MOC) & (df_report.Parameter == row.Parameter)), 'Type'] = row.script_type
#             else:
#                 df_report.loc[((df_report.MO.str.endswith(row.MO)) & (df_report.Parameter == row.Parameter)), 'Type'] = row.script_type
#
#         for node in df_report.Site.unique():
#             # LTE ---> LTE Relations
#             nw_dict = self.get_eutran_network_mos_dict_to_be_created(node)
#             for st in ['mos', 'cli', 'cmedit']:
#                 lines = []
#                 file_name = F'01_lte_lte_eutran_rel_cr_{node}_{self.usid.sw_ver}_{st}.{st if st == "mos" else "txt"}'
#                 for mo_fdn in nw_dict.keys(): lines += self.create_script_from_dict(mo_fdn, nw_dict.get(mo_fdn), st)
#                 if len(lines) > 0: self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)
#             # LTE ---> NR Relations
#             nw_dict = self.get_gutran_network_mos_dict_to_be_created(node)
#             for st in ['mos', 'cli', 'cmedit']:
#                 lines = []
#                 file_name = F'02_lte_nr_gutran_rel_cr_{node}_{self.usid.sw_ver}_{st}.{st if st == "mos" else "txt"}'
#                 for mo_fdn in nw_dict.keys(): lines += self.create_script_from_dict(mo_fdn, nw_dict.get(mo_fdn), st)
#                 if len(lines) > 0: self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)
#             # NR ---> NR Relations
#             nw_dict = self.get_nr_network_mos_dict_to_be_created(node)
#             for st in ['mos', 'cli', 'cmedit']:
#                 lines = []
#                 file_name = F'03_nr_nr_nrnetwork_rel_cr_{node}_{self.usid.sw_ver}_{st}.{st if st == "mos" else "txt"}'
#                 for mo_fdn in nw_dict.keys(): lines += self.create_script_from_dict(mo_fdn, nw_dict.get(mo_fdn), st)
#                 if len(lines) > 0: self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)
#
#             df_temp = df_report.loc[df_report.Site == node].copy()
#             if len(df_temp.index) == 0: continue
#             sctipt_dict = {
#                 '05_lte_nr_live_defult': df_temp.loc[(df_temp.Type.isin(['Defult']))],
#                 '11_lte_live_node': df_temp.loc[(df_temp.Type.isin(['LTE']))],
#                 '12_lte_live_cell': df_temp.loc[((df_temp.Type.isin(['LTECell'])) & (df_temp.OnAir.isin([1])))],
#                 '13_lte_non_live_cell': df_temp.loc[((df_temp.Type.isin(['LTECell'])) & (df_temp.OnAir.isin([0])))],
#                 '14_lte_ratfreqprio': df_temp.loc[(df_temp.Type.isin(['LTE_RATFreqPrio']))],
#                 '15_lte_lte_umts_relation': df_temp.loc[((df_temp.Type.str.startswith('LTERelation_EUtran', na=False)) |
#                                                          (df_temp.Type.str.startswith('LTERelation_Utran', na=False)))],
#                 '16_lte_nr_relation': df_temp.loc[(df_temp.Type.str.startswith('LTERelation_GUtran', na=False))],
#                 # '15_lte_lte_umts_relation': df_temp.loc[df_temp.Type.isin(['LTERelation_EUtranFrequency', 'LTERelation_EUtranFreqRelation',
#                 #                                                            'LTERelation_EUtranCellRelation', 'LTERelation_UtranFreqRelation'])],
#                 # '16_lte_nr_relation': df_temp.loc[df_temp.Type.isin(['LTERelation_GUtranSyncSignalFrequency', 'LTERelation_GUtranFreqRelation',
#                 #                                                      'LTERelation_GUtranCellRelation'])],
#                 '19_lte_nr_parameter_for_endc': df_temp.loc[(df_temp.Type.isin(['LTENR_para']))],
#
#                 '21_nr_live_node': df_temp.loc[(df_temp.Type.isin(['NR']))],
#                 '22_nr_live_cell': df_temp.loc[((df_temp.Type.isin(['NRCell'])) & (df_temp.OnAir.isin([1])))],
#                 '23_nr_non_live_cell': df_temp.loc[((df_temp.Type.isin(['NRCell'])) & (df_temp.OnAir.isin([0])))],
#                 '24_nr_nr_relation': df_temp.loc[(df_temp.Type.str.startswith('NRRelation', na=False))],
#             }
#
#             # ecolumns = ['OnAir', 'Site', 'MO', 'Parameter', 'InitialValue', 'Permission', 'Suffix', 'Type', 'MOC', 'mos_MO']
#             for script_file in sctipt_dict.keys():
#                 df_tmp = sctipt_dict[script_file].copy()
#                 if len(df_tmp.index) == 0: continue
#                 for st in ['mos', 'cli', 'cmedit']:
#                     if st == 'mos':
#                         lines = list(chain(*df_tmp.loc[(df_tmp.Permission != 'Internal')][F'{st}_cmd']))
#                         lines += list(chain(*df_tmp.loc[(df_tmp.Permission == 'Internal')][F'internal_cmd']))
#                     else:
#                         lines = list(chain(*df_tmp.loc[(df_tmp.Permission == 'Internal')][F'internal_cmd']))
#                         if len(lines) > 0:
#                             file_name = F'internalmom_{script_file}_{node}_{self.usid.sw_ver}_mos.mos'
#                             self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, 'mos', node)
#                         lines = list(chain(*df_tmp.loc[(df_tmp.Permission != 'Internal')][F'{st}_cmd']))
#                     if len(lines) > 0:
#                         file_name = F'{script_file}_{node}_{self.usid.sw_ver}_{st}.{st if st == "mos" else "txt"}'
#                         self.write_script_to_file(os.path.join(self.usid.outdir, st, node, file_name), lines, st, node)
#
#     def get_script_command(self, rr):
#         # /cm/internalmomwrite
#         return [
#             [F'set1x {rr.mos_MO}$ {rr.Parameter} {self.mos_norm_gold_val(rr.InitialValue)}'],
#             self.script_list_cli(rr, 'cli'),
#             self.script_list_cli(rr, 'cmedit'),
#             [F'seti {rr.mos_MO}$ {rr.Parameter} {self.mos_norm_gold_val(rr.InitialValue)}']
#         ]
#
#     @staticmethod
#     def write_script_to_file(file_name, script_list, s_type, node):
#         if s_type == 'mos':
#             script_list = [
#                              F'lt all',
#                              F'$DATE = `date +%Y%m%d_%H%M%S`',
#                              F'l+ LogFile_{os.path.basename(file_name)[:-4]}_$DATE.log',
#                              F'confbd+',
#                              F'',
#                              F'####:- NODE NAME -:####',
#                              F'pv $nodename',
#                              F'if $nodename != {node}',
#                              F'print !!! Node Name mismatch.Wrong Node. ABORT !!!',
#                              F'l-',
#                              F'return',
#                              F'fi',
#                              F'',
#                          ] + script_list + [
#                              F'',
#                              F'',
#                              F'commit',
#                              F'confbd',
#                              F'l-',
#                              F'',
#                          ]
#         if not os.path.exists(os.path.dirname(file_name)): os.makedirs(os.path.dirname(file_name))
#         with open(file_name, 'a') as f: f.write('\n'.join(script_list))
#
#     def mos_norm_gold_val_json(self, val):
#         if type(val) == dict: return ','.join([F"{key}={self.mos_norm_gold_val_json(val.get(key))}" for key in val])
#         elif type(val) == list:
#             if sum([type(_) == dict for _ in val]) == 0: return ' '.join([self.mos_norm_gold_val_json(_) for _ in val])
#             else: return ';'.join([self.mos_norm_gold_val_json(_) for _ in val])
#         elif val in [None, 'None', '', '""']: return ''
#         elif 'ManagedElement' in val: return self.get_ldn_from_fdn(val)
#         elif re.match('(.*)\s\((.*)\)$', val): return re.match('(.*)\s\((.*)\)$', val).group(1)
#         else: return val.strip('"')
#
#     def mos_norm_gold_val(self, gs_val):
#         if pd.isnull(gs_val) or not (gs_val.startswith('[') or gs_val.startswith('{')) or (gs_val == ''): return self.mos_norm_gold_val_json(gs_val)
#         else:
#             try: json_gold_val = json.loads(gs_val)
#             except:
#                 self.log.info('Not Able to Convert to JSON. Please check value', gs_val)
#                 json_gold_val = {'XXXXXX': 'CHECK GS SHEET'}
#             return self.mos_norm_gold_val_json(json_gold_val)
#
#     @staticmethod
#     def get_moc_mocid_moidval_from_fdn(mo_fdn):
#         moc = re.search(r'.*,(.*)=.*', mo_fdn).group(1)
#         mo_id_val = re.search(r'.*=(.*)$', mo_fdn).group(1)
#         return moc, moc[0].lower() + moc[1:] + 'Id', mo_id_val
#
#     # @staticmethod
#     # def get_ldn_from_fdn(fdn_mo):
#     #     return re.search(r'.*ManagedElement=\w+,(.*)', fdn_mo).group(1) if 'ManagedElement=' in fdn_mo else fdn_mo
#
#     @staticmethod
#     def get_ldn_from_fdn(fdn_mo): return re.search(r'.*ManagedElement=[^,]*,(.*)', fdn_mo).group(1) if 'ManagedElement=' in fdn_mo else fdn_mo
#
#     def cmedit_norm_gold_val(self, gs_val, dnprefix=''):
#         if pd.isnull(gs_val) or not (gs_val.startswith('[') or gs_val.startswith('{')) or gs_val == '':
#             return self.cmedit_norm_gold_val_json(gs_val, dnprefix)
#         else:
#             try: gs_val = json.loads(gs_val)
#             except:
#                 self.log.info('Not Able to Convert to JSON. Please check value', gs_val)
#                 gs_val = {'Error': 'CHECK GS SHEET'}
#             return self.cmedit_norm_gold_val_json(gs_val, dnprefix)
#
#     def cmedit_norm_gold_val_json(self, gs_val, dnprefix=''):
#         """
#         Special Character --- *()[]\+<>= and space
#         Special characters are any characters other than the supported characters.
#         These characters must be wrapped in quotes to be accepted in the scope name or attribute value part of the command.
#         *()[]\+<>= and space - Special C
#         """
#         if type(gs_val) == list and len(gs_val) == 0: return "[]"
#         elif type(gs_val) == dict and len(gs_val) == 0: return "{}"
#         elif type(gs_val) not in [dict, list] and len(gs_val) == 0: return '<empty>'
#         elif gs_val in ['null', 'empty']: return F'<{gs_val}>'
#         elif type(gs_val) == dict: return '{' + ', '.join([F"{key}={self.cmedit_norm_gold_val_json(gs_val.get(key), dnprefix)}" for key in gs_val]) + '}'
#         elif type(gs_val) == list: return '[' + ', '.join([self.cmedit_norm_gold_val_json(_, dnprefix) for _ in gs_val]) + ']'
#         elif gs_val in [None, 'None', '']: return '<empty>'
#         elif len([_ for _ in ['{', '[', '('] if str(gs_val).startswith(_)]) > 0: return gs_val
#         elif re.match('(.*)\s\((.*)\)$', gs_val): return re.match('(.*)\s\((.*)\)$', gs_val).group(2)
#         elif re.match('(.*),(.*)=(.*)$', gs_val) and 'ManagedElement=' not in gs_val and len(dnprefix) > 0: return F'"{dnprefix},{gs_val}"'
#         elif re.match('(.*),(.*)=(.*)$', gs_val) and 'SubNetwork=' not in gs_val and 'ManagedElement=' in gs_val and len(dnprefix) > 0:
#             return '"' + dnprefix + re.match('.*ManagedElement=([^,]*),(.*)$', gs_val).group(2) + '"'
#         elif len([_ for _ in ['*', '(', ')', '[', ']', '\\', '+', '<', '>', '=', ' ', ',', ':'] if _ in str(gs_val)]) > 0: return F'"{gs_val}"'
#         else: return gs_val
#
#     def script_list_cli(self, x, script_type='cli'):
#         val = self.cmedit_norm_gold_val(x.InitialValue, re.search(r'(.*,ManagedElement=[^,=]*),.*', x.MO).group(1))
#         if script_type == 'cli':
#             return [
#                 F'set',
#                 F'FDN : {x.MO}',
#                 F'{x.Parameter} : {val}',
#                 F'',
#             ]
#         elif script_type == 'cmedit': return [F"cmedit set {x.MO} {x.Parameter}:{val}"]
#
#     def create_script_from_dict(self, mo_fdn, mo_dict, script_type):
#         script_list = []
#         if len(mo_fdn) == 0: return script_list
#         moc, moid, moidval = self.get_moc_mocid_moidval_from_fdn(mo_fdn)
#         dnprefix = re.search(r'(.*,ManagedElement=[^,=]*),.*', mo_fdn).group(1)
#         if moidval != mo_dict.get(moid):
#             self.log(F'ID Mismatch for MO {mo_fdn}')
#             self.log(F'{moc}--{moid}--{moidval}----{mo_dict.get(moid)}')
#         if script_type == 'mos':
#             mo_ldn = self.get_ldn_from_fdn(mo_fdn)
#             if len(mo_ldn) > 0:
#                 script_list.append(F'crn {mo_ldn}')
#                 for key in mo_dict:
#                     if str(key).lower() == str(moid).lower() or mo_dict[key] in [None, 'None', 'null', '', [], {}]: continue
#                     script_list.append(F'{key} {self.mos_norm_gold_val(mo_dict[key])}')
#                 script_list.extend(['end', ''])
#         elif script_type == 'cli':
#             script_list.extend([F'create', F'FDN : {mo_fdn}', F'{moid} : {moidval}'])
#             for key in mo_dict:
#                 if str(key).lower() == str(moid).lower() or mo_dict[key] in [None, 'None', 'null', '', [], {}]: continue
#                 script_list.append(F'{key} : {self.cmedit_norm_gold_val(mo_dict.get(key), dnprefix)}')
#             script_list.append('')
#         elif script_type == 'cmedit':
#             script_str = F'cmedit create {mo_fdn} {moid}={moidval};'
#             for key in mo_dict:
#                 if str(key).lower() == str(moid).lower() or mo_dict[key] in [None, 'None', 'null', '', [], {}]: continue
#                 script_str += F'{key}={self.cmedit_norm_gold_val(mo_dict.get(key), dnprefix)};'
#             script_list.append(script_str[:-1])
#         return script_list
#
#     def get_mocid_and_its_value_for_fdn(self, mo_fdn):
#         moc = re.search(r'.*,(.*)=.*', mo_fdn).group(1)
#         return {moc[0].lower() + moc[1:] + 'Id': re.search(r'.*=(.*)$', mo_fdn).group(1)}
#
#     def get_eutran_network_mos_dict_to_be_created(self, node):
#         s_dict = {}
#         df_new = self.usid.df_lte_crel.copy()
#         df_new = df_new.loc[((df_new.site == node) & (~df_new.flag) & (df_new.cr_flag))]
#         if len(df_new.index) == 0: return s_dict
#         site = self.usid.sites.get(F'site_{node}')
#         # EUtraNetwork, EUtranFrequency, EUtranFreqRelation
#         if site.enb_enw != '' and site.enb_enw not in site.mo_list:
#             s_dict[site.enb_enw] = self.get_mocid_and_its_value_for_fdn(site.enb_enw)
#         for row in self.usid.df_lte_freq.loc[((self.usid.df_lte_freq.site == node) & (~self.usid.df_lte_freq.flag))].itertuples():
#             s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
#             s_dict[row.fdn] |= {'arfcnValueEUtranDl': row.earfcn}
#         for row in self.usid.df_lte_rel.loc[((self.usid.df_lte_rel.site == node) & (~self.usid.df_lte_rel.flag) &
#                                              (self.usid.df_lte_rel.cr_flag))].itertuples():
#             s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
#             s_dict[row.fdn] |= {'cellReselectionPriority': '2', 'eutranFrequencyRef': F'{site.enb_enw},EUtranFrequency={row.freq}'}
#
#         # ExternalENodeBFunction, TermPointToENB, ExternalEUtranCellFDD, EUtranCellRelation
#         for nodeid in df_new.nodeid.unique():
#             if site.enodeb_id == nodeid:
#                 # for t_cell in df_new.loc[df_new.nodeid == nodeid].t_cell.unique():
#                 for row_c in df_new.loc[(df_new.nodeid == nodeid)].itertuples():
#                     s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
#                     s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'neighborCellRef': F'{site.enb},EUtranCellFDD={row_c.t_cell}'}
#             else:
#                 ext_mo_flag, ext_mo = True, F'{site.enb_enw},ExternalENodeBFunction=310410-{nodeid}'
#                 for mo in site.get_mos_with_parent_moc(parent=site.enb_enw, moc='ExternalENodeBFunction'):
#                     if site.get_mo_para(mo, 'eNBId') == nodeid:
#                         ext_mo = mo
#                         ext_mo_flag = False
#                         break
#                 if ext_mo_flag:
#                     s_dict[ext_mo] = self.get_mocid_and_its_value_for_fdn(ext_mo)
#                     s_dict[ext_mo] |= {'eNBId': nodeid, 'eNodeBPlmnId': '{"mcc": "310", "mnc": "410", "mncLength": "3"}',
#                                        'eSCellCapacityScaling': '100', 'mfbiSupport': 'true'}
#                 if len(site.get_mos_with_parent_moc(parent=ext_mo, moc='TermPointToENB')) == 0:
#                     tpt_ext_mo = F'{ext_mo},TermPointToENB=310410-{nodeid}'
#                     s_dict[tpt_ext_mo] = self.get_mocid_and_its_value_for_fdn(tpt_ext_mo)
#                     s_dict[tpt_ext_mo] |= {'administrativeState': '1 (UNLOCKED)', 'ipAddress': '0.0.0.0', 'ipv6Address': '::'}
#
#                 # ExternalEUtranCellFDD
#                 for row in df_new.loc[df_new.nodeid == nodeid].drop_duplicates().groupby([
#                     'site', 'nodeid', 'cellid', 'relid', 'pci', 'tac', 'freq'], sort=False, as_index=False).head(1).itertuples():
#                     ext_fdd_mo_flag, ext_fdd_mo = True, F'{ext_mo},ExternalEUtranCellFDD=310410-{nodeid}-{row.cellid}'
#                     for mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalEUtranCellFDD'):
#                         if site.get_mo_para(mo, 'localCellId') == row.cellid:
#                             ext_fdd_mo = mo
#                             ext_fdd_mo_flag = False
#                             break
#                     if ext_fdd_mo_flag:
#                         s_dict[ext_fdd_mo] = self.get_mocid_and_its_value_for_fdn(ext_fdd_mo)
#                         s_dict[ext_fdd_mo] |= {
#                             'activePlmnList': '[{"mcc": "310", "mnc": "410", "mncLength": "3"}, {"mcc": "313", "mnc": "100", "mncLength": "3"}]',
#                             'endcAllowedPlmnList': '{"mcc": "310", "mnc": "410", "mncLength": "3"}', 'noOfTxAntennas': '2',
#                             'eutranFrequencyRef': F'{site.enb_enw},EUtranFrequency={row.freq}', 'localCellId': F'{row.cellid}',
#                             'physicalLayerCellIdGroup': F'{int(row.pci) // 3}', 'physicalLayerSubCellId': F'{int(row.pci) % 3}', 'tac': F'{row.tac}'
#                         }
#                     for row_c in df_new.loc[(df_new.nodeid == nodeid) & (df_new.cellid == row.cellid)].itertuples():
#                         s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
#                         s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'neighborCellRef': ext_fdd_mo}
#         return s_dict
#
#     def get_gutran_network_mos_dict_to_be_created(self, node):
#         s_dict = {}
#         df_new = self.usid.df_lte_nr_crel.copy()
#         df_new = df_new.loc[(df_new.site == node) & (~df_new.flag)]
#         if len(df_new.index) == 0: return s_dict
#         site = self.usid.sites.get(F'site_{node}')
#         # GUtraNetwork, ExternalGNodeBFunction, ExternalGUtranCell, TermPointToGNB, GUtranSyncSignalFrequency, GUtranFreqRelation, GUtranCellRelation
#         if site.enb_gnw not in site.mo_list:
#             s_dict[site.enb_gnw] = self.get_mocid_and_its_value_for_fdn(site.enb_gnw)
#         for row in self.usid.df_lte_nr_freq.loc[(self.usid.df_lte_nr_freq.site == node) & (~self.usid.df_lte_nr_freq.flag)].itertuples():
#             s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
#             s_dict[row.fdn] |= {'arfcn': row.ssbfreq, 'smtcDuration': row.duration, 'smtcOffset': row.offset, 'smtcPeriodicity': row.periodicity,
#                                 'smtcScs': row.scc, 'band': F'["{self.usid.param_dict["ssbfreq"][row.ssbfreq]["band"]}"]'}
#
#         for row in self.usid.df_lte_nr_rel.loc[(self.usid.df_lte_nr_rel.site == node) & (~self.usid.df_lte_nr_rel.flag)].itertuples():
#             s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
#             s_dict[row.fdn] |= {
#                 'cellReselectionPriority': '7',
#                 'gUtranSyncSignalFrequencyRef': F'{site.enb_gnw},GUtranSyncSignalFrequency={row.freq}',
#                 'allowedPlmnList': '[{"mcc": "310", "mnc": "410", "mncLength": "3"}, {"mcc": "313", "mnc": "100", "mncLength": "3"}]',
#                 'anrMeasOn': 'true',
#                 'connectedModeMobilityPrio': '6',
#                 # 'endcB1MeasPriority': '-1',
#                 'qOffsetFreq': '0',
#                 'qQualMin': '-30',
#                 'qRxLevMin': '-104',
#                 'threshXHigh': '4',
#                 'threshXHighQ': '0',
#                 'threshXLow': '0',
#                 'threshXLowQ': '0',
#                 'timeToTriggerB1Override': '-1000',
#                 'triggerQuantityGUtraOverride': '0',
#             }
#         # ExternalGNodeBFunction, ExternalGUtranCell, TermPointToGNB,  GUtranFreqRelation, GUtranCellRelation
#         for row_ext_gnb in df_new.groupby(['nodeid'], sort=False, as_index=False).head(1).itertuples():
#             ext_mo_flag, ext_mo = True, F'{site.enb_gnw},ExternalGNodeBFunction={row_ext_gnb.ext_node}'
#             for mo in site.get_mos_with_parent_moc(parent=site.enb_gnw, moc='ExternalGNodeBFunction'):
#                 if site.get_mo_para(mo, 'gNodeBId') == row_ext_gnb.nodeid:
#                     ext_mo = mo
#                     ext_mo_flag = False
#                     break
#             if ext_mo_flag:
#                 s_dict[ext_mo] = self.get_mocid_and_its_value_for_fdn(ext_mo)
#                 s_dict[ext_mo] |= {'gNodeBId': row_ext_gnb.nodeid, 'gNodeBPlmnId': '{"mcc": "310", "mnc": "410", "mncLength": "3"}',
#                                    'gNodeBIdLength': row_ext_gnb.nodeid_len}
#             if len(site.get_mos_with_parent_moc(parent=ext_mo, moc='TermPointToGNB')) == 0:
#                 tpt_ext_mo = F'{ext_mo},TermPointToGNB={row_ext_gnb.ext_node}'
#                 s_dict[tpt_ext_mo] = self.get_mocid_and_its_value_for_fdn(tpt_ext_mo)
#                 s_dict[tpt_ext_mo] |= {'administrativeState': '1 (UNLOCKED)', 'ipAddress': '0.0.0.0', 'upIpAddress': '::'}
#
#             # ExternalEUtranCellFDD
#             for row in df_new.loc[df_new.nodeid == row_ext_gnb.nodeid].drop_duplicates().groupby(['site', 't_site', 't_cell'],
#                                                                                                  sort=False, as_index=False).head(1).itertuples():
#                 ext_fdd_mo_flag, ext_fdd_mo = True, F'{ext_mo},ExternalGUtranCell=310410-000000{row.nodeid}-{row.cellid}'
#                 for mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalGUtranCell'):
#                     if site.get_mo_para(mo, 'localCellId') == row.cellid:
#                         ext_fdd_mo = mo
#                         ext_fdd_mo_flag = False
#                         break
#                 if ext_fdd_mo_flag:
#                     s_dict[ext_fdd_mo] = self.get_mocid_and_its_value_for_fdn(ext_fdd_mo)
#                     s_dict[ext_fdd_mo] |= {
#                         'localCellId': F'{row.cellid}',
#                         'physicalLayerCellIdGroup': F'{int(row.pci) // 3}', 'physicalLayerSubCellId': F'{int(row.pci) % 3}',
#                         'gUtranSyncSignalFrequencyRef': F'{site.enb_gnw},GUtranSyncSignalFrequency={row.freq}',
#                         'plmnIdList': '[{"mcc": "310", "mnc": "410", "mncLength": "3"}, {"mcc": "313", "mnc": "100", "mncLength": "3"}]',
#                         'isRemoveAllowed': 'false',
#                         'nRTAC': '-1',
#                     }
#                 for row_c in df_new.loc[(df_new.nodeid == row.nodeid) & (df_new.cellid == row.cellid)].itertuples():
#                     s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
#                     s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'neighborCellRef': ext_fdd_mo}
#         return s_dict
#
#     def get_nr_network_mos_dict_to_be_created(self, node):
#         s_dict = {}
#         df_new = self.usid.df_nr_crel.copy()
#         df_new = df_new.loc[((df_new.site == node) & (~df_new.flag))]
#
#         if len(df_new.index) == 0: return s_dict
#         site = self.usid.sites.get(F'site_{node}')
#         # NRFrequency, NRFreqRelation, NRFreqRelation
#         if site.gnb_nnw != '' and site.gnb_nnw not in site.mo_list:
#             s_dict[site.gnb_nnw] = self.get_mocid_and_its_value_for_fdn(site.gnb_nnw)
#         for row in self.usid.df_nr_freq.loc[((self.usid.df_nr_freq.site == node) & (~self.usid.df_nr_freq.flag))].itertuples():
#             s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
#             s_dict[row.fdn] |= {'arfcnValueNRDl': row.ssbfreq, 'smtcScs': row.scc, 'smtcDuration': row.duration, 'smtcOffset': row.offset,
#                                 'smtcPeriodicity': row.periodicity}
#             # # McpcPSCellNrFreqRelProfile, UeMCNrFreqRelProfile, McpcPCellNrFreqRelProfile, TrStSaNrFreqRelProfile
#             # _, _, mos_list = self.get_nr_freq_rel_id_n_profile_mos(row)
#             # for moc in mos_list:
#             #     mos_ldn_dict[moc[1]] = F'GNBCUCPFunction=1,{moc[0]}=1,{moc[1]}={row.relid}'
#             #     if mos_ldn_dict[moc[1]] in mo_list: pass
#             #     if self.no_eq_change_with_dcgk_flag and len(self.site.get_mos_w_end_str(mos_ldn_dict[moc[1]])) > 0:
#             #         mo_list += [mos_ldn_dict[moc[1]]]
#             #     else:
#             #         mo_list += [mos_ldn_dict[moc[1]]]
#             #         tmp_dict = self.get_mo_dict_from_moc_node_fdn_moid(moc[1], None, None, row.relid)
#             #         tmp_dict |= {self.get_moc_id(moc[1]): row.relid}
#             #         if len(moc) == 3:
#             #             tmp_dict[moc[2]] = self.get_mo_dict_from_moc_node_fdn_moid(moc[2], None, None, 'Base')
#             #             tmp_dict[moc[2]] |= {'attributes': {'xc:operation': 'update'}}
#             #             tmp_dict |= self.update_rel_cug_profile(row.freqband, moc[2], tmp_dict)
#             #         mo_dict = copy.deepcopy(me_dict)
#             #         mo_dict['GNBCUCPFunction'][moc[0]] = {self.get_moc_id(moc[0]): '1', moc[1]: tmp_dict}
#             #         self.mo_dict[mos_ldn_dict[moc[1]]] = copy.deepcopy(mo_dict)
#
#         for row in self.usid.df_nr_rel.loc[((self.usid.df_nr_rel.site == node) & (~self.usid.df_nr_rel.flag))].itertuples():
#             s_dict[row.fdn] = self.get_mocid_and_its_value_for_fdn(row.fdn)
#             s_dict[row.fdn] |= {'cellReselectionPriority': '7', 'nRFrequencyRef': F'{site.gnb_nnw},NRFrequency={row.freq}'}
#
#         # ExternalENodeBFunction, TermPointToENB, ExternalEUtranCellFDD, EUtranCellRelation
#         for nodeid in df_new.nodeid.unique():
#             if site.gnodeb_id == nodeid:
#                 for row_c in df_new.loc[(df_new.nodeid == nodeid)].itertuples():
#                     s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
#                     s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'nRCellRef': F'{site.gnb_cucp},NRCellCU={row_c.t_cell}',
#                                           'nRFreqRelationRef': F'{site.gnb_cucp},NRCellCU={row_c.cell},NRFreqRelation={row_c.relid}'}
#             else:
#                 row_ext = df_new.loc[(df_new.nodeid == nodeid)].head(1).iloc[0]
#                 ext_mo_flag, ext_mo = True, F'{site.gnb_nnw},ExternalGNBCUCPFunction={row_ext.get("t_site")}'
#                 for mo in site.get_mos_with_parent_moc(parent=site.gnb_nnw, moc='ExternalGNBCUCPFunction'):
#                     if site.get_mo_para(mo, 'gNBId') == nodeid:
#                         ext_mo_flag, ext_mo = False, mo
#                         break
#                 if ext_mo_flag:
#                     s_dict[ext_mo] = self.get_mocid_and_its_value_for_fdn(ext_mo)
#                     s_dict[ext_mo] |= {'gNBId': row_ext.get("nodeid"), 'gNBIdLength': row_ext.get("nodeid_len"),
#                                        'pLMNId': '{"mcc": "310", "mnc": "410"}'}
#                 # ExternalNRCellCU
#                 for row in df_new.loc[df_new.nodeid == nodeid].groupby([
#                         'site', 'nodeid', 'cellid', 'relid', 'pci', 'tac', 'freq'], sort=False, as_index=False).head(1).itertuples():
#                     ext_fdd_mo_flag, ext_fdd_mo = True, F'{ext_mo},ExternalNRCellCU={row.t_cell}'
#                     for mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalNRCellCU'):
#                         if site.get_mo_para(mo, 'cellLocalId') == row.cellid:
#                             ext_fdd_mo_flag, ext_fdd_mo = False, mo
#                             break
#                     if ext_fdd_mo_flag:
#                         s_dict[ext_fdd_mo] = self.get_mocid_and_its_value_for_fdn(ext_fdd_mo)
#                         s_dict[ext_fdd_mo] |= {'cellLocalId': row.cellid, 'nRPCI': row.pci, 'nRTAC': row.tac,
#                                                'plmnIdList': '[{"mcc": "310", "mnc": "410"}, {"mcc": "313", "mnc": "100"}]',
#                                                'nRFrequencyRef': F'{site.gnb_nnw},NRFrequency={row.freq}'}
#                     for row_c in df_new.loc[(df_new.nodeid == nodeid) & (df_new.cellid == row.cellid)].itertuples():
#                         s_dict[row_c.fdn] = self.get_mocid_and_its_value_for_fdn(row_c.fdn)
#                         s_dict[row_c.fdn] |= {'isRemoveAllowed': 'false', 'nRCellRef': ext_fdd_mo,
#                                               'nRFreqRelationRef': F'{site.gnb_cucp},NRCellCU={row_c.cell},NRFreqRelation={row_c.relid}'}
#         return s_dict
#
#     def get_nr_freq_rel_id_n_profile_mos(self, freq):
#         """ :rtype: set """
#         freqband = str(freq.freqband).upper()
#         freq_id = F'{freq.ssbfrequency}-{freq.ssbsubcarrierspacing}'
#         freq_mo_id = F'{freq.ssbfrequency}-{freq.ssbsubcarrierspacing}-{freq.ssbperiodicity}-{freq.ssboffset}-{freq.ssbduration}'
#         mos_list = [
#             ('Mcpc', 'McpcPCellNrFreqRelProfile', 'McpcPCellNrFreqRelProfileUeCfg'),
#             ('Mcpc', 'McpcPSCellNrFreqRelProfile', 'McpcPSCellNrFreqRelProfileUeCfg'),
#             ('UeMC', 'UeMCNrFreqRelProfile', 'UeMCNrFreqRelProfileUeCfg'),
#         ]
#         if freqband in ["N260", "N261", "N258"]: mos_list = []
#         elif freqband in ['N077']: mos_list += [('TrafficSteering', 'TrStSaNrFreqRelProfile', 'TrStSaNrFreqRelProfileUeCfg')]
#         return freq_id, freq_mo_id, mos_list
