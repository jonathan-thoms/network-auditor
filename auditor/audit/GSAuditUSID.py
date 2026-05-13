import sys
import copy
import os
import json
import pandas as pd
import numpy as np
from common_func.dcgkextract import dcgkextract
from auditor.audit.GSAuditDCGK import GSAuditDCGK
from auditor.audit.GSAuditLogic import GSAuditLogic

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mScripter.settings")
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
from auditor.models import LTEearfcnBandBWLayer, LTECAPair, NRBand
# from auditor.models import UMTSBand
from django.conf import settings

bb_type_dict = {
    '5216': 'G2', '6630': 'G2',
    '6648': 'G3', '6651': 'G3', '6655': 'G3',
    '6507': 'G3', '6355': 'G3', '6339': 'G3',
    '6672': 'G4',
}


class GSAuditUSID:
    def __init__(self, software_log, job, custom_log, outdir):
        self.site_id = job.sites
        self.sw_ver = job.version
        self.revision = self.sw_ver
        self.market = job.market
        self.log = custom_log.log
        self.outdir = outdir

        self.dlonly = [_.strip() for _ in job.dlonly.split(',') if _ != '']
        # self.umts_femto = [_.strip() for _ in job.femto.split(',') if _ != '']

        self.log.info(F'Started running job for AT&T GS Audit Site : {self.site_id}')
        self.log.info('')
        self.log.info(F'Site: {self.site_id}')
        self.log.info(F'SW Version: {self.sw_ver}')
        self.log.info(F'Market: {self.market}')
        self.log.info(F'DlOnly: {self.dlonly}')
        # self.log.info(F'Fento: {self.umts_femto}')
        self.log.info('')

        # DCGK Log file Extract and Store in Dict
        self.sites = {}
        dcgk_extract = dcgkextract(inzip=software_log)
        for siteid in dcgk_extract.merged_dict.keys():
            self.sites['site_' + str(siteid)] = GSAuditDCGK(siteid, dcgk_extract.merged_dict.get(siteid, {}))
        if len(self.sites) == 0:
            self.log.exception("message")
            self.log.info(F'Job completed for AT&T GS Audit Site no Log Files Found, Status: Failed!!!')
            assert False, F'!!! Log Files not Found !!! '
        if F'site_{self.site_id}' not in self.sites.keys():
            dcgk_list = [', '.join(_.split('_')[-1]) for _ in self.sites.keys()][-1]
            self.log.exception("message")
            self.log.info(F'Avialable DCGK Files {dcgk_list}!!!!')
            self.log.info(F'Job completed for AT&T GS Audit, {self.site_id} not found in Log DCGK Files, Status: Failed!!!')
            assert False, F''

        # GS Parameters Dict
        self.embms = False
        self.param_dict = {
            'para': {self.market: True, F'market_{self.market}': True, F'{self.sw_ver}': True, 'EMBMS': False},
            'sites': {self.sites.get(key).siteid: self.get_site_dict(self.sites.get(key)) for key in self.sites},
            'earfcn': {},
            # 'uarfcn': {},
            'ssbfreq': {},
            'lte_ca_set': []
        }
        if self.embms:
            self.param_dict['para']['EMBMS'] = copy.deepcopy(self.embms)
        del self.embms

        self.logic = GSAuditLogic(op_dict=self.param_dict)
        # Mandatory Data
        self.earfcn_dict = {}
        self.nr_band = {}
        # self.utran_band_dict = {}
       
        self.df_nr_cells = pd.DataFrame([], columns=[])
        self.df_lte_cells = pd.DataFrame([], columns=[])
        
        self.df_lte_freq = pd.DataFrame([], columns=['site', 'freq', 'earfcn', 'fdn', 'flag'])
        self.df_lte_rel = pd.DataFrame([], columns=['site', 'cell', 'relid', 'earfcn', 'fdn', 'flag', 'freq', 'cr_flag'])
        self.df_lte_crel = pd.DataFrame([], columns=['site', 'cell', 'relid', 'crelid', 'nodeid', 'cellid', 'pci', 'tac', 't_cell', 'fdn',
                                                     'flag', 'earfcn', 't_site', 'cr_flag', 'freq'])
        # self.df_lte_umts_freq = pd.DataFrame([], columns=['site', 'freq', 'arfcn', 'fdn', 'flag'])
        # self.df_lte_umts_rel = pd.DataFrame([], columns=['site', 'cell', 'relid', 'arfcn', 'fdn', 'flag', 'freq'])

        self.df_nr_freq = pd.DataFrame([], columns=['site', 'arfcndl', 'ssbfreq', 'scc', 'duration', 'offset', 'periodicity', 'fdn', 'flag'])
        self.df_nr_rel = pd.DataFrame([], columns=['site', 'cell', 'relid', 'ssbfreq', 'fdn', 'arfcndl', 'flag'])
        self.df_nr_crel = pd.DataFrame([], columns=['site', 'cell', 'relid', 'crelid', 'nodeid', 'nodeid_len', 'cellid', 'pci', 'tac',
                                                    't_cell', 'fdn', 'flag', 'ssbfreq', 't_site'])
        
        self.df_lte_nr_freq = pd.DataFrame([], columns=['site', 'freq', 'fdn', 'flag', 'ssbfreq', 'scc', 'duration', 'offset', 'periodicity'])
        self.df_lte_nr_rel = pd.DataFrame([], columns=['site', 'cell', 'relid', 'fdn', 'flag', 'freq', 'ssbfreq', 'scc', 'duration',
                                                       'offset', 'periodicity'])
        self.df_lte_nr_crel = pd.DataFrame([], columns=['site', 'cell', 'relid', 'crelid', 'nodeid', 'nodeid_len', 'cellid', 'pci', 'tac',
                                                        't_cell', 'fdn', 'flag', 'ssbfreq', 't_site'])
        
        self.df_gs = pd.DataFrame([], columns=[])
        self.df_script_type = pd.DataFrame([], columns=['MO', 'MOC', 'Parameter', 'script_type'])
        self.df_report = pd.DataFrame([], columns=['OnAir', 'Site', 'MO',  'Parameter', 'CurrentValue', 'GSValue', 'InitialValue', 'Permission',
                                                   'Suffix', 'flag', 'Type', 'MOC'])

        self.initialize()
        
    def initialize(self):
        self.get_850_lb_list()
        self.set_db_vars()
        self.initialize_lte_nr_cell_data()
        self.get_usid_nrcells_ltecells_dataframes()
        
        self.get_nr_nr_relations_data()
        self.get_lte_lte_relations_data()
        # self.get_lte_umts_relations_data()
        self.get_lte_nr_relations_data()

        self.update_lte_carrier_agg()
        self.update_lte_catm_cells()
        self.update_lte_cellsleep_mimosleep()
        self.update_lte_anchor_flag()
        
        self.update_site_usid_params_from_site_cell()
        self.update_multiple_nr_bands_tdd_fdd()
        self.update_relations_dict_with_site_data()
        self.update_nh_mocn_gw_nr_dc_mn_nr_dc_sn()
        self.get_att_ericsson_enb_gnb_gold_standard_and_suffix_from_excell()

        # del self.utran_band_dict
        del self.earfcndl_lb_850

    def update_nh_mocn_gw_nr_dc_mn_nr_dc_sn(self):
        """
        NH_MOCN_GW
        Site has ENodeBFunction=1,EUtranCellFDD,EUtranFreqRelation,eUtranFreqRelationId=b48(55240-56739)
        NR-DC_Mn
        MgNB: FeatureState=CXC4012582 featureState=1 and
        GNBCUCPFunction=1,NrdcControl=1,NrdcMnCellProfile=1,NrdcMnCellProfileUeCfg=Base  nrdcEnabled=TRUE and SA
        NR-DC_Sn
        SgNB: FeatureState=CXC4012582 featureState=1 and non_SA and NR_HB
        eNodeB with eutranfreqrelation 5330 ---- Removed
        eNB_eFreqRel_5330 ---- Removed
        eNodeB with (B14 or B30) eutranfreqrelation ---> eNodeB_with_B14_B30_eutranfreqrelation ---- Added
        :return:
        """
        for node in self.param_dict.get('sites'):
            if len(self.df_lte_rel.loc[((self.df_lte_rel.site == node) & (self.df_lte_rel.earfcn >= '55240') &
                                        (self.df_lte_rel.earfcn <= '56739'))].index) > 0:
                self.param_dict['sites'][node]['para']['NH_MOCN_GW'] = True
            # if len(self.df_lte_rel.loc[((self.df_lte_rel.site == node) & (self.df_lte_rel.earfcn == '5330'))].index) > 0:
            #     self.param_dict['sites'][node]['para']['eNB_eFreqRel_5330'] = True
            all_bands__for_enb_rel = set([self.param_dict.get('earfcn').get(_, {}).get('band', '') for _ in
                                 self.df_lte_rel.loc[(self.df_lte_rel.site == node), 'earfcn']])
            if '14' in all_bands__for_enb_rel or '30' in all_bands__for_enb_rel:
                self.param_dict['sites'][node]['para']['eNodeB_with_B14_B30_eutranfreqrelation'] = True
            self.param_dict['sites'][node]['para']['NR-DC_Mn'] = (self.param_dict['sites'][node]['para']['NR-DC_Mn'] and
                                                                  self.param_dict['sites'][node]['para'].get('SA', False))
            self.param_dict['sites'][node]['para']['NR-DC_Sn'] = (self.param_dict['sites'][node]['para']['NR-DC_Sn'] and
                                                                  (not self.param_dict['sites'][node]['para'].get('SA', True)) and
                                                                  self.param_dict['sites'][node]['para'].get('NR_HB', False))

    def get_850_lb_list(self):
        # Special Setting for 850 as LB when 700 band doesnot exit on USID
        flag_700, earfcndl_lb_850 = False, []
        if self.market in ['NE']:
            for key in self.sites:
                site = self.sites.get(key)
                for cell_mo in site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellFDD'):
                    if site.get_mo_data(cell_mo).get('freqBand', '') in ['12', '17']:
                        flag_700 = True
                    elif site.get_mo_data(cell_mo).get('freqBand', '') in ['5']:
                        earfcndl_lb_850.append(site.get_mo_data(cell_mo).get('earfcndl', ''))
        if flag_700: earfcndl_lb_850 = []
        self.earfcndl_lb_850 = copy.deepcopy(earfcndl_lb_850)

    @staticmethod
    def get_feature_status_of_site(*, site_dict, feature_name) -> bool:
        feature = site_dict.get_mos_with_moc_moid('FeatureState', feature_name)
        return site_dict.get_mo_data(feature[0]).get('featureState', '')[0] == '1' if len(feature) > 0 else False

    def get_site_dict(self, site):
        ulcomp = site.get_mo_data(site.enb).get('eranUlCompVlanPortRef', None)
        idle = site.get_mo_data(site.enb).get('eranVlanPortRef', None)
        node_dict = {}
        node_dict['cells'] = {}
        # Node level parameters
        node_dict['para'] = {
            F'siteid': site.siteid,
            F'{site.audit_type_str}': True,
            F'{self.sw_ver}': True,
            F'{self.market}': True,
            F'market_{self.market}': True,
            F'BBType': '',
            F'G2': False,
            F'G3': False,
            F'G4': False,
            F'IPv4': False,
            F'IPv6': True,
            F'eNB': len(site.enb) > 0,
            F'gNB': len(site.gnb) > 0,
            F'MMBB': len(site.enb) > 0 and len(site.gnb) > 0,
            F'UlCoMP': True if ulcomp not in [None, '', 'None'] and len(ulcomp) > 0 else False,
            F'IDLe': True if idle not in [None, '', 'None'] and len(idle) > 0 else False,
            F'AMF': False,
            F'hicap': False,
            F'FirstNetHiCap': False,
            F'GPS': False,
            F'Inter-PLMN_HO': False,
            F'PSHO': self.get_feature_status_of_site(site_dict=site, feature_name='CXC4011011'),
            F'AASFDD': self.get_feature_status_of_site(site_dict=site, feature_name='CXC4012254'),
            F'InterENBCA': self.get_feature_status_of_site(site_dict=site, feature_name='CXC4011983'),
            F'NRULCAHB': self.get_feature_status_of_site(site_dict=site, feature_name='CXC4012376'),
            
            F'mRBS': False,
            F'MSMM': False,
            F'MultiCabinet': False,
            F'noOfXMU': 0,
            F'noOfCabinet': 0,
            F'Radio_2203': False,
            F'AIR_1641': False,
            F'DaylightSavingMarket': site.siteid[:2].upper() not in ['AZ', 'HI'],
            F'NGRDS': False,  # ToDO Need to add logic for same Pending
            # F'NH_MOCN_GW': False, # defined on method update_nh_mocn_gw
            F'NR-DC_Mn': (self.get_feature_status_of_site(site_dict=site, feature_name='CXC4012582') and
                          len(site.gnb_cucp) > 0 and
                          site.get_mo_data(F'{site.gnb_cucp},NrdcControl=1,NrdcMnCellProfile=1,'
                                           F'NrdcMnCellProfileUeCfg=Base').get('nrdcEnabled', '') == 'true'),
            F'NR-DC_Sn': self.get_feature_status_of_site(site_dict=site, feature_name='CXC4012582'),
        }

        equipment_str = 'AuxPlugInUnit' if site.equipment_type != 'BB' else 'FieldReplaceableUnit'
        for mo in site.get_mos_with_moc(moc=equipment_str):
            prod_name = site.get_mo_data(mo).get('productData', {}).get('productName', [])
            if site.get_mo_data(mo).get('isSharedWithExternalMe') == 'true': node_dict['para']['MSMM'] = True
            # BB Type
            if len([_ for _ in bb_type_dict.keys() if _ in prod_name]) == 1:
                node_dict['para']['BBType'] = [_ for _ in bb_type_dict.keys() if _ in prod_name][0]

            if '2203' in prod_name: node_dict['para']['Radio_2203'] = True
            if '1641' in prod_name: node_dict['para']['AIR_1641'] = True
            if 'mrru' in prod_name: node_dict['para']['mRBS'] = True
            if 'R503' in prod_name: node_dict['para']['noOfXMU'] = node_dict['para']['noOfXMU'] + 1
            if len([_ for _ in ['RD2272', 'RD2274', 'RD4459', 'RD4455'] if _ in prod_name]) > 0: node_dict['NGRDS'] = False
        if len(node_dict['para']['BBType']) > 0:
            node_dict['para'][bb_type_dict.get(node_dict['para']['BBType'], 'G3')] = True
        else:
            self.log.info(F'BB Type for {site.siteid} not defined on GS Audit tool and need to be added!!!')
            node_dict['para']['G3'] = True
        # MultiCabinet
        node_dict['para']['noOfCabinet'] = len(site.get_mos_with_moc(moc='Cabinet'))
        if node_dict['para']['noOfCabinet'] > 1:
            node_dict['para']['MultiCabinet'] = True
        elif node_dict['para']['BBType'] in ['5216'] and node_dict['para']['noOfXMU'] > 1:
            node_dict['para']['MultiCabinet'] = True
        if node_dict['para']['BBType'] in ['6630', '6648', '6651', '6672'] and node_dict['para']['noOfXMU'] > 0:
            node_dict['para']['MultiCabinet'] = True
        # AMF for NR_SA, FirstNetHiCap, hicap, GSP, No of LTE Cells
        node_dict['para']['AMF'] = len(site.get_mos_with_parent_moc(parent=site.gnb_cucp, moc='TermPointToAmf')) > 0
        # AMF for NR_SA
        for mo in site.get_mos_with_parent_moc(parent=F'{site.enb},PtmFunction=1,PtmCellProfile=1', moc='PtmResOpUseConfig'):
            if site.get_mo_data(mo).get('resMsrUsageThreshold', 'aa') == '5':
                node_dict['para']['FirstNetHiCap'] = True
                break
        # hicap
        for mo in site.get_mos_with_moc_moid('QciProfilePredefined', 'qci8'):
            if ',EnodebFunction=' in mo and site.get_mo_data(mo).get('schedulingAlgorithm', 'aa')[0] == '0':
                node_dict['para']['hicap'] = True
                break
        # GPS, PTP, PTP_FREQ, PTP_TIME for Site
        for mo in site.get_mos_with_moc(moc='RadioEquipmentClockReference'):
            if site.get_mo_data(mo).get('syncRefType', 'aa')[0] == '7': node_dict['para']['GPS'] = True
            elif 'PTP' in site.get_mo_data(mo).get('syncRefType', 'aa'): node_dict['para']['PTP'] = True
        for mo in site.get_mos_with_moc(moc='BoundaryOrdinaryClock'):
            if site.get_mo_data(mo).get('domainNumber', 'aa') == '0': node_dict['para']['PTP_FREQ'] = True
            elif site.get_mo_data(mo).get('domainNumber', 'aa') == '44': node_dict['para']['PTP_TIME'] = True
        # No of FDD & TDD LTE Cells
        tmp_val = len(site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellFDD') +
                      site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellTDD'))
        node_dict['para']['s__=1cells'] = tmp_val == 1
        for val in [1, 3, 6, 9, 12, 18]:
            node_dict['para'][F's__>{val}cells'] = tmp_val > val
            node_dict['para'][F's__<={val}cells'] = tmp_val <= val

        # USID Para EMBMS
        if (not self.embms) and (len(site.enb) > 0):
            if len(site.get_mos_with_parent_moc(parent=site.enb, moc='MbsfnArea')) > 0: self.embms = True
            if len(site.enb) > 0 and len([_ for _ in ['CXC4011365', 'CXC4011555', 'CXC4011558', 'CXC4011618', 'CXC4012012'] if
                                          self.get_feature_status_of_site(site_dict=site, feature_name=_)]) == 5: self.embms = True
        return copy.deepcopy(node_dict)
    
    def initialize_lte_nr_cell_data(self):
        # Special Setting for 850 as LB when 700 band doesnot exit on USID
        flag_700, earfcndl_850 = False, []
        if self.market in ['NE']:
            for key in self.sites:
                site = self.sites.get(key)
                for cell_mo in site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellFDD'):
                    if site.get_mo_data(cell_mo).get('freqBand', '') in ['12', '17']: flag_700 = True
                    elif site.get_mo_data(cell_mo).get('freqBand', '') in ['5']:
                        earfcndl_850.append(site.get_mo_data(cell_mo).get('earfcndl', ''))
        if flag_700 is True: earfcndl_850 = []
        del flag_700
        
        for key in self.sites:
            site = self.sites.get(key)
            cell_dict = {}
            # NRCellDU
            cell_type = 'NR'
            for nr_cell_mo in site.get_mos_with_parent_moc(parent=site.gnb, moc='NRCellDU'):
                data = site.get_mo_data(nr_cell_mo)
                cellid = data.get('cellLocalId')
                cell = nr_cell_mo.split('=')[-1]
                sa_flag = False
                if self.param_dict['sites'][site.siteid]['para']['AMF']:
                    for nr_cell_cu_mo in site.get_mos_with_parent_moc(parent=site.gnb_cucp, moc='NRCellCU'):
                        if cellid == site.get_mo_data(nr_cell_cu_mo).get('cellLocalId'):
                            sa_flag = 1052688 <= int(data.get('nRTAC')) <= 3167231
                            break
                        # if data.get('secondaryCellOnly') == 'false' and cellid == site.get_mo_data(nr_cell_cu_mo).get('cellLocalId'):
                            # sa_flag = (len(site.get_mos_with_parent_moc(parent=nr_cell_cu_mo, moc='EUtranFreqRelation')) > 0)
                            # break
                vonr_flag = self.get_feature_status_of_site(site_dict=site, feature_name='CXC4012592')
                if vonr_flag:
                    vonr_flag = False
                    for nr_cell_cu_mo in site.get_mos_with_parent_moc(parent=site.gnb_cucp, moc='NRCellCU'):
                        if cellid == site.get_mo_data(nr_cell_cu_mo).get('cellLocalId'):
                            sec_mo = site.get_first_mo_from_ref_parameter(site.get_mo_data(nr_cell_cu_mo).get('mcfbCellProfileRef'))
                            for rfb in site.get_mos_with_parent_moc(parent=sec_mo, moc='McfbCellProfileUeCfg'):
                                if site.get_mo_data(rfb).get('epsFallbackOperation', '000')[0] == '1':
                                    vonr_flag = True
                                    break
                            break

                sec_name = cell.split('_')
                sec_name = sec_name[2] if sec_name[1].upper not in ['N260', 'N261', 'N258'] else sec_name[1]
                sec_numb = [_ for _ in cell.split('_') if _.isdigit()]
                sec_numb = sec_numb[-1] if len(sec_numb) > 0 else '1'
                cascaded_flag, sector_data, sef_mo, fru_type = False, {}, None, []
                sec_mo = site.get_first_mo_from_ref_parameter(data.get('nRSectorCarrierRef'))
                if len(sec_mo) > 0:
                    sector_data = site.get_mo_data(sec_mo)
                    sef_mo = site.get_first_mo_from_ref_parameter(sector_data.get('sectorEquipmentFunctionRef'))
                    if sef_mo != '':
                        frus = []
                        for rfb in site.get_mo_data(sef_mo).get('rfBranchRef', []):
                            rfb = site.get_first_mo_from_ref_parameter(rfb)
                            if 'Transceiver' in rfb: frus.append(','.join(rfb.split(',')[:-1]))
                            elif site.get_first_mo_from_ref_parameter(site.get_mo_data(rfb).get('rfPortRef')):
                                frus.append(','.join(site.get_first_mo_from_ref_parameter(site.get_mo_data(rfb).get('rfPortRef')).split(',')[:-1]))
                        for fru in set(frus):
                            prod_type = site.get_mo_data(fru).get('productData', {}).get('productName', None)
                            if prod_type is not None and site.get_mo_data(fru).get('operationalState', '0')[0] == '1' and len(prod_type) > 0:
                                fru_type.append('_'.join(prod_type))
                all_frus = 'Radio_NA' if len(fru_type) == 0 else '___'.join(fru_type)
                fru_type = 'Radio_NA' if len(fru_type) == 0 else '_'.join(fru_type[0].split('_')[:2])
                ECDD_flag = 'commscope_cdd' in fru_type.lower()
                ssbfrequency = data.get('ssbFrequency') if data.get('ssbFrequencyAutoSelected') is None else data.get('ssbFrequencyAutoSelected')
                ssbsubcarrierspacing = data.get('ssbSubCarrierSpacing')
                ssboffset = data.get('ssbOffset') if data.get('ssbOffsetAutoSelected') is None else data.get('ssbOffsetAutoSelected')
                ssbduration = data.get('ssbDuration') if data.get('ssbDurationAutoSelected') is None else data.get('ssbDurationAutoSelected')
                ssbperiodicity = data.get('ssbPeriodicity')
                bw = sector_data.get('bSChannelBwDL', '0')
                earfcndl = sector_data.get('arfcnDL', '0')
                OnAir = data.get('cellReservedForOperator', '0')[0] == '1'
                nr_band_update_dict = {'arfcndl': earfcndl, 'bschannelbwdl': bw, 'ssbfrequency': ssbfrequency, 'ssboffset': ssboffset,
                                       'ssbduration': ssbduration, 'ssbperiodicity': ssbperiodicity, 'ssbsubcarrierspacing': ssbsubcarrierspacing}
                self.check_update_db_nr_band(nr_band_update_dict=nr_band_update_dict)
                band = self.nr_band.get((earfcndl, bw), {}).get('band')
                layer = self.nr_band.get((earfcndl, bw), {}).get('layer')
                ssbfreq = self.nr_band.get((earfcndl, bw), {}).get('ssbfrequency', '0')
                ess = not (sector_data.get('essScLocalId', None) in [None, '0'] and sector_data.get('essScPairId', None) in [None, '0'])
                # Cell level Parameters NR
                cell_dict[cell] = {
                    F'siteid': site.siteid,
                    F'CellName': cell,
                    F'CellType': cell_type,
                    F'nodeid': site.gnodeb_id,
                    F'nodeid_len': site.gnodeb_length,
                    F'cellid': cellid,
                    F'tac': data.get('nRTAC'),
                    F'pci': data.get('nRPCI'),
                    F'sec_mo': sec_mo,
                    F'sef_mo': sef_mo,
                    F'FRU_Type': all_frus,
                    F'ssbfreq': ssbfreq,
                    F'layer': layer,
                    F'band': band,
                    F'earfcndl': earfcndl,
                    F'bw': bw,
                    F'b_bw_l': F'N{band}-{bw}-{layer}',
                    F'DlOnly': False,
                    F'OnAir': OnAir,
                    F'BWMHz': F'{bw}MHz',
                    F'FWLL': cell.endswith('L'),
                    F'RDS': cell.endswith('DB'),
                    F'DAS': cell.endswith('DB'),
                    F'LAA': 'NA',
                    F'CRAN': (cell.endswith('_M') or cell.endswith('_N')),
                    F'DigSec': False,
                    F'DigSecType': False,
                    F'ESS': ess,
                    F'ESS_N30': ess and band == '30',
                    F'NGFW': cell.endswith('_G'),
                    F'Catm1': data.get('catm1SupportEnabled', 'false') == 'true',
                    F'NR_HiCap': False,
                    cell_type: True,
                    layer: True,
                    F"N{band}": True,
                    F'{bw}MHz': True,
                    F"N{band}/{bw}MHz": True,
                    F"{sector_data.get('noOfUsedRxAntennas', '0')}RX": True,
                    F"{sector_data.get('noOfUsedTxAntennas', '0')}TX": True,
                    F'sec_name': sec_name,
                    F'sec_numb': sec_numb,
                    F'SECTOR_{sec_numb}': True,
                    fru_type: True,
                    F'Cascaded': cascaded_flag,
                    F'SA': sa_flag,
                    F'SA_cell': sa_flag,
                    F'Barred': data.get('cellBarred', '0')[0] == '0',
                    F'<=30MHz': int(bw) <= 30,
                    F'>30MHz': int(bw) > 30,
                    F'>=30MHz': int(bw) >= 30,
                    F'<80MHz': int(bw) < 80,
                    F'>=80MHz': int(bw) >= 80,
                    F'>20MHz': int(bw) > 20,
                    F'<20MHz': int(bw) < 20,
                    F'<10MHz': int(bw) < 10,
                    F'>10MHz': int(bw) > 10,
                    F'NR_FDD': band in ['5', '12', '14', '29', '2', '66', '30'],
                    F'RedCap': data.get('redCap1RxEnabled', '') == 'true' and data.get('redCapUeLimit', '') == '3 (MAXIMUM)',
                    F'VoNR': vonr_flag,
                    F'ECDD': ECDD_flag,
                    F'ECDD_FDD': ECDD_flag and band != '77',
                    F'ECDD_TDD': ECDD_flag and band == '77',
                }
                # NR_MB+_n77, NR_MB+_n77G, NR_MB+_n77D
                if band == '77':
                    cell_dict[cell] |= {
                        F'NR_MB+_n77': True,
                        F'NR_MB+_n77G': 630000 <= int(earfcndl) <= 636666,
                        F'NR_MB+_n77D': 646666 <= int(earfcndl) <= 665333,
                    }
                # DoD1, DoD2
                if cell_dict[cell].get(F'NR_MB+_n77G', False):
                    cell_dict[cell] |= {'DoD1': cell.endswith('_2'), 'DoD2': cell.endswith('_3')}
                cell_dict[cell].update(self.nr_band.get((earfcndl, bw), {}))

            # EUtranCellFDD
            cell_type = 'FDD'
            for cell_mo in site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellFDD'):
                data = site.get_mo_data(cell_mo)
                cell = cell_mo.split('=')[-1]
                sec_mo = site.get_first_mo_from_ref_parameter(data.get('sectorCarrierRef'))
                sef_mo, fru_type, sector_data = None, [], {}
                if len(sec_mo) > 0:
                    sector_data = site.get_mo_data(sec_mo)
                    sef_mo = site.get_first_mo_from_ref_parameter(sector_data.get('sectorFunctionRef'))
                    if len(sef_mo) > 0:
                        frus = []
                        for rfb in site.get_mo_data(sef_mo).get('rfBranchRef', []):
                            rfb = site.get_first_mo_from_ref_parameter(rfb)
                            if 'Transceiver' in rfb:  frus.append(','.join(rfb.split(',')[:-1]))
                            elif site.get_first_mo_from_ref_parameter(site.get_mo_data(rfb).get('rfPortRef')):
                                frus.append(','.join(site.get_first_mo_from_ref_parameter(site.get_mo_data(rfb).get('rfPortRef')).split(',')[:-1]))
                        if len(set(frus)) > 1:
                            self.param_dict['sites'][site.siteid]['para']['>1_Radio_per_Cell'] = True
                        for fru in set(frus):
                            prod_type = site.get_mo_data(fru).get('productData', {}).get('productName', None)
                            if prod_type is not None and site.get_mo_data(fru).get('operationalState', '0')[0] == '1' and len(
                                    prod_type) > 0:
                                fru_type.append('_'.join(prod_type))
                all_frus = 'Radio_NA' if len(fru_type) == 0 else '___'.join(fru_type)
                fru_type = 'Radio_NA' if len(fru_type) == 0 else '_'.join(fru_type[0].split('_')[:2])
                ECDD_flag = 'commscope_cdd' in fru_type.lower()
                bw = data.get('dlChannelBandwidth', data.get('channelBandwidth', '0'))
                OnAir = data.get('additionalPlmnReservedList', [''])[0] == 'false' if cell.endswith('L') else \
                    data.get('primaryPlmnReserved') == 'false'
                earfcndl = data.get('earfcndl', data.get('earfcn', '0'))
                band = data.get('freqBand')
                dlonly = False if band == '46' else data.get('isDlOnly') == 'true'
                self.check_update_db_lte_earfcn_band_bw(earfcndl, band, bw, dlonly)
                # Special Setting for 850 as LB when 700 band doesnot exit on USID
                if earfcndl in earfcndl_850: self.earfcn_dict[earfcndl]['layer'] = 'LB'
                self.earfcn_dict[earfcndl].update({'USID_FREQ': True})
                layer = self.earfcn_dict.get(earfcndl).get('layer')
                ess = sector_data.get('essScLocalId', '0')[0] != '0' and sector_data.get('essScPairId', '0')[0] != '0'
                # Cell level Parameters FDD
                cell_dict[cell] = {
                    F'siteid': site.siteid,
                    F'CellName': cell,
                    F'CellType': cell_type,
                    F'nodeid': site.enodeb_id,
                    F'nodeid_len': '',
                    F'cellid': data.get('cellId'),
                    F'tac': data.get('tac'),
                    F'pci': data.get('physicalLayerCellId'),
                    F'sec_mo': sec_mo,
                    F'sef_mo': sef_mo,
                    F'FRU_Type': all_frus,
                    F'layer': layer,
                    F'band': band,
                    F'earfcndl': earfcndl,
                    F'bw': bw,
                    F'b_bw_l': F'B{band}-{bw}-{layer}',
                    F'DlOnly': dlonly,
                    F'OnAir': OnAir,
                    F'BWMHz': F'{int(bw) // 1000}MHz',
                    F'FWLL': cell.endswith('L'),
                    F'RDS': cell.endswith('DB'),
                    F'DAS': cell.endswith('DB'),
                    F'LAA': True if data.get('isLaa', 'false') == 'true' else False,
                    F'CRAN': (cell.endswith('_M') or cell.endswith('_N')),
                    F'DigSec': sector_data.get('sectorCarrierType', 'ZZZ')[0] != '0',
                    F'DigSecType': sector_data.get('sectorCarrierType', 'ZZZ')[0],
                    F'ESS': ess,
                    F'ESS_N30': False,
                    F'NGFW': cell.endswith('_G'),
                    F'Catm1': data.get('catm1SupportEnabled', 'false') == 'true',
                    cell_type: True,
                    layer: True,
                    F"B{band}": True,
                    F'{int(bw) // 1000}MHz': True,
                    F"B{band}/{int(bw) // 1000}MHz": True,
                    F"{sector_data.get('noOfRxAntennas', '0')}RX": True,
                    F"{sector_data.get('noOfTxAntennas', '0')}TX": True,
                    F'ulintermgt': (data.get('ulFrequencyAllocationProportion', '100') == '100') and (data.get('ulConfigurableFrequencyStart', '0') == '0'),
                    fru_type: True,
                    F'WCS_Slim': True if (earfcndl == '9820') and (data.get('dlFrequencyAllocationProportion', '100') == '64') and
                                         (data.get('dlConfigurableFrequencyStart', '0') == '37') else False,
                    F'Barred': data.get('cellBarred', '0')[0] == '0',
                    F'DL_ENDC_Buffer': data.get('endcSetupDlPktVolThr', '0') != '0' or data.get('endcSetupDlPktAgeThr', '0') != '0',
                    F'ECDD': ECDD_flag,
                    F'ECDD_FDD': ECDD_flag,
                }
                cell_dict[cell].update({'ESS_B30': cell_dict[cell].get('ESS', False) and cell_dict[cell].get('B30', False)})
            
            # EUtranCellTDD
            cell_type = 'TDD'
            for cell_mo in site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellTDD'):
                data = site.get_mo_data(cell_mo)
                cell = cell_mo.split('=')[-1]
                sec_mo = site.get_first_mo_from_ref_parameter(data.get('sectorCarrierRef'))
                sef_mo, fru_type, sector_data = None, [], {}
                if len(sec_mo) > 0:
                    sector_data = site.get_mo_data(sec_mo)
                    sef_mo = site.get_first_mo_from_ref_parameter(sector_data.get('sectorFunctionRef'))
                    if len(sef_mo) > 0:
                        frus = []
                        for rfb in site.get_mo_data(sef_mo).get('rfBranchRef', []):
                            rfb = site.get_first_mo_from_ref_parameter(rfb)
                            if 'Transceiver' in rfb:
                                frus.append(','.join(rfb.split(',')[:-1]))
                            elif site.get_mo_data(rfb).get('rfPortRef', '') not in [None, '', []]:
                                frus.append(','.join(site.get_first_mo_from_ref_parameter(site.get_mo_data(rfb).get('rfPortRef').split(',')[:-1])))
                        if len(set(frus)) > 1:
                            self.param_dict['sites'][site.siteid]['para']['>1_Radio_per_Cell'] = True
                        for fru in set(frus):
                            prod_type = site.get_mo_data(fru).get('productData', {}).get('productName', None)
                            if prod_type is not None and site.get_mo_data(fru).get('operationalState', '0')[0] == '1' and len(
                                    prod_type) > 0:
                                fru_type.append('_'.join(prod_type))
                all_frus = 'Radio_NA' if len(fru_type) == 0 else '___'.join(fru_type)
                fru_type = 'Radio_NA' if len(fru_type) == 0 else '_'.join(fru_type[0].split('_')[:2])
                ECDD_flag = 'commscope_cdd' in fru_type.lower()
                bw = data.get('dlChannelBandwidth', data.get('channelBandwidth', '0'))
                OnAir = data.get('additionalPlmnReservedList', [''])[0] == 'false' if cell.endswith('L') else \
                    data.get('primaryPlmnReserved') == 'false'
                earfcndl = data.get('earfcndl', data.get('earfcn', '0'))
                band = data.get('freqBand')
                dlonly = False if band == '46' else data.get('isDlOnly') == 'true'
                self.check_update_db_lte_earfcn_band_bw(earfcndl, band, bw, dlonly)
                self.earfcn_dict[earfcndl].update({'USID_FREQ': True})
                layer = self.earfcn_dict.get(earfcndl).get('layer')
                ess = sector_data.get('essScLocalId', '0')[0] != '0' and sector_data.get('essScPairId', '0')[0] != '0'
                # Cell level Parameters TDD
                cell_dict[cell] = {
                    F'siteid': site.siteid,
                    F'CellName': cell,
                    F'CellType': cell_type,
                    F'nodeid': site.enodeb_id,
                    F'nodeid_len': '',
                    F'cellid': data.get('cellId'),
                    F'tac': data.get('tac'),
                    F'pci': data.get('physicalLayerCellId'),
                    F'sec_mo': sec_mo,
                    F'sef_mo': sef_mo,
                    F'FRU_Type': all_frus,
                    F'layer': layer,
                    F'band': band,
                    F'earfcndl': earfcndl,
                    F'bw': bw,
                    F'b_bw_l': F'B{band}-{bw}-{layer}',
                    F'DlOnly': dlonly,
                    F'OnAir': OnAir,
                    F'BWMHz': F'{int(bw) // 1000}MHz',
                    F'FWLL': cell.endswith('L'),
                    F'RDS': cell.endswith('DB'),
                    F'DAS': cell.endswith('DB'),
                    F'LAA': True if data.get('isLaa', 'false') == 'true' else False,
                    F'CRAN': (cell.endswith('_M') or cell.endswith('_N')),
                    F'DigSec': sector_data.get('sectorCarrierType', 'ZZZ')[0] != '0',
                    F'DigSecType': sector_data.get('sectorCarrierType', 'ZZZ')[0],
                    F'ESS': ess,
                    F'ESS_N30': False,
                    F'NGFW': cell.endswith('_G'),
                    F'Catm1': data.get('catm1SupportEnabled', 'false') == 'true',
                    cell_type: True,
                    layer: True,
                    F"B{band}": True,
                    F'{int(bw) // 1000}MHz': True,
                    F"B{band}/{int(bw) // 1000}MHz": True,
                    F"{sector_data.get('noOfRxAntennas', '0')}RX": True,
                    F"{sector_data.get('noOfTxAntennas', '0')}TX": True,
                    F'ulintermgt': (data.get('ulFrequencyAllocationProportion', '100') == '100') and (
                                data.get('ulConfigurableFrequencyStart', '0') == '0'),
                    fru_type: True,
                    F'Barred': data.get('cellBarred', '0')[0] == '0',
                    F'DL_ENDC_Buffer': data.get('endcSetupDlPktVolThr', '0') != '0' or data.get('endcSetupDlPktAgeThr', '0') != '0',
                    F'ECDD': ECDD_flag,
                    F'ECDD_TDD': ECDD_flag,
                }
                cell_dict[cell].update({'ESS_B30': cell_dict[cell].get('ESS', False) and cell_dict[cell].get('B30', False)})

            # NbIotCell
            cell_type = 'IOT'
            for cell_mo in site.get_mos_with_parent_moc(parent=site.enb, moc='NbIotCell'):
                data = site.get_mo_data(cell_mo)
                cell = cell_mo.split('=')[-1]
                fdd_id, nbIotCellType, ess = '', None, False
                fdd_tdd_mo = site.get_first_mo_from_ref_parameter(data.get('eutranCellRef'))
                if len(fdd_tdd_mo) > 0:
                    fdd_id = fdd_tdd_mo.split('=')[-1]
                    fdd_tdd_data = site.get_mo_data(fdd_tdd_mo)
                    nbIotCellType = 1 if fdd_tdd_data.get('dlChannelBandwidth',  fdd_tdd_data.get('channelBandwidth', '0')) == '5000' else 2
                    sec_mo = site.get_first_mo_from_ref_parameter(fdd_tdd_data.get('sectorCarrierRef'))
                    if len(sec_mo) > 0:
                        sector_data = site.get_mo_data(sec_mo)
                        ess = sector_data.get('essScLocalId', '0')[0] != '0' and sector_data.get('essScPairId', '0')[0] != '0'
                sec_mo = site.get_first_mo_from_ref_parameter(data.get('sectorCarrierRef'))
                if fdd_id == '' and len(sec_mo) > 0:
                    sector_data = site.get_mo_data(sec_mo)
                    ess = sector_data.get('essScLocalId', '0')[0] != '0' and sector_data.get('essScPairId', '0')[0] != '0'
                    for fdd_tdd_mo in sector_data.get('reservedBy', []):
                        if ',EUtranCellFDD=' in fdd_tdd_mo or ',EUtranCellTDD=' in fdd_tdd_mo:
                            fdd_id = fdd_tdd_mo.split('=')[-1]
                            fdd_tdd_data = site.get_mo_data(site.get_first_mo_from_ref_parameter(fdd_tdd_mo))
                            nbIotCellType = 1 if fdd_tdd_data.get('dlChannelBandwidth', fdd_tdd_data.get('channelBandwidth', '0')) == '5000' else 2
                            break
                if fdd_id == '': nbIotCellType = int(data.get('nbIotCellType', '3')[0])
                OnAir = 'false' in data.get('plmnReservedList', 'true')
                earfcndl = data.get('earfcndl', data.get('earfcn', '-1'))
                band = data.get('freqBand')
                # ess = sector_data.get('essScLocalId', '0')[0] != '0' and sector_data.get('essScPairId', '0')[0] != '0'
                # Cell level Parameters NbIoT
                cell_dict[cell] = {
                    F'siteid': site.siteid,
                    F'CellName': cell,
                    F'CellType': cell_type,
                    F'nodeid': site.enodeb_id,
                    F'nodeid_len': '',
                    F'cellid': data.get('cellId'),
                    F'tac': data.get('tac'),
                    F'pci': data.get('physicalLayerCellId'),
                    F'sec_mo': sec_mo,
                    F'band': band,
                    F'earfcndl': earfcndl,
                    F'OnAir': OnAir,
                    F'ESS': ess,
                    F'eutranCell': fdd_id,
                    cell_type: True,
                    F'nbIotCellType': str(nbIotCellType),
                    F'NbiotCellType=1or2': nbIotCellType in [1, 2]
                }
                if fdd_id != '':
                    cell_dict[fdd_id][F'NbiotCellType=1or2'] = nbIotCellType in [1, 2]
                    # cell_dict[fdd_id].update({F'NbiotCellType=1or2': nbIotCellType == 1 or nbIotCellType == 2})
            self.param_dict['sites'][site.siteid]['cells'].update(cell_dict)

    def get_usid_nrcells_ltecells_dataframes(self):
        nr_cell_list, lte_cell_list = [], []
        for site in self.param_dict['sites']:
            for cell in self.param_dict['sites'][site]['cells']:
                cell_dict_get = self.param_dict['sites'][site]['cells'].get(cell).get
                if cell_dict_get('CellType') == 'NR':
                    nr_cell_list.append([
                        cell_dict_get('siteid'), cell_dict_get('CellName'), cell_dict_get('nodeid'), cell_dict_get('nodeid_len'),
                        cell_dict_get('cellid'), cell_dict_get('tac'), cell_dict_get('pci'), cell_dict_get('earfcndl'), cell_dict_get('bw'),
                        cell_dict_get('ssbfrequency'), cell_dict_get('ssbsubcarrierspacing'), cell_dict_get('ssbperiodicity'),
                        cell_dict_get('ssboffset'), cell_dict_get('ssbduration'), cell_dict_get('band'), cell_dict_get('layer'),
                        cell_dict_get('sec_numb'), cell_dict_get('sec_name'), cell_dict_get('ESS')
                    ])
                elif cell_dict_get('CellType') == 'FDD' or cell_dict_get('CellType') == 'TDD':
                    lte_cell_list.append([
                        cell_dict_get('siteid'), cell_dict_get('CellType'), cell_dict_get('CellName'), cell_dict_get('nodeid'),
                        cell_dict_get('cellid'), cell_dict_get('tac'), cell_dict_get('pci'), cell_dict_get('earfcndl'), cell_dict_get('bw'),
                        cell_dict_get('band'), cell_dict_get('layer'),
                    ])
        df_tmp = pd.DataFrame(nr_cell_list, columns=['site', 'cell', 'nodeid', 'nodeid_len', 'cellid', 'tac', 'pci', 'arfcn', 'bw', 'ssbfreq',
                                                     'scc', 'periodicity', 'offset', 'duration', 'band', 'layer', 'sec_numb', 'sec_name', 'ESS'])
        df_tmp['flag'] = False
        df_tmp[['freq', 'relid', 'fdn']] = None
        if len(df_tmp.index) > 0:
            df_tmp['freq'] = df_tmp.apply(lambda x: F'{x.ssbfreq}-{x.scc}', axis=1)
            df_tmp['relid'] = df_tmp.apply(lambda x: F'{x.ssbfreq}-{x.scc}-{x.periodicity}-{x.offset}-{x.duration}', axis=1)
        self.df_nr_cells = df_tmp.copy()
        
        df_tmp = pd.DataFrame(lte_cell_list, columns=['site', 'cell_type', 'cell', 'nodeid', 'cellid', 'tac', 'pci', 'earfcn', 'bw', 'band', 'layer'])
        df_tmp['freq'] = df_tmp.earfcn
        df_tmp['relid'] = df_tmp.earfcn
        df_tmp['fdn'] = None
        df_tmp['flag'] = False
        self.df_lte_cells = df_tmp.copy()
    
    def update_lte_carrier_agg(self):
        u_noofscell = 0
        for s_site in self.param_dict.get('sites'):
            s_noofscell = 0
            for s_cell in self.param_dict.get('sites').get(s_site).get('cells'):
                noofscell = 0
                s_cell_dict_get = self.param_dict.get('sites').get(s_site).get('cells').get(s_cell).get
                if s_cell_dict_get('CellType', 'NR') in ['NR', 'IOT'] or s_cell_dict_get('DlOnly', False): continue
                for t_site in self.param_dict.get('sites'):
                    for t_cell in self.param_dict.get('sites').get(t_site).get('cells'):
                        t_cell_dict = self.param_dict.get('sites').get(t_site).get('cells').get(t_cell)
                        if (t_cell_dict.get('CellType', 'NR') in ['NR', 'IOT']) or (s_cell_dict_get('earfcndl') == t_cell_dict.get('earfcndl')) or \
                            (not self.get_co_sector_for_lte_cell(s_cell, t_cell)): continue
                        s_cell_set = F"B{s_cell_dict_get('band')}_{s_cell_dict_get('BWMHz')}"
                        if 'B66' in s_cell_set: s_cell_set = s_cell_set + ' (nonDlOnly)'
                        if F"{s_cell_set}--->B{t_cell_dict.get('band')}_{t_cell_dict.get('BWMHz')}" in self.param_dict['lte_ca_set']:
                            noofscell += 1
                        elif t_cell_dict.get('band') == '46' and t_cell_dict.get("LAA"):
                            noofscell += 1
                self.param_dict.get('sites').get(s_site).get('cells').get(s_cell).update({'noOfSCell': noofscell, '2DLCA': noofscell > 0})
                if s_noofscell < noofscell: s_noofscell = noofscell
                if u_noofscell < noofscell: u_noofscell = noofscell
            self.param_dict.get('sites').get(s_site).get('para').update({
                'noOfSCell': s_noofscell,
                '2DLCA': True if s_noofscell > 0 else False,
                '3DLCA': True if s_noofscell > 1 else False,
                '4DLCA': True if s_noofscell > 2 else False,
                '5DLCA': True if s_noofscell > 3 else False,
            })
        
        self.param_dict.get('para').update({
            'noOfSCell': u_noofscell,
            '2DLCA': True if u_noofscell > 0 else False,
            '3DLCA': True if u_noofscell > 1 else False,
            '4DLCA': True if u_noofscell > 2 else False,
            '5DLCA': True if u_noofscell > 3 else False,
        })
    
    @staticmethod
    def update_df_with_unique_moc_ids(df, col_list=None):
        df.replace({np.nan: None}, inplace=True)
        df.reset_index(drop=True, inplace=True)
        if len(df.index) > 0 and len(col_list) > 1 and col_list not in [None, 'None', '', [], {}]:
            moc_id = col_list[-1]
            df['cnt'] = df.groupby(col_list, sort=False).cumcount() + 1
            df.loc[df.cnt > 1, moc_id] = df.loc[df.cnt > 1, [moc_id, 'cnt']].apply(lambda x: '_'.join(x.astype(str)), axis=1)
            df.drop(['cnt'], axis=1, inplace=True)
        return df
        
    def get_nr_nr_relations_data(self):
        freq_list = []
        freq_rel_list = []
        cell_rel_list = []
        freq_id_list = ['ssbfreq', 'scc', 'duration', 'offset', 'periodicity']
        usid_cell_map = {}
        usid_cell_map.update({
            (row.nodeid, row.nodeid_len, row.cellid): {'site': row.site, 'cell': row.cell, 'nodeid': row.nodeid, 'nodeid_len': row.nodeid_len,
                                                       'cellid': row.cellid, 'pci': row.pci, 'tac': row.tac} for row in self.df_nr_cells.itertuples()
        })
        usid_cell_map.update({
            (row.site, row.cell): {'site': row.site, 'cell': row.cell, 'nodeid': row.nodeid, 'nodeid_len': row.nodeid_len, 'cellid': row.cellid,
                                   'pci': row.pci, 'tac': row.tac} for row in self.df_nr_cells.itertuples()
        })
        for site_key in self.sites:
            site = self.sites.get(site_key)
            if len(site.gnb_nnw) == 0 or site.gnb_nnw not in site.mo_list: continue
            for freq_mo in site.get_mos_with_parent_moc(parent=site.gnb_nnw, moc='NRFrequency'):
                mo_data = site.get_mo_data(freq_mo)
                freq_list.append([site.siteid, freq_mo.split('=')[-1], freq_mo, True, mo_data.get('arfcnValueNRDl'), mo_data.get('smtcScs'),
                                  mo_data.get('smtcDuration'), mo_data.get('smtcOffset'), mo_data.get('smtcPeriodicity')])
            for nr_mo in site.get_mos_with_parent_moc(moc='NRCellCU', parent=site.gnb_cucp):
                for mo_rel in site.get_mos_with_parent_moc(parent=nr_mo, moc='NRFreqRelation'):
                    mo_data = site.get_mo_data(mo_rel)
                    mo_dict = {_.split('=')[0]: _.split('=')[1] for _ in mo_rel.split(',')}
                    freq_ref = site.get_first_mo_from_ref_parameter(mo_data.get('nRFrequencyRef'))
                    freq_rel_list.append([site.siteid, mo_dict.get('NRCellCU'), mo_dict.get('NRFreqRelation'), freq_ref.split('=')[-1], mo_rel, True])
                for mo_crel in site.get_mos_with_parent_moc(parent=nr_mo, moc='NRCellRelation'):
                    neighourref = site.get_first_mo_from_ref_parameter(site.get_mo_data(mo_crel).get('nRCellRef'))
                    if len(neighourref) == 0: continue
                    elif ",NRCellCU=" in neighourref:
                        t_cell = usid_cell_map.get((site.siteid, neighourref.split('=')[-1]))
                    else:
                        ext_data = site.get_mo_data(','.join(neighourref.split(',')[:-1]))
                        t_cell = usid_cell_map.get((ext_data.get('gNBId'), ext_data.get('gNBIdLength'),
                                                    site.get_mo_data(neighourref).get('cellLocalId')))
                    if t_cell is not None:
                        mo_dict = {_.split('=')[0]: _.split('=')[1] for _ in mo_crel.split(',')}
                        cell_rel_list.append({
                            'site': site.siteid, 'cell': mo_dict.get('NRCellCU'), 'crelid': mo_dict.get('NRCellRelation'), 't_site': t_cell['site'],
                            't_cell': t_cell['cell'], 'nodeid': t_cell['nodeid'], 'nodeid_len': t_cell['nodeid_len'], 'cellid': t_cell['cellid'],
                            'pci': t_cell['pci'], 'tac': t_cell['tac'], 'fdn': mo_crel, 'flag': True,
                            'relid': site.get_mo_data(mo_crel).get('nRFreqRelationRef').split('=')[-1]
                        })
        del usid_cell_map
        
        # Get USID NR Cells
        df_nr_cr = self.df_nr_cells.loc[~(self.df_nr_cells.band.isin(['260', '261', '258']) & (self.df_nr_cells.sec_numb != '1'))]
        df_nrhb_n_s1 = self.df_nr_cells.loc[(self.df_nr_cells.band.isin(['260', '261', '258'])) & (self.df_nr_cells.sec_numb != '1')]
        if len(df_nr_cr.index) > 0:
            df_site_rel = df_nr_cr[['site', 'cell', 'flag']].merge(df_nr_cr[
                ['site', 'cell', 'freq', 'relid', 'fdn', 'flag', 'nodeid', 'nodeid_len', 'cellid', 'pci', 'tac'] + freq_id_list].rename(
                columns={'site': 't_site', 'cell': 't_cell'}, inplace=False), on='flag')
            if len(df_nrhb_n_s1.index) > 0:
                for row in df_nrhb_n_s1.groupby(['site', 'sec_name'], sort=False, as_index=False).head(1).itertuples():
                    df_tmp_aa = df_nr_cr.loc[(df_nr_cr.site == row.site) & (df_nr_cr.sec_name == row.sec_name) & (df_nr_cr.band.isin(['260', '261', '258']))]
                    if len(df_tmp_aa.index) > 0:
                        df_site_tmp = df_tmp_aa[['site', 'cell', 'flag']].merge(df_nrhb_n_s1.loc[(df_nrhb_n_s1.site == row.site) &
                            (df_nrhb_n_s1.sec_name == row.sec_name), ['site', 'cell', 'freq', 'relid', 'fdn', 'flag', 'nodeid', 'nodeid_len', 'cellid',
                            'pci', 'tac'] + freq_id_list].rename(columns={'site': 't_site', 'cell': 't_cell'}, inplace=False), on='flag')
                        df_site_rel = pd.concat([df_site_rel, df_site_tmp], join='inner', ignore_index=True)
            df_site_rel['crelid'] = df_site_rel.t_cell
            df_site_rel = df_site_rel.loc[~((df_site_rel.site == df_site_rel.t_site) & (df_site_rel.cell == df_site_rel.t_cell))]
            df_site_rel = df_site_rel.groupby(['site', 'cell', 't_site', 't_cell'], sort=False, as_index=False).head(1)
            df_site_rel.reset_index(drop=True, inplace=True)
        else:
            df_site_rel = pd.DataFrame([], columns=['site', 'cell', 'relid', 'crelid', 't_site', 't_cell', 'nodeid', 'nodeid_len',
                                                    'cellid', 'pci', 'tac', 'fdn', 'flag', 'freq'] + freq_id_list)
        del df_nr_cr, df_nrhb_n_s1
        
        # NRFrequency
        freq_id_list = ['ssbfreq', 'scc', 'duration', 'offset', 'periodicity']
        df_temp = pd.DataFrame(freq_list, columns=['site', 'freq', 'fdn', 'flag'] + freq_id_list)
        # Fix the duration, offset, periodicity based on Site Data
        if len(df_temp.index) > 0 and len(df_site_rel.index) > 0:
            df_temp = df_temp.merge(df_site_rel[['site'] + freq_id_list].groupby(['site'] + freq_id_list, sort=False, as_index=False).head(1),
                                    on=['site', 'ssbfreq', 'scc'], how='left', suffixes=('', '_site'))
            df_temp.loc[((~df_temp.duration_site.isna()) & (df_temp.duration != df_temp.duration_site)), ['duration']] = \
                df_temp.loc[((~df_temp.duration_site.isna()) & (df_temp.duration != df_temp.duration_site))].duration_site
            df_temp.loc[((~df_temp.offset_site.isna()) & (df_temp.offset != df_temp.offset_site)), ['offset']] = \
                df_temp.loc[((~df_temp.offset_site.isna()) & (df_temp.offset != df_temp.offset_site))].offset_site
            df_temp.loc[((~df_temp.periodicity_site.isna()) & (df_temp.periodicity != df_temp.periodicity_site)), ['periodicity']] = \
                df_temp.loc[((~df_temp.periodicity_site.isna()) & (df_temp.periodicity != df_temp.periodicity_site))].periodicity_site
            df_temp.drop(columns=['duration_site', 'offset_site', 'periodicity_site'], inplace=True)

        if len(df_site_rel.index) > 0:
            df_temp = pd.concat([df_temp, df_site_rel], join='inner', ignore_index=True)
            df_temp = df_temp.groupby(['site'] + freq_id_list, sort=False, as_index=False).head(1)
            df_temp = self.update_df_with_unique_moc_ids(df=df_temp, col_list=['site', 'freq'])
        if len(df_temp.index):
            df_temp.loc[df_temp.fdn.isna(), 'fdn'] = df_temp.loc[df_temp.fdn.isna(), ['site', 'freq']].apply(
                lambda x: F"{self.sites.get(F'site_{x.site}').gnb_nnw},NRFrequency={x.freq}", axis=1)
        self.df_nr_freq = df_temp.copy()[['site', 'freq', 'fdn', 'flag'] + freq_id_list]
        
        # NRFreqRelation
        df_temp = pd.DataFrame(freq_rel_list, columns=['site', 'cell', 'relid', 'freq', 'fdn', 'flag'])
        df_temp = df_temp.merge(self.df_nr_freq[['site', 'freq'] + freq_id_list], on=['site', 'freq'], how='left')
        df_temp.drop(columns=['freq'], inplace=True)
        if len(df_site_rel.index) > 0:
            df_temp = pd.concat([df_temp, df_site_rel], join='inner', ignore_index=True)
            df_temp = df_temp.groupby(['site', 'cell'] + freq_id_list, sort=False, as_index=False).head(1)
            df_temp = self.update_df_with_unique_moc_ids(df=df_temp, col_list=['site', 'cell', 'relid'])
        df_temp = df_temp.merge(self.df_nr_freq[['site', 'freq'] + freq_id_list], on=['site'] + freq_id_list, how='left')
        if len(df_temp.index) > 0:
            df_temp.loc[df_temp.fdn.isna(), 'fdn'] = df_temp.loc[df_temp.fdn.isna(), ['site', 'cell', 'relid']].apply(
                lambda x: F"{self.sites.get(F'site_{x.site}').gnb_cucp},NRCellCU={x.cell},NRFreqRelation={x.relid}", axis=1)
        self.df_nr_rel = df_temp.copy()[['site', 'cell', 'relid', 'freq', 'flag', 'fdn'] + freq_id_list]
        
        # NRCellRelation
        crel_columns = ['site', 'cell', 'crelid', 't_site', 't_cell', 'nodeid', 'nodeid_len', 'cellid', 'pci', 'tac', 'fdn', 'flag', 'relid']
        df_temp = pd.DataFrame(cell_rel_list) if len(cell_rel_list) > 0 else pd.DataFrame(cell_rel_list, columns=crel_columns)
        df_temp = df_temp.merge(self.df_nr_rel[['site', 'cell', 'relid'] + freq_id_list], on=['site', 'cell', 'relid'], how='left')
        df_temp.drop(columns=['relid'], inplace=True)
        if len(df_site_rel.index) > 0:
            df_temp = pd.concat([df_temp, df_site_rel], join='inner', ignore_index=True)
            df_temp = df_temp.groupby(['site', 'cell', 't_site', 't_cell'], sort=False, as_index=False).head(1)
            df_temp = self.update_df_with_unique_moc_ids(df=df_temp, col_list=['site', 'cell', 'crelid'])
        df_temp = df_temp.merge(self.df_nr_rel[['site', 'cell', 'relid', 'freq'] + freq_id_list], on=['site', 'cell'] + freq_id_list, how='left')
        if len(df_temp.index):
            df_temp.loc[df_temp.fdn.isna(), 'fdn'] = df_temp.loc[df_temp.fdn.isna(), ['site', 'cell', 'crelid']].apply(
                lambda x: F"{self.sites.get(F'site_{x.site}').gnb_cucp},NRCellCU={x.cell},NRCellRelation={x.crelid}", axis=1)
        self.df_nr_crel = df_temp.copy()[['site', 'cell', 'crelid', 't_site', 't_cell', 'nodeid', 'nodeid_len', 'cellid', 'pci',
                                          'tac', 'fdn', 'flag', 'relid', 'freq'] + freq_id_list]

    def get_lte_nr_relations_data(self):
        def get_ext_gnb_gnb_cell(row_ext):
            ext_node_id = F'310410-000000{row_ext["nodeid"]}'
            ext_cell_id = F'310410-000000{row_ext["nodeid"]}-{row_ext["cellid"]}'
            crelid = F'310410-000000{row_ext["nodeid"]}-{row_ext["cellid"]}'
            if len(df_ext_node.loc[(df_ext_node.site == row_ext['site']) & (df_ext_node.nodeid == row_ext['nodeid'])].index):
                ext_node_id = df_ext_node.loc[(df_ext_node.site == row_ext['site']) & (df_ext_node.nodeid == row_ext['nodeid'])].ext_node.values[0]
            if len(df_ext_cell.loc[(df_ext_cell.site == row_ext['site']) & (df_ext_cell.nodeid == row_ext['nodeid']) & (df_ext_cell.cellid == row_ext['cellid'])].index):
                ext_cell_id = df_ext_cell.loc[(df_ext_cell.site == row_ext['site']) & (df_ext_cell.nodeid == row_ext['nodeid']) &
                                              (df_ext_cell.cellid == row_ext['cellid'])].ext_cell.values[0]
            return ext_node_id, ext_cell_id, crelid
        
        freq_list, freq_rel_list, cell_rel_list = [], [], []
        ext_node, ext_cell = [], []
        freq_id_list = ['ssbfreq', 'scc', 'duration', 'offset', 'periodicity']
        for site_key in self.sites:
            site = self.sites.get(site_key)
            for freq_mo in site.get_mos_with_parent_moc(parent=site.enb_gnw, moc='GUtranSyncSignalFrequency'):
                freq_data = site.get_mo_data(freq_mo)
                freq_list.append([site.siteid, freq_mo.split('=')[-1], freq_mo, True, freq_data.get('arfcn'), freq_data.get('smtcScs'),
                                  freq_data.get('smtcDuration'), freq_data.get('smtcOffset'), freq_data.get('smtcPeriodicity')])
            for fdd_mo in site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellFDD'):
                for mo_rel in site.get_mos_with_parent_moc(parent=fdd_mo, moc='GUtranFreqRelation'):
                    mo_dict = {_.split('=')[0]: _.split('=')[1] for _ in mo_rel.split(',')}
                    freq_ref = site.get_first_mo_from_ref_parameter(site.get_mo_data(mo_rel).get('gUtranSyncSignalFrequencyRef'))
                    freq_rel_list.append([site.siteid, mo_dict.get('EUtranCellFDD'), mo_dict.get('GUtranFreqRelation'), freq_ref.split("=")[-1], mo_rel, True])
                    for mo_crel in site.get_mos_with_parent_moc(parent=mo_rel, moc='GUtranCellRelation'):
                        mo_dict = {_.split('=')[0]: _.split('=')[1] for _ in mo_crel.split(',')}
                        ext_mo = site.get_first_mo_from_ref_parameter(site.get_mo_data(mo_crel).get('neighborCellRef'))
                        ext_mo_dict = {_.split('=')[0]: _.split('=')[1] for _ in ext_mo.split(',')}
                        if len(ext_mo) > 0:
                            gnbid = site.get_mo_data(','.join(ext_mo.split(',')[:-1])).get('gNodeBId', None)
                            gnb_len = site.get_mo_data(','.join(ext_mo.split(',')[:-1])).get('gNodeBIdLength', None)
                            cellid = site.get_mo_data(ext_mo).get('localCellId', None)
                        else: gnbid, gnb_len, cellid = None, None, None
                        cell_rel_list.append([site.siteid, mo_dict.get('EUtranCellFDD'), mo_dict.get('GUtranFreqRelation'),
                                              mo_dict.get('GUtranCellRelation'), ext_mo_dict.get('ExternalGNodeBFunction', None),
                                              ext_mo_dict.get('ExternalGUtranCell', None), mo_crel, True, gnbid, gnb_len, cellid])
            # External MOs for LTE to NR
            for ext_mo in site.get_mos_with_parent_moc(parent=site.enb_gnw, moc='ExternalGNodeBFunction'):
                freq_data = site.get_mo_data(ext_mo)
                tp_id, tp_ip = None, None
                tp = site.get_mos_with_parent_moc(parent=ext_mo, moc='TermPointToGNB')
                if len(tp) > 0:
                    tp_id = tp[0].split('=')[-1]
                    tp_ip = site.get_mo_data(tp[0]).get('ipv6Address' '::')
                ext_node.append([site.siteid, ext_mo.split('=')[-1], freq_data.get('gNodeBId'), freq_data.get('gNodeBIdLength'),
                                 freq_data.get('gNodeBPlmnId'), ext_mo, True, tp_id, tp_ip])
                for ext_cell_mo in site.get_mos_with_parent_moc(parent=ext_mo, moc='ExternalGUtranCell'):
                    ext_cell.append([site.siteid, ext_mo.split('=')[-1], ext_cell_mo.split('=')[-1], freq_data.get('gNodeBId'),
                                     freq_data.get('gNodeBIdLength'), site.get_mo_data(ext_cell_mo).get('localCellId'), ext_cell_mo, True])
        
        # Create NR Cell Data
        df_ext_node = pd.DataFrame(ext_node, columns=['site', 'ext_node', 'nodeid', 'nodeid_len', 'plmn', 'fdn', 'flag', 'tp_id', 'tp_ip'])
        df_ext_cell = pd.DataFrame(ext_cell, columns=['site', 'ext_node', 'ext_cell', 'nodeid', 'nodeid_len', 'cellid', 'fdn', 'flag'])

        df_site_rel = self.df_lte_cells.copy()[['site', 'cell_type', 'cell', 'bw', 'band', 'layer', 'flag']]
        df_site_rel = df_site_rel.loc[((df_site_rel.layer != 'DlOnly') & (df_site_rel.cell_type == 'FDD') & (~(df_site_rel.cell.str.endswith('_L'))))]
        df_site_rel = df_site_rel[['site', 'cell', 'bw', 'band', 'flag']]
        df_site_rel = df_site_rel.merge(self.df_nr_cells.loc[~((self.df_nr_cells.band.isin(['260', '261', '258'])) & (self.df_nr_cells.sec_numb != '1'))],
                                        on='flag', suffixes=('', '_nr')).reset_index(drop=True, inplace=False)
        if self.market == 'NE':
            df_site_rel = df_site_rel.loc[(
                ((df_site_rel.bw.astype(int) >= 5000) & (df_site_rel.band.isin(['2', '4', '30', '66']))) |
                ((df_site_rel.band.isin(['5', '12', '17'])) & (df_site_rel.layer.isin(['NR_LB', 'NR_MB', 'NR_HB', 'NR_MB+_N77']))) |
                ((df_site_rel.band.isin(['14'])) & (df_site_rel.layer.isin(['NR_LB', 'NR_MB', 'NR_HB', 'NR_MB+_N77'])))
            )]
        else:
            df_site_rel = df_site_rel.loc[(
                ((df_site_rel.bw.astype(int) >= 5000) & (df_site_rel.band.isin(['2', '4', '30', '66']))) |
                ((df_site_rel.band.isin(['5', '12', '17'])) & (df_site_rel.layer.isin(['NR_LB', 'NR_MB', 'NR_HB', 'NR_MB+_N77']))) |
                ((df_site_rel.band.isin(['14'])) & (df_site_rel.layer.isin(['NR_MB', 'NR_HB', 'NR_MB+_N77'])))
            )]
        # ((df_site_rel.bw.astype(int) == 5000) & (df_site_rel.band.isin(['2', '4', '30', '66'])) & (df_site_rel.layer.isin(['NR_HB', 'NR_MB+_N77']))) |
        df_site_rel.drop(columns=['bw', 'band'], inplace=True)
        df_site_rel.rename(columns={'site_nr': 't_site', 'cell_nr': 't_cell', 'band_nr': 'band', 'bw_nr': 'bw'}, inplace=True)
        df_site_rel.reset_index(drop=True, inplace=True)
        # df_site_rel['relid'] = df_site_rel.freq
        df_site_rel[['ext_node', 'ext_cell', 'crelid']] = None
        if len(df_site_rel.index):
            df_site_rel[['ext_node', 'ext_cell', 'crelid']] = df_site_rel.apply(get_ext_gnb_gnb_cell, axis=1, result_type="expand")

        # LTE - NR GUtranSyncSignalFrequency
        df_temp = pd.DataFrame(freq_list, columns=['site', 'freq', 'fdn', 'flag'] + freq_id_list)
        # Fix the duration, offset, periodicity based on Site Data
        if len(df_temp.index) > 0 and len(df_site_rel.index) > 0:
            df_temp = df_temp.merge(df_site_rel[['site'] + freq_id_list].groupby(['site'] + freq_id_list, sort=False, as_index=False).head(1),
                                    on=['site', 'ssbfreq', 'scc'], how='left', suffixes=('', '_site'))
            df_temp.loc[((~df_temp.duration_site.isna()) & (df_temp.duration != df_temp.duration_site)), ['duration']] = \
                df_temp.loc[((~df_temp.duration_site.isna()) & (df_temp.duration != df_temp.duration_site))].duration_site
            df_temp.loc[((~df_temp.offset_site.isna()) & (df_temp.offset != df_temp.offset_site)), ['offset']] = \
                df_temp.loc[((~df_temp.offset_site.isna()) & (df_temp.offset != df_temp.offset_site))].offset_site
            df_temp.loc[((~df_temp.periodicity_site.isna()) & (df_temp.periodicity != df_temp.periodicity_site)), ['periodicity']] = \
                df_temp.loc[((~df_temp.periodicity_site.isna()) & (df_temp.periodicity != df_temp.periodicity_site))].periodicity_site
            df_temp.drop(columns=['duration_site', 'offset_site', 'periodicity_site'], inplace=True)
        df_temp = pd.concat([df_temp, df_site_rel], join='inner', ignore_index=True).groupby(['site'] + freq_id_list, sort=False, as_index=False).head(1)
        df_temp = self.update_df_with_unique_moc_ids(df=df_temp, col_list=['site', 'freq'])
        if len(df_temp.index) > 0:
            df_temp.loc[df_temp.fdn.isna(), 'fdn'] = df_temp.loc[df_temp.fdn.isna(), ['site', 'freq']].apply(
                lambda x: F"{self.sites.get(F'site_{x.site}').enb_gnw},GUtranSyncSignalFrequency={x.freq}", axis=1)
        self.df_lte_nr_freq = df_temp.copy()[['site', 'freq', 'fdn', 'flag'] + freq_id_list]
        
        # LTE - NR GUtranFreqRelation
        df_temp = pd.DataFrame(freq_rel_list, columns=['site', 'cell', 'relid', 'freq', 'fdn', 'flag'])
        df_temp = df_temp.merge(self.df_lte_nr_freq[['site', 'freq'] + freq_id_list], on=['site', 'freq'], how='left')

        df_temp = pd.concat([df_temp, df_site_rel], join='inner', ignore_index=True).groupby(
            ['site', 'cell'] + freq_id_list, sort=False, as_index=False).head(1)
        df_temp = self.update_df_with_unique_moc_ids(df=df_temp, col_list=['site', 'cell', 'relid'])
        if len(df_temp.index):
            df_temp.loc[df_temp.fdn.isna(), 'fdn'] = df_temp.loc[df_temp.fdn.isna(), ['site', 'cell', 'relid']].apply(
                lambda x: F"{self.sites.get(F'site_{x.site}').enb},EUtranCellFDD={x.cell},GUtranFreqRelation={x.relid}", axis=1)
        self.df_lte_nr_rel = df_temp.copy()[['site', 'cell', 'relid', 'fdn', 'flag', 'freq'] + freq_id_list]
        
        # LTE - NR GUtranCellRelation
        df_temp = pd.DataFrame(cell_rel_list, columns=['site', 'cell', 'relid', 'crelid', 'ext_node', 'ext_cell', 'fdn', 'flag', 'nodeid', 'nodeid_len', 'cellid'])
        df_temp = df_temp.merge(self.df_lte_nr_rel[['site', 'cell', 'relid', 'freq'] + freq_id_list], on=['site', 'cell', 'relid'], how='left')
        df_temp = df_temp.merge(self.df_nr_cells.copy()[['site', 'cell', 'nodeid', 'nodeid_len', 'cellid', 'tac', 'pci', 'band']].rename(
            columns={'site': 't_site', 'cell': 't_cell'}, inplace=False), on=['nodeid', 'nodeid_len', 'cellid'], how='left')
        df_temp = df_temp.loc[~df_temp.t_cell.isna()].reset_index(drop=True, inplace=False)
        df_temp = pd.concat([df_temp, df_site_rel], join='inner', ignore_index=True).groupby(['site', 'cell', 't_site', 't_cell'],
                                                                                             sort=False, as_index=False).head(1)
        df_temp = self.update_df_with_unique_moc_ids(df=df_temp, col_list=['site', 'cell', 'relid', 'crelid'])
        if len(df_temp.index):
            df_temp.loc[df_temp.fdn.isna(), 'fdn'] = df_temp.loc[df_temp.fdn.isna(), ['site', 'cell', 'relid', 'crelid']].apply(
                lambda x: F"{self.sites.get(F'site_{x.site}').enb},EUtranCellFDD={x.cell},GUtranFreqRelation={x.relid},GUtranCellRelation={x.crelid}", axis=1)
        self.df_lte_nr_crel = df_temp.copy()[['site', 'cell', 'relid', 'crelid', 'fdn', 'flag', 't_site', 't_cell', 'nodeid', 'nodeid_len',
                                              'cellid', 'ext_node', 'ext_cell', 'tac', 'pci', 'band', 'freq'] + freq_id_list]
    
    def get_index_of_lte_freq_flag_for_la_market(self, df_lte_tmp_rel):
        sites_get = self.param_dict.get('sites').get
        la_relations_flag = []
        for row_t in df_lte_tmp_rel.itertuples():
            if sites_get(row_t.site).get('cells').get(row_t.cell).get('earfcndl') == row_t.earfcn: continue
            s_layer = sites_get(row_t.site).get('cells').get(row_t.cell).get('layer')
            s_band = sites_get(row_t.site).get('cells').get(row_t.cell).get('band')
            t_layer = self.earfcn_dict.get(row_t.earfcn, {}).get('layer', 'LB')
            t_band = self.earfcn_dict.get(row_t.earfcn, {}).get('band', '0')
            t_bw = self.earfcn_dict.get(row_t.earfcn, {}).get('bandwidth', '5000')
            if (s_band in ['17', '12', '14'] and t_band in ['29']) or \
                    (s_layer == 'DlOnly' and (t_layer in ['DlOnly', 'HB+', 'HB'] or (t_layer == 'MB' and int(t_bw) <= 10000))):
                la_relations_flag.append(row_t.Index)
        return la_relations_flag

    def get_lte_lte_relations_data(self):
        freq_list, freq_rel_list, cell_rel_list = [], [], []
        usid_cell_map = {(row.nodeid, row.cellid): {'site': row.site, 'cell': row.cell, 'nodeid': row.nodeid, 'cellid': row.cellid, 'pci': row.pci,
                         'tac': row.tac} for row in self.df_lte_cells.loc[self.df_lte_cells.cell_type == 'FDD'].itertuples()}
        usid_cell_map.update({(row.site, row.cell): {'site': row.site, 'cell': row.cell, 'nodeid': row.nodeid, 'cellid': row.cellid, 'pci': row.pci,
                                                     'tac': row.tac} for row in self.df_lte_cells.loc[self.df_lte_cells.cell_type == 'FDD'].itertuples()})
        for site_key in self.sites:
            site = self.sites.get(site_key)
            if len(site.enb_enw) == 0 or site.enb_enw not in site.mo_list: continue
            for freq_mo in site.get_mos_with_parent_moc(parent=site.enb_enw, moc='EUtranFrequency'):
                freq_list.append([site.siteid, freq_mo.split('=')[-1], site.get_mo_data(freq_mo).get('arfcnValueEUtranDl'), freq_mo, True])
            for fdd_mo in site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellFDD'):
                for mo_rel in site.get_mos_with_parent_moc(parent=fdd_mo, moc='EUtranFreqRelation'):
                    mo_dict = {_.split('=')[0]: _.split('=')[1] for _ in mo_rel.split(',')}
                    cell = mo_dict.get('EUtranCellFDD')
                    relid = mo_dict.get('EUtranFreqRelation')
                    earfcn = site.get_mo_data(site.get_first_mo_from_ref_parameter(site.get_mo_data(mo_rel).get('eutranFrequencyRef'))).get('arfcnValueEUtranDl')
                    freq_rel_list.append([site.siteid, cell, relid, earfcn, mo_rel, True])
                    for mo in site.get_mos_with_parent_moc(parent=mo_rel, moc='EUtranCellRelation'):
                        neighourref = site.get_first_mo_from_ref_parameter(site.get_mo_data(mo).get('neighborCellRef'))
                        if len(neighourref) == 0: continue
                        if ',EUtranCellFDD=' in neighourref:
                            t_cell = usid_cell_map.get((site.siteid, neighourref.split('=')[-1]))
                        else:
                            t_cell = usid_cell_map.get((site.get_mo_data(','.join(neighourref.split(',')[:-1])).get('eNBId'),
                                                        site.get_mo_data(neighourref).get('localCellId')))
                        if t_cell is not None:
                            cell_rel_list.append({'site': site.siteid, 'cell': cell, 'earfcn': earfcn, 'crelid': mo.split('=')[-1],
                                                  't_site': t_cell['site'], 't_cell': t_cell['cell'], 'nodeid': t_cell['nodeid'],
                                                  'cellid': t_cell['cellid'], 'pci': t_cell['pci'], 'tac': t_cell['tac'], 'fdn': mo, 'flag': True})
                
        # USID LTE-LTE Relations Data
        df_site_rel = self.df_lte_cells.copy().loc[self.df_lte_cells.cell_type == 'FDD'][
            ['site', 'cell', 'nodeid', 'cellid', 'tac', 'pci', 'earfcn', 'bw', 'band', 'layer', 'freq', 'relid', 'fdn', 'flag']]
        df_site_rel = df_site_rel[['site', 'cell', 'flag']].merge(df_site_rel[['site', 'cell', 'freq', 'relid', 'nodeid', 'cellid', 'pci', 'tac',
                                    'fdn', 'flag', 'earfcn']].rename(columns={'site': 't_site', 'cell': 't_cell'}, inplace=False), on='flag')
        df_site_rel['crelid'] = df_site_rel.t_cell
        df_site_rel = df_site_rel.loc[~((df_site_rel.site == df_site_rel.t_site) & (df_site_rel.cell == df_site_rel.t_cell))]
        df_site_rel = df_site_rel.groupby(['site', 'cell', 't_site', 't_cell'], sort=False, as_index=False).head(1)
        df_site_rel.reset_index(drop=True, inplace=True)
        
        # EUtranFrequency
        df_temp = pd.DataFrame(freq_list, columns=['site', 'freq', 'earfcn', 'fdn', 'flag'])
        df_temp = pd.concat([df_temp, df_site_rel], join='inner', ignore_index=True)
        df_temp = df_temp.groupby(['site', 'earfcn'], sort=False, as_index=False).head(1)
        df_temp = self.update_df_with_unique_moc_ids(df=df_temp, col_list=['site', 'freq'])
        if len(df_temp.index):
            df_temp.loc[df_temp.fdn.isna(), 'fdn'] = df_temp.loc[df_temp.fdn.isna(), ['site', 'freq']].apply(
                    lambda x: F"{self.sites.get(F'site_{x.site}').enb_enw},EUtranFrequency={x.freq}", axis=1)
        self.df_lte_freq = df_temp.copy()[['site', 'freq', 'earfcn', 'fdn', 'flag']]
        
        # EUtranFreqRelation
        df_temp = pd.DataFrame(freq_rel_list, columns=['site', 'cell', 'relid', 'earfcn', 'fdn', 'flag'])
        df_temp = pd.concat([df_temp, df_site_rel], join='inner', ignore_index=True)
        df_temp = df_temp.groupby(['site', 'cell', 'earfcn'], sort=False, as_index=False).head(1)
        df_temp = df_temp.merge(self.df_lte_freq[['site', 'earfcn', 'freq']], on=['site', 'earfcn'], how='left')
        df_temp = self.update_df_with_unique_moc_ids(df=df_temp, col_list=['site', 'cell', 'relid'])
        if len(df_temp.index) > 0:
            df_temp.loc[df_temp.fdn.isna(), 'fdn'] = df_temp.loc[df_temp.fdn.isna(), ['site', 'cell', 'relid']].apply(
                lambda x: F"{self.sites.get(F'site_{x.site}').enb},EUtranCellFDD={x.cell},EUtranFreqRelation={x.relid}", axis=1)
        df_temp['cr_flag'] = True
        if self.market == 'LA' and len(df_temp) > 0:
            df_temp.loc[self.get_index_of_lte_freq_flag_for_la_market(df_temp), 'cr_flag'] = False
        self.df_lte_rel = df_temp.copy()[['site', 'cell', 'relid', 'earfcn', 'fdn', 'flag', 'freq', 'cr_flag']]
        # EUtranCellRelation
        crel_columns = ['site', 'cell', 'earfcn', 'crelid', 't_site', 't_cell', 'nodeid', 'cellid', 'pci', 'tac', 'fdn', 'flag']
        df_temp = pd.DataFrame(cell_rel_list) if len(cell_rel_list) > 0 else pd.DataFrame([], columns=crel_columns)
        df_temp = pd.concat([df_temp, df_site_rel], join='inner', ignore_index=True)
        df_temp = df_temp.groupby(['site', 'cell', 't_site', 't_cell'], sort=False, as_index=False).head(1)
        df_temp = df_temp.merge(self.df_lte_rel[['site', 'cell', 'earfcn', 'relid', 'cr_flag', 'freq']], on=['site', 'cell', 'earfcn'], how='left')
        df_temp = self.update_df_with_unique_moc_ids(df=df_temp, col_list=['site', 'cell', 'relid', 'crelid'])
        if len(df_temp.index) > 0:
            df_temp.loc[df_temp.fdn.isna(), 'fdn'] = df_temp.loc[df_temp.fdn.isna(), ['site', 'cell', 'relid', 'crelid']].apply(
                lambda x: F"{self.sites.get(F'site_{x.site}').enb},EUtranCellFDD={x.cell},EUtranFreqRelation={x.relid},EUtranCellRelation={x.crelid}", axis=1)
        self.df_lte_crel = df_temp.copy()[['site', 'cell', 'relid', 'crelid', 't_site', 't_cell', 'nodeid',  'cellid', 'pci',  'tac', 'earfcn',
                                           'freq', 'fdn', 'flag', 'cr_flag']]

    def update_relations_dict_with_site_data(self):
        temp_dict = {}
        nr_band_dict = pd.DataFrame(self.nr_band).T.reset_index(drop=True).T
        nr_band_dict.columns = nr_band_dict.loc['ssbfrequency']
        nr_band_dict = nr_band_dict.to_dict()
        for ssbfreq in list(set().union(self.df_nr_freq.ssbfreq.unique(), self.df_lte_nr_freq.ssbfreq.unique())):
            if ssbfreq in nr_band_dict.keys():
                ssb = nr_band_dict[ssbfreq]
            elif len(self.df_nr_freq.loc[(self.df_nr_freq.ssbfreq == ssbfreq)].index) > 0:
                ssb = self.df_nr_freq.loc[(self.df_nr_freq.ssbfreq == ssbfreq)].head(1).iloc[0]
            else:
                ssb = self.df_lte_nr_freq.loc[(self.df_lte_nr_freq.ssbfreq == ssbfreq)].head(1).iloc[0]

            band = ssb.get('band', self.get_nr_band_from_arfcndl_frequency(arfcndl=ssbfreq))
            layer = self.get_nr_layer_from_band(band=band)
            # ssbfreq', 'scc', 'duration', 'offset',
            #        'periodicity'
            temp_dict[ssbfreq] = {
                'ssbfreq': ssbfreq,
                'ssbfrequency': ssbfreq,
                'bschannelbwdl': ssb.get('bschannelbwdl', '0'),
                'ssbduration': ssb.get('ssbduration', ssb.get('duration', 'NA')),
                'ssboffset': ssb.get('ssboffset', ssb.get('offset', 'NA')),
                'ssbperiodicity': ssb.get('ssbperiodicity', ssb.get('periodicity', 'NA')),
                'ssbsubcarrierspacing': ssb.get('ssbsubcarrierspacing', ssb.get('scc', 'NA')),
                'layer': layer,
                'band': band,
                'N5_REL': False,
                'USID_FREQ': len(self.df_nr_cells.loc[self.df_nr_cells.ssbfreq == ssbfreq].index) > 0,
                'E///_FREQ': int(ssb.get('ssbsubcarrierspacing', ssb.get('scc', '0'))) <= 120,
                'SA': False,
                'ESS': len(self.df_nr_cells.loc[((self.df_nr_cells.ssbfreq == ssbfreq) & self.df_nr_cells.ESS)].index) > 0,
                'NR_MB+_n77': band == '77',
                'NR_MB+_n77_n_>40MHz': band == '77' and int(ssb.get('bschannelbwdl', 0)) > 40,
                'NR_MB+_n77D': 646666 <= int(ssbfreq) <= 665333 and band == '77',
                'NR_MB+_n77G': 630000 <= int(ssbfreq) <= 636666 and band == '77',
                F'N{band}': True,
                layer: True,
                F'{int(ssb.get("bschannelbwdl", 0))}MHz': True,
                '>40MHz': int(ssb.get('bschannelbwdl', 0)) > 40,
                '<=30MHz': int(ssb.get('bschannelbwdl', 0)) <= 30,
                '>30MHz': int(ssb.get('bschannelbwdl', 0)) > 30,
                '>=90MHz': int(ssb.get('bschannelbwdl', 0)) >= 90,
            }
        # SA, DoD1 & DoD2 for NR Frequency
        for site in self.param_dict['sites']:
            for cell in self.param_dict['sites'][site]['cells']:
                cell_dict_get = self.param_dict['sites'][site]['cells'].get(cell).get
                if cell_dict_get('CellType') == 'NR':
                    ssbfreq = cell_dict_get('ssbfrequency')
                    if ssbfreq in temp_dict.keys():
                        for para in ['SA', 'DoD1', 'DoD2']:
                            if cell_dict_get(para, False): temp_dict[ssbfreq][para] = True
        # N5_REL
        if len([_ for _ in temp_dict if temp_dict[_]['band'] == '5']) > 0:
            for ssbfreq in temp_dict:
                temp_dict[ssbfreq]['N5_REL'] = True
        self.param_dict['ssbfreq'] = copy.deepcopy(temp_dict)

        # Update EUtranFrequency earfcn_dict with missing band, BW data in DB
        temp_dict = {}
        for earfcn in self.df_lte_freq.earfcn.unique():
            if self.earfcn_dict.get(earfcn, None) is None:
                if len(self.df_lte_freq[(self.df_lte_freq.flag) & (self.df_lte_freq.earfcn == earfcn)].index) > 0:
                    bw, dlonly = '5000', False
                    row = self.df_lte_freq[(self.df_lte_freq.flag) & (self.df_lte_freq.earfcn == earfcn)].head(1).iloc[0]
                    band = self.sites.get(F'site_{row.site}').get_mo_para(mo=row.fdn, para='freqBand')
                    if len(self.df_lte_rel.loc[(self.df_lte_rel.flag) & (self.df_lte_rel.site == row.site) & (self.df_lte_rel.freq == row.freq)].index):
                        rel_row = self.df_lte_rel.loc[(self.df_lte_rel.flag) & (self.df_lte_rel.site == row.site) & (self.df_lte_rel.freq == row.freq)].head(1).iloc[0]
                        bw = self.sites.get(F'site_{rel_row.site}').get_mo_para(mo=rel_row.fdn, para='allowedMeasBandwidth')
                        bw = {'6': '1400', '15': '3000', '25': '5000', '50': '10000', '75': '15000', '100': '20000', 'N/F': '5000'}.get(bw)
                        if band == '66' and self.sites.get(F'site_{rel_row.site}').get_mo_para(rel_row.fdn, 'cellReselectionPriority') == '1': dlonly = True
                    self.check_update_db_lte_earfcn_band_bw(row.earfcn, band, bw, dlonly)
            temp_dict[earfcn] = self.earfcn_dict.get(earfcn)
            temp_dict[earfcn][F'B{temp_dict[earfcn]["band"]}/{int(temp_dict[earfcn]["bandwidth"])//1000}MHz'] = True
            if temp_dict[earfcn]["layer"] in ['LB', 'MB', 'MB+', 'HB', 'HB+']:
                if temp_dict[earfcn]["layer"] != 'LB': temp_dict[earfcn][F'{temp_dict[earfcn]["layer"][0:2]}*'] = True
                temp_dict[earfcn][F'{temp_dict[earfcn]["layer"][0:2]}/{int(temp_dict[earfcn]["bandwidth"]) // 1000}'] = True
            temp_dict[earfcn][earfcn] = True
            temp_dict[earfcn]['USID_FREQ'] = True if len(self.df_lte_cells.loc[self.df_lte_cells.earfcn == earfcn].index) > 0 else False
        
        tmp_flag = max([self.param_dict.get('sites').get(_, {}).get('para').get('FWLL', False) for _ in self.param_dict.get('sites')])
        if tmp_flag and '9820' in temp_dict.keys(): temp_dict['9820']['FWLL'] = tmp_flag
        tmp_flag = max([self.param_dict.get('sites').get(_, {}).get('para').get('WCS_Slim', False) for _ in self.param_dict.get('sites')])
        if tmp_flag and '9820' in temp_dict.keys(): temp_dict['9820']['WCS_Slim'] = tmp_flag

        self.param_dict['earfcn'] = copy.deepcopy(temp_dict)
    
    def update_lte_cellsleep_mimosleep(self):
        df_cell = self.df_lte_cells.copy()[['site', 'cell_type', 'cell', 'earfcn', 'bw', 'band', 'layer']]
        df_cell['band'] = df_cell.band.astype(int)
        df_cell['bw'] = df_cell.bw.astype(int)
        df_cell.sort_values(by=['band'], ascending=True, inplace=True)
        df_cell.sort_values(by=['bw'], ascending=False, inplace=True)
        df_cell.reset_index(drop=True, inplace=True)
        df_cell['sum_bw'] = 'CELLsleep_15MHz'
        df_cell['b17_5mhz'] = False
        df_cell['cell_sleep'] = True
        df_cell['mimo_sleep'] = False
        df_cell.loc[(df_cell.band == 14), 'cell_sleep'] = False
        if len(df_cell.index) > 0:
            df_cell['fwll_das_ngfw'] = df_cell.apply(
                lambda x: (self.param_dict.get('sites').get(x.site).get('cells').get(x.cell).get('FWLL', False) or
                           self.param_dict.get('sites').get(x.site).get('cells').get(x.cell).get('DAS', False) or
                           self.param_dict.get('sites').get(x.site).get('cells').get(x.cell).get('NGFW', False)), axis=1)
            df_cell.loc[df_cell.fwll_das_ngfw, 'cell_sleep'] = False
            df_cell.drop(['fwll_das_ngfw'], axis=1, inplace=True)
        df_cell['sec_str'] = None
        if len(df_cell.index) > 0:
            df_cell['sec_str'] = df_cell.cell.apply(lambda x: x[9:12].upper() if (x.endswith('_M') or x.endswith('_N')) else x[10])
        for sec_str in df_cell.sec_str.unique():
            cell_index = []
            if len(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([46]))].index) > 0:
                df_cell.loc[(df_cell.sec_str == sec_str), 'cell_sleep'] = False
            elif (len(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([17])) & (df_cell.bw >= 10000)].index) > 0) & \
                    (len(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([2, 4]))].index) > 0):
                cell_index.extend(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([17])) & (df_cell.bw >= 10000)].head(1).index)
                cell_index.extend(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([2, 4]))].head(1).index)
                sum_bw = int(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([17])) & (df_cell.bw >= 10000)].head(1).bw) + \
                    int(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([2, 4]))].head(1).bw)
                sum_bw = int(sum_bw//1000)
                if sum_bw <= 15: sum_bw = 'CELLsleep_15MHz'
                elif sum_bw == 20: sum_bw = 'CELLsleep_20MHz'
                else: sum_bw = 'CELLsleep_25MHz'
                df_cell.loc[(df_cell.sec_str == sec_str), 'sum_bw'] = sum_bw
                df_cell.loc[cell_index, 'cell_sleep'] = False
                if len(df_cell.loc[((df_cell.sec_str == sec_str) & (df_cell.cell_sleep))].index) > 0:
                    df_cell.loc[cell_index, 'mimo_sleep'] = True
            elif (len(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([17])) & (df_cell.bw == 5000)].index) > 0) & \
                    (len(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([2, 4]))].index) > 0):
                cell_index.extend(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([17])) & (df_cell.bw == 5000)].head(1).index)
                cell_index.extend(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([2, 4]))].head(1).index)
                sum_bw = int(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([17])) & (df_cell.bw == 5000)].head(1).bw) + \
                    int(df_cell.loc[(df_cell.sec_str == sec_str) & (df_cell.band.isin([2, 4]))].head(1).bw)
                sum_bw = int(sum_bw//1000)
                if sum_bw <= 15: sum_bw = 'CELLsleep_15MHz'
                elif sum_bw == 20: sum_bw = 'CELLsleep_20MHz'
                else: sum_bw = 'CELLsleep_25MHz'
                df_cell.loc[(df_cell.sec_str == sec_str), 'sum_bw'] = sum_bw
                df_cell.loc[(df_cell.sec_str == sec_str), 'b17_5mhz'] = True
                df_cell.loc[cell_index, 'cell_sleep'] = False
                if len(df_cell.loc[((df_cell.sec_str == sec_str) & (df_cell.cell_sleep))].index) > 0:
                    df_cell.loc[cell_index, 'mimo_sleep'] = True
            else:
                df_cell.loc[(df_cell.sec_str == sec_str), 'cell_sleep'] = False
        # Updated to get GS Values
        for row in df_cell.itertuples():
            self.param_dict.get('sites').get(row.site).get('cells').get(row.cell).update({
                row.sum_bw: True, '5MHzB17CellsPerSector': row.b17_5mhz,
                'CELLsleep': row.cell_sleep, 'MIMOsleep': row.mimo_sleep})

        # # Will get Live values from exixting cells with is already on-air
        # for row in df_cell.itertuples():
        #     sleep_cell_dict = {row.sum_bw: True, '5MHzB17CellsPerSector': row.b17_5mhz,
        #                        'CELLsleep': row.cell_sleep, 'MIMOsleep': row.mimo_sleep}
        #     if self.param_dict.get('sites').get(row.site).get('cells').get(row.cell).get('OnAir', False):
        #         site = self.sites.get(F'site_{row.site}')
        #         cell_mo = site.get_mos_with_parent_moc_moid(site.enb, F'EUtranCell{row.cell_type}', row.cell)[0]
        #         sleep_cell_dict.update({'CELLsleep': site.get_mo_data(site.get_mos_with_parent_moc(
        #             parent=cell_mo, moc='CellSleepFunction')[0]).get('sleepMode', 'aa')[0] == '1'})
        #         sleep_cell_dict.update({'MIMOsleep': site.get_mo_data(site.get_mos_with_parent_moc(
        #             parent=cell_mo, moc='MimoSleepFunction')[0]).get('sleepMode', 'aa')[0] == '4'})
        #     self.param_dict.get('sites').get(row.site).get('cells').get(row.cell).update(sleep_cell_dict)

    def update_lte_catm_cells(self):
        df_tmp_fdd_cells = self.df_lte_cells.copy()[['site', 'cell_type', 'cell', 'earfcn', 'bw', 'band']]
        df_tmp_fdd_cells = df_tmp_fdd_cells.loc[(df_tmp_fdd_cells.cell_type == 'FDD') & df_tmp_fdd_cells.band.isin(['17', '2', '4'])]
        if len(df_tmp_fdd_cells.loc[(df_tmp_fdd_cells.band == '17') & (df_tmp_fdd_cells.bw == '10000')].index) > 0:
            df_tmp_fdd_cells = df_tmp_fdd_cells.loc[(df_tmp_fdd_cells.band == '17') & (df_tmp_fdd_cells.bw == '10000')]
        elif len(df_tmp_fdd_cells.loc[df_tmp_fdd_cells.band.isin(['2', '4'])].index) > 0:
            df_tmp_fdd_cells = df_tmp_fdd_cells.loc[df_tmp_fdd_cells.band.isin(['2', '4'])]
            df_tmp_fdd_cells = df_tmp_fdd_cells.loc[df_tmp_fdd_cells.bw == df_tmp_fdd_cells['bw'].max()]
            df_tmp_fdd_cells = df_tmp_fdd_cells.loc[df_tmp_fdd_cells.earfcn == df_tmp_fdd_cells['earfcn'].min()]
        elif len(df_tmp_fdd_cells.loc[(df_tmp_fdd_cells.band == '17') & (df_tmp_fdd_cells.bw == '5000')].index) > 0:
            df_tmp_fdd_cells = df_tmp_fdd_cells.loc[(df_tmp_fdd_cells.band == '17') & (df_tmp_fdd_cells.bw == '5000')]
        for row in df_tmp_fdd_cells.itertuples():
            self.param_dict.get('sites').get(row.site).get('cells').get(row.cell).update({'Catm1': True})
        # for row in df_tmp_fdd_cells.itertuples():
        #     if not self.param_dict.get('sites').get(row.site).get('cells').get(row.cell).get('OnAir'):
        #         self.param_dict.get('sites').get(row.site).get('cells').get(row.cell).update({'Catm1': True})
        
    def update_site_usid_params_from_site_cell(self):
        # Update multiCarrier for LTE USID
        self.param_dict['para'].update({F'multiCarrier': len(self.df_lte_cells.loc[self.df_lte_cells.cell_type == 'FDD'].earfcn.unique()) > 1})
        
        # Update LB*, MB*, HB* and layes/bw for Cells
        for site in self.param_dict.get('sites'):
            for cell in self.param_dict.get('sites').get(site).get('cells'):
                if self.param_dict.get('sites').get(site).get('cells').get(cell).get('CellType', 'NA') not in ['FDD', 'TDD']: continue
                for param in ['LB', 'MB', 'MB+', 'HB', 'HB+']:
                    if self.param_dict.get('sites').get(site).get('cells').get(cell).get(param, False):
                        bw = F'{int(self.param_dict.get("sites").get(site).get("cells").get(cell).get("bw", "0")) // 1000}'
                        self.param_dict.get('sites').get(site).get('cells').get(cell)[F'{param[0:2]}/{bw}'] = True
                        if param not in ['LB']:
                            self.param_dict.get('sites').get(site).get('cells').get(cell)[F'{param[0:2]}*'] = True
        
        # Parameter Update for Site from Cells
        update_site_param_list = ['FWLL', 'WCS_Slim', 'DAS', 'RDS', 'LLA', 'B5', 'B14', 'B17', 'B30', 'B46', 'DlOnly', 'LB', 'MB', 'MB+', 'HB', 'HB+',
                                  'DigSec', 'AASFDD', 'AIR1641', 'SA', 'NR_LB', 'NR_MB', 'NR_MB+', 'NR_MB+_n77', 'NR_MB+_n77G', 'NR_HB']
        # TMBB, Pre-Production, Post-Production
        for site in self.param_dict.get('sites'):
            update_site_param_dict = {}
            for param in update_site_param_list:
                for cell in self.param_dict.get('sites').get(site).get('cells'):
                    if self.param_dict.get('sites').get(site).get('cells').get(cell).get(param, False):
                        update_site_param_dict[param] = True
                        break
            self.param_dict.get('sites').get(site).get('para').update(update_site_param_dict)

        for site in self.param_dict.get('sites'):
            self.param_dict.get('sites').get(site).get('para')['TMBB'] = bool(
                bool(self.param_dict.get('sites').get(site).get('para').get('NR_MB+_n77') or
                 self.param_dict.get('sites').get(site).get('para').get('NR_MB+_n77G')) and
                bool(self.param_dict.get('sites').get(site).get('para').get('NR_LB') or
                 self.param_dict.get('sites').get(site).get('para').get('NR_MB') or
                 self.param_dict.get('sites').get(site).get('para').get('NR_HB')) and
                len([_ for _ in self.param_dict.get('sites').get(site).get('cells').keys() if
                     self.param_dict.get('sites').get(site).get('cells').get(_).get('CellType', '') in ['FDD', 'TDD']]) > 0
            )
            self.param_dict.get('sites').get(site).get('para')['Post-Production'] = bool(
                    len([_ for _ in self.param_dict.get('sites').get(site).get('cells').keys() if
                         self.param_dict.get('sites').get(site).get('cells').get(_).get('CellType', '') in ['FDD', 'TDD'] and
                         self.param_dict.get('sites').get(site).get('cells').get(_).get('OnAir', False)]) > 0)
            self.param_dict.get('sites').get(site).get('para')['Pre-Production'] = (
                    not self.param_dict.get('sites').get(site).get('para')['Post-Production'])

        for site in self.param_dict.get('sites'):
            for cell in self.param_dict.get('sites').get(site).get('cells'):
                if self.param_dict.get('sites').get(site).get('cells').get(cell).get('CellType', '') == 'NR':
                    self.param_dict.get('sites').get(site).get('para').update({'gNB': True})
                    break
        
        # Parameter Update for Inter-PLMN_HO
        tmp_val = [{'mcc': '310', 'mnc': '410', 'mncLength': '3'}, {'mcc': '313', 'mnc': '100', 'mncLength': '3'}]
        for node in self.param_dict.get('sites'):
            site = self.sites.get(F'site_{node}')
            for row in self.df_lte_crel.loc[self.df_lte_crel.site == site.siteid].itertuples():
                'allowedPlmnList'
                plmn_list = site.get_mo_data(row.fdn).get('allowedPlmnList', [])
                if len(plmn_list) == 0: continue
                elif len(plmn_list) == 1 and plmn_list[0] in tmp_val: continue
                elif len(plmn_list) == 2 and plmn_list[0] in tmp_val and plmn_list[1] in tmp_val: continue
                else: self.param_dict['sites'][node]['para']['Inter-PLMN_HO'] = True
        
        # Parameter Update for USID from Site & Cells
        # SA__and__NR_MB+_n77G___and__DoD2
        usid_layer_dict = {}
        for site_key in self.param_dict['sites']:
            site_get = self.param_dict['sites'][site_key]['para'].get
            for cell_key in self.param_dict['sites'][site_key]['cells']:
                cell_get = self.param_dict['sites'][site_key]['cells'][cell_key].get
                if cell_get('LB'):
                    if int(cell_get('bw')) == 5000: usid_layer_dict['LB/5'] = True
                    if int(cell_get('bw')) >= 10000: usid_layer_dict['LB/10'] = True
                if cell_get('MB') or cell_get('MB+'):
                    if int(cell_get('bw')) == 5000: usid_layer_dict['MB/5'] = True
                    if int(cell_get('bw')) >= 10000: usid_layer_dict['MB/10'] = True
                if cell_get('CellType') == 'NR' and cell_get('SA') and cell_get('NR_MB+_n77G') and cell_get('DoD2'):
                    usid_layer_dict['SA__and__NR_MB+_n77G___and__DoD2'] = True
        self.param_dict['para'].update(usid_layer_dict)
        
        update_usid_param_list = ['FWLL', 'DAS', 'RDS', 'LLA', 'B5', 'B14', 'B17', 'B30', 'B46', 'DlOnly', 'LB', 'MB', 'MB+', 'HB', 'HB+',
                                  'DigSec', 'AASFDD', 'SA', 'NR_MB+_n77']
        update_usid_param_dict = {}
        for param in update_usid_param_list:
            for site in self.param_dict.get('sites'):
                if update_usid_param_dict.get(param, False): break
                if self.param_dict.get('sites').get(site).get('para').get(param, False):
                    update_usid_param_dict[param] = True
                    break
                for cell in self.param_dict.get('sites').get(site).get('cells'):
                    if self.param_dict.get('sites').get(site).get('cells').get(cell).get(param, False):
                        update_usid_param_dict[param] = True
                        break
        self.param_dict.get('para').update(update_usid_param_dict)
        # 'LTE_SA_Colo', 'NR_MB+_n77_Colo'
        if self.param_dict.get('para').get('SA'): self.param_dict.get('para')['LTE_SA_Colo'] = True
        if self.param_dict.get('para').get('NR_MB+_n77'): self.param_dict.get('para')['NR_MB+_n77_Colo'] = True

        # df_tmp = self.df_nr_rel.copy()
        # df_tmp['band'] = None
        # if len(df_tmp.index) > 0: df_tmp['band'] = df_tmp.ssbfreq.apply(lambda x: self.get_nr_band_from_arfcndl_frequency(x))
        # self.param_dict['para'].update({'Multiple_NR_Bands_TDD/FDD':
        #                                     len(df_tmp.loc[df_tmp.band.isin(['5', '12', '14', '29', '2', '66', '30'])].index) > 0 and
        #                                     len(df_tmp.loc[df_tmp.band.isin(['46', '48', '77', '258', '260', '261'])].index) > 0})

    def update_multiple_nr_bands_tdd_fdd(self):
        # Multiple_NR_Bands_TDD/FDD
        # len(df_tmp.loc[(df_tmp.site == site) & (df_tmp.cell == cell) &
        #                (df_tmp.band.isin(['46', '48', '77', '258', '260', '261']))].index) > 0:
        if len(self.df_nr_rel.index) > 0:
            df_tmp = self.df_nr_rel.copy()[['site', 'cell', 'ssbfreq']]
            df_tmp['band'] = df_tmp.ssbfreq.apply(lambda x: self.get_nr_band_from_arfcndl_frequency(x))
            for site in self.param_dict.get('sites'):
                for cell in self.param_dict.get('sites').get(site).get('cells'):
                    if self.param_dict.get('sites').get(site).get('cells').get(cell).get('CellType', '') == 'NR' and \
                            len(df_tmp.loc[(df_tmp.site == site) & (df_tmp.cell == cell) &
                                           (df_tmp.band.isin(['5', '12', '14', '29', '2', '66', '30']))].index) > 0 and \
                            len(df_tmp.loc[(df_tmp.site == site) & (df_tmp.cell == cell) &
                                           (df_tmp.band.isin(['77', '258', '260', '261']))].index) > 0:
                        self.param_dict.get('sites').get(site).get('cells').get(cell)['Multiple_NR_Bands_TDD/FDD'] = True
                        self.param_dict['sites'][site]['para']['Multiple_NR_Bands_TDD/FDD'] = True

    def update_lte_anchor_flag(self):
        """
        This method calculates the following 3 sets of suffixes:
            - LTE_ANCHOR, LTE_ANCHOR_NR_LB, LTE_ANCHOR_NR_MB, LTE_ANCHOR_NR_MB+, LTE_ANCHOR_NR_HB, LTE_ANCHOR_multipleNRBands
        self.df_lte_nr_rel = df_rel[['site', 'cell', 'relid', 'freq', 'fdn', 'flag', 'ssbfreq', 'scc', 'duration', 'offset', 'periodicity']]
        """
        df_lte_nr_rel = self.df_lte_nr_rel.copy()
        df_lte_nr_rel['band'] = None
        if len(df_lte_nr_rel.index):
            df_lte_nr_rel['band'] = df_lte_nr_rel.ssbfreq.apply(lambda x: self.get_nr_band_from_arfcndl_frequency(x))
        # Check if Only MB/5MHz exists
        mb5mhz_flag = True
        for site in self.param_dict.get('sites'):
            for cell in self.param_dict.get('sites').get(site).get('cells'):
                if self.param_dict.get('sites').get(site).get('cells').get(cell).get('layer') in ['MB', 'MB+', '66'] and \
                        int(self.param_dict.get('sites').get(site).get('cells').get(cell).get('bw', '0')) > 5000:
                    mb5mhz_flag = False
                    break
        for site in self.param_dict.get('sites'):
            nr_rel = df_lte_nr_rel.loc[df_lte_nr_rel.site == site]
            for cell in self.param_dict.get('sites').get(site).get('cells'):
                cell_dict = {'LTE_ANCHOR': False, 'LTE_ANCHOR_NR_LB': False, 'LTE_ANCHOR_NR_MB': False, 'LTE_ANCHOR_NR_MB+': False,
                             'LTE_ANCHOR_NR_HB': False, 'LTE_ANCHOR_multipleNRBands': False}
                cell_params_get = self.param_dict.get('sites').get(site).get('cells').get(cell).get
                cell_bw = cell_params_get('bw')
                cell_band = cell_params_get('band')
                nr_rel_band = set(list(nr_rel.loc[(nr_rel.cell == cell)].band.unique()))
                if (cell_params_get('CellType') == 'FDD') and (not cell_params_get('DlOnly')) and \
                        (not cell_params_get('FWLL')) and (int(cell_bw) >= 5000):
                    if mb5mhz_flag and (cell_band in ['2', '4', '66', '30']) and \
                        len(nr_rel_band.intersection({'5', '12', '14', '29'})) > 0: cell_dict.update({'LTE_ANCHOR_NR_LB': True})
                    if (cell_band in ['2', '4', '66', '30']) and int(cell_bw) > 5000 and \
                        len(nr_rel_band.intersection({'5', '12', '14', '29'})) > 0: cell_dict.update({'LTE_ANCHOR_NR_LB': True})
                    if len(nr_rel_band.intersection({'2', '66', '30'})) > 0: cell_dict.update({'LTE_ANCHOR_NR_MB': True})
                    if len(nr_rel_band.intersection({'46', '48', '77'})) > 0: cell_dict.update({'LTE_ANCHOR_NR_MB+': True})
                    if len(nr_rel_band.intersection({'260', '261', '258'})) > 0: cell_dict.update({'LTE_ANCHOR_NR_HB': True})
                    if len(nr_rel_band) > 1: cell_dict.update({'LTE_ANCHOR_multipleNRBands': True})
                    for _ in cell_dict.keys():
                        if cell_dict.get(_): cell_dict.update({'LTE_ANCHOR': True}); break
                self.param_dict['sites'][site]['cells'][cell].update(cell_dict)

    """
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    """

    def check_carrier_agg_flag(self, site, cell, t_site, t_cell):
        if not self.get_co_sector_for_lte_cell(cell, t_cell): return False
        source_cell_dict = self.param_dict.get('sites').get(site).get('cells').get(cell)
        target_cell_dict = self.param_dict.get('sites').get(t_site).get('cells').get(t_cell)
        if source_cell_dict.get('DlOnly', False): return False
        if source_cell_dict.get('earfcndl') == target_cell_dict.get('earfcndl'): return False
        p_cell_set = F"B{source_cell_dict.get('band')}_{source_cell_dict.get('BWMHz')}{' (nonDlOnly)' if source_cell_dict.get('band') == '66' else ''}"
        s_cell_set = F'B{target_cell_dict.get("band")}_{target_cell_dict.get("BWMHz")}'
        return True if F'{p_cell_set}--->{s_cell_set}' in self.param_dict['lte_ca_set'] else False

    @staticmethod
    def get_nr_band_from_arfcndl_frequency(arfcndl):
        arfcn_band_dict = {
            '5': (173800, 178800), '12': (145800, 149200), '14': (151600, 153600), '29': (143400, 145600),
            '2': (386000, 398000), '30': (470000, 472000), '66': (422000, 440000),
            '46': (743334, 795000), '48': (636667, 646666),
            '77': (620000, 680000),
            '258': (2016667, 2070832), '260': (2229166, 2279165), '261': (2070833, 2084999),
        }
        band = [_ for _ in arfcn_band_dict if arfcn_band_dict.get(_)[0] <= int(arfcndl) <= arfcn_band_dict.get(_)[1]]
        band = str(band[0]) if len(band) else '0'
        return str(band)
    
    @staticmethod
    def get_nr_layer_from_band(band):
        band = str(band)
        if band in ['260', '261', '258']: return 'NR_HB'
        elif band in ['5', '12', '14', '29']: return 'NR_LB'
        elif band in ['2', '66', '30']: return 'NR_MB'
        elif band in ['46', '48', '77']: return 'NR_MB+'
        else: return 'NA'
    
    @staticmethod
    def get_co_sector_for_lte_cell(cell, t_cell):
        if cell == t_cell: return False
        elif cell[-2:] in ['_M', '_N'] or t_cell[-2:] in ['_M', '_N']: return cell[9:12].upper() == t_cell[9:12].upper()
        else: return cell[10] == t_cell[10]

    @staticmethod
    def get_co_sector_for_nr_cell(source_cell, t_cell):
        def get_scrtor(cell=''):
            sec = cell
            source = cell.split('_')
            if len(source) == 3:
                sec = source[1]
                for i in ['N005', 'N002', 'N004', 'N066', 'N077', 'N260', 'N261', 'N258']:
                    sec = sec.replace(i, '')
            elif len(source) > 3:
                if source[1] in ['N005', 'N002', 'N004', 'N066', 'N077', 'N260', 'N261', 'N258']: sec = source[2] + '_' + source[-1][-1]
                else: sec = source[1] + '_' + source[2][-1]
            return sec
        return get_scrtor(source_cell) == get_scrtor(t_cell)
   
    def get_same_sef_for_nr_cell(self, s_site, s_cell, t_site, t_cell):
        return (self.param_dict['sites'][s_site]['cells'][s_cell].get('sef_mo') not in ['', None]) and \
               (self.param_dict['sites'][t_site]['cells'][t_cell].get('sef_mo') not in ['', None]) and \
               (self.param_dict['sites'][s_site]['cells'][s_cell].get('sef_mo') ==
                self.param_dict['sites'][t_site]['cells'][t_cell].get('sef_mo'))
    
    """
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!:- DataBase Get and/or  Update Procedure -:!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    """
    
    def set_db_vars(self):
        self.param_dict['lte_ca_set'] = [F'{_.pcell}--->{_.scell}' for _ in LTECAPair.objects.all()]
        # self.utran_band_dict = {(_.start, _.end): str(_.band) for _ in UMTSBand.objects.all()}
        for earfcn_layer in LTEearfcnBandBWLayer.objects.all():
            tmp_dict = {
                F'freq': str(earfcn_layer.earfcndl),
                F'band': str(earfcn_layer.band),
                F'bandwidth': str(earfcn_layer.bandwidth),
                F'layer': str(earfcn_layer.layer),
                F'b_bw_l': F'B{earfcn_layer.band}-{earfcn_layer.bandwidth}-{earfcn_layer.layer}',
                F'B{earfcn_layer.band}': True,
                F'{earfcn_layer.bandwidth // 1000}MHz': True,
                F'{earfcn_layer.layer}': True,
            }
            if str(earfcn_layer.earfcndl) in self.dlonly:
                del tmp_dict[F'{earfcn_layer.layer}']
                tmp_dict.update({F'DlOnly': True, F'layer': F'DlOnly', F'b_bw_l': F'B{earfcn_layer.band}-{earfcn_layer.bandwidth}-DlOnly'})
            if str(earfcn_layer.earfcndl) in self.earfcndl_lb_850:
                del tmp_dict[F'{earfcn_layer.layer}']
                tmp_dict |= {F'LB': True, F'layer': F'LB', F'b_bw_l': F'B{earfcn_layer.band}-{earfcn_layer.bandwidth}-LB'}
            self.earfcn_dict[str(earfcn_layer.earfcndl)] = tmp_dict
    
        for arfcn_item in NRBand.objects.filter(market=self.market):
            tmp_dict = {
                'arfcndl': str(arfcn_item.arfcndl),
                'bschannelbwdl': str(arfcn_item.bschannelbwdl),
                'ssbfrequency': str(arfcn_item.ssbfrequency),
                'ssbduration': str(arfcn_item.ssbduration),
                'ssboffset': str(arfcn_item.ssboffset),
                'ssbperiodicity': str(arfcn_item.ssbperiodicity),
                'ssbsubcarrierspacing': str(arfcn_item.ssbsubcarrierspacing),
                'band': str(arfcn_item.band),
                'layer': str(arfcn_item.layer),
                'b_bw_l': F'N{arfcn_item.band}-{arfcn_item.bschannelbwdl}-{arfcn_item.layer}',
            }
            self.nr_band.update({(str(arfcn_item.arfcndl), str(arfcn_item.bschannelbwdl)): tmp_dict})
        
    def check_update_db_nr_band(self, nr_band_update_dict):
        temp_dict = {}
        if self.nr_band.get((str(nr_band_update_dict['arfcndl']), str(nr_band_update_dict['bschannelbwdl'])), None) is not None:
            temp_dict = copy.deepcopy(self.nr_band.get((str(nr_band_update_dict['arfcndl']), str(nr_band_update_dict['bschannelbwdl']))))
            del temp_dict['band']
            del temp_dict['layer']
            del temp_dict['b_bw_l']
        if (self.nr_band.get((str(nr_band_update_dict['arfcndl']), str(nr_band_update_dict['bschannelbwdl'])), None) is None) or \
                (temp_dict != nr_band_update_dict):
            for key in nr_band_update_dict:
                nr_band_update_dict[key] = int(nr_band_update_dict.get(key))
            nr_band_update_dict['market'] = self.market
            obj, created = NRBand.objects.update_or_create(market=nr_band_update_dict['market'], arfcndl=nr_band_update_dict['arfcndl'],
                                                           bschannelbwdl=nr_band_update_dict['bschannelbwdl'], defaults=nr_band_update_dict)
            tmp_dict = {
                'arfcndl': str(obj.arfcndl),
                'bschannelbwdl': str(obj.bschannelbwdl),
                'ssbfrequency': str(obj.ssbfrequency),
                'ssbduration': str(obj.ssbduration),
                'ssboffset': str(obj.ssboffset),
                'ssbperiodicity': str(obj.ssbperiodicity),
                'ssbsubcarrierspacing': str(obj.ssbsubcarrierspacing),
                'band': str(obj.band),
                'layer': str(obj.layer),
                'b_bw_l': F'N{obj.band}-{obj.bschannelbwdl}-{obj.layer}',
            }
            self.nr_band.update({(str(obj.arfcndl), str(obj.bschannelbwdl)): tmp_dict})

    def check_update_db_lte_earfcn_band_bw(self, earfcndl, band, bandwidth, dlonly=False):
        earfcndl, band, bandwidth = int(earfcndl), int(band), int(bandwidth)
        if (self.earfcn_dict.get(str(earfcndl)) is None) or \
                (self.earfcn_dict.get(str(earfcndl)).get('band') != band) or \
                (self.earfcn_dict.get(str(earfcndl)).get('bandwidth') != bandwidth):
            para_dict = {'earfcndl': earfcndl, 'band': band, 'bandwidth': bandwidth}
            obj, created = LTEearfcnBandBWLayer.objects.update_or_create(earfcndl=earfcndl, defaults=para_dict)
            if dlonly or (str(obj.earfcndl) in self.dlonly): layer = 'DlOnly'
            elif str(obj.earfcndl) in self.earfcndl_lb_850: layer = 'LB'
            else: layer = obj.layer
            tmp_dict = {
                F'freq': str(obj.earfcndl),
                F'band': str(obj.band),
                F'bandwidth': str(obj.bandwidth),
                F'layer': F'{layer}',
                F'b_bw_l': F'B{obj.band}-{obj.bandwidth}-{layer}',
                F'B{obj.band}': True,
                F'{obj.bandwidth // 1000}MHz': True,
                F'{layer}': True,
            }
            self.earfcn_dict[str(obj.earfcndl)] = tmp_dict
    
    """
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!:- GS Audit Sheet Process for SW Relese -:!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    """
    
    def get_att_ericsson_enb_gnb_gold_standard_and_suffix_from_excell(self):
        # gs_excell_file = os.path.join(settings.MEDIA_ROOT, 'audit_dir', 'att_gs.xlsx')
        # gs_excell_file = os.path.join(os.path.dirname(__file__), F'att_ericsson_enb_gnb_gold_standard.xlsx')
        gs_excell_file = os.path.join(settings.MEDIA_ROOT, 'audit_file', 'att_gs.xlsx')

        if not os.path.isfile(gs_excell_file): raise Exception(F"Could not find AT&T GS Audit Files.")
        df_gs = pd.read_excel(gs_excell_file, sheet_name='eNB_gNB_Parameters', nrows=None, dtype=str,
                              usecols=['type', 'sw_start', 'sw_end', 'MOC', 'Parameter', 'Suffix', 'Logic', 'GSValue', 'InitialValue', 'Permission'])
        df_gs.Suffix = df_gs.Suffix.str.strip()
        df_gs.Logic = df_gs.Logic.str.strip()
        df_gs = df_gs.replace({np.nan: None, '': None})
        df_gs = df_gs.loc[~(df_gs.type.isnull() | df_gs.sw_start.isnull() | df_gs.sw_end.isnull() | df_gs.MOC.isnull() | df_gs.Parameter.isnull())]
        df_gs = df_gs.loc[(df_gs.sw_start <= self.sw_ver) & (self.sw_ver <= df_gs.sw_end)]
        df_gs.Logic = df_gs.Logic.str.strip()
        df_gs['GSValue'] = df_gs['GSValue'].fillna('')
        df_gs.reset_index(inplace=True, drop=True)
        self.df_gs = df_gs.copy()

        df_gs = pd.read_excel(gs_excell_file, sheet_name='scripts', usecols=['MO', 'MOC', 'Parameter', 'script_type'], dtype=str)
        df_gs = df_gs.loc[(~(df_gs.MO.isnull() | df_gs.MOC.isnull() | df_gs.Parameter.isnull() | df_gs.script_type.isnull()))]
        df_gs.MO = df_gs.MO.str.strip()
        df_gs.MOC = df_gs.MOC.str.strip()
        df_gs.Parameter = df_gs.Parameter.str.strip()
        df_gs.script_type = df_gs.script_type.str.strip()
        df_gs.reset_index(inplace=True, drop=True)
        self.df_script_type = df_gs.copy()

        df_gs = pd.read_excel(gs_excell_file, sheet_name='Referance', usecols=['parameter', 'value'], dtype=str)
        self.revision += '_' + df_gs.loc[(df_gs.parameter == 'Version')].value.iloc[0]

        # Update Parameter based on USID configurations
        self.gs_parameter_update_RATFreqPrio_freqPrioListEUTRA()
        self.gs_parameter_update_CaCellProfileUeCfg_Base_blockedSCellFreqList()

        # df_suffix = pd.read_excel(gs_excell_file, sheet_name='suffix_mapping', usecols=['type', 'Suffix', 'Logic'], dtype=str)
        # df_suffix.Suffix = df_suffix.Suffix.str.strip()
        # df_suffix.replace({np.nan: None, '': None}, inplace=True)
        # df_suffix = df_suffix.loc[~(df_suffix.type.isnull() | df_suffix.Suffix.isnull() | df_suffix.Logic.isnull())]
        # df_suffix.reset_index(inplace=True, drop=True)
        # self.df_suffix = df_suffix.copy()
        #
        # enum_dict
        # df_gs = pd.read_excel(gs_excell_file, sheet_name='enum', nrows=None, dtype=str, usecols=['type', 'MOC', 'Parameter', 'enumRef', 'dict_value'])
        # df_gs.replace({np.nan: None, '': None, ' ': ''}, regex=True, inplace=True)
        # df_gs = df_gs.loc[~(df_gs.MOC.isnull() | df_gs.Parameter.isnull() | df_gs.enumRef.isnull())]
        # self.enum_dict = {F'{row.MOC}.{row.Parameter}': json.loads(row.dict_value) for row in df_gs.itertuples()}
    
    # Update RATFreqPrio--freqPrioListEUTRA parameter based on earfcn defined on given usid
    def gs_parameter_update_RATFreqPrio_freqPrioListEUTRA(self):
        ret_mo_ids = list(set([_.split('=')[-1] for _ in list(set([_ for _ in self.df_gs.MOC.unique() if _.startswith('RATFreqPrio=')]))]))
        fdd_earfcn = [str(i) for i in sorted([int(_) for _ in list(
            self.df_lte_cells.loc[((self.df_lte_cells.cell_type == 'FDD') & (self.df_lte_cells.bw.astype(int) > 3000) &
                                   (self.df_lte_cells.layer != 'DlOnly'))].earfcn.unique())])]
        for ret_id in ret_mo_ids:
            all_gold_val = []
            suffix = ''
            for earfcn in fdd_earfcn:
                for row in self.df_gs.loc[(self.df_gs.MOC == F'RATFreqPrio={ret_id}') & (self.df_gs.Parameter == 'freqPrioListEUTRA')].itertuples():
                    if self.logic.evaluate(row.Logic, cell=earfcn, site='', mo_level='earfcn'):
                        gold_val = json.loads(row.GSValue)
                        gold_val |= {'arfcnValueEUtranDl': earfcn}
                        all_gold_val.append(gold_val)
                        suffix += F' and {earfcn} as {row.Suffix}'
                        break
            mask = ((self.df_gs.MOC == F'RATFreqPrio={ret_id}') & (self.df_gs.Parameter == 'freqPrioListEUTRA'))
            self.df_gs.loc[mask, 'Logic'] = None
            self.df_gs.loc[mask, 'GSValue'] = json.dumps(all_gold_val)
            self.df_gs.loc[mask, 'Suffix'] = suffix[5:] if len(suffix) > 5 else ''
            # self.df_gs.loc[((self.df_gs.MOC == F'RATFreqPrio={ret_id}') &
            #                 (self.df_gs.Parameter == 'freqPrioListEUTRA')), 'Logic'] = None
            # self.df_gs.loc[((self.df_gs.MOC == F'RATFreqPrio={ret_id}') &
            #                 (self.df_gs.Parameter == 'freqPrioListEUTRA')), 'GSValue'] = json.dumps(all_gold_val)
            # self.df_gs.loc[((self.df_gs.MOC == F'RATFreqPrio={ret_id}') &
            #                 (self.df_gs.Parameter == 'freqPrioListEUTRA')), 'Suffix'] = suffix[5:] if len(suffix) > 5 else ''

    # Update {SSBFREQUENCY} CaCellProfileUeCfg=Base--blockedSCellFreqList for given site with DoD2 ssbfrequency if it exists
    def gs_parameter_update_CaCellProfileUeCfg_Base_blockedSCellFreqList(self):
        dod2_ssbfrequency = []
        for site in self.param_dict.get('sites'):
            for cell in self.param_dict.get('sites').get(site).get('cells'):
                cell_get = self.param_dict.get('sites').get(site).get('cells').get(cell).get
                if cell_get('CellType', '') == 'NR' and cell_get(F'DoD2', False):
                    dod2_ssbfrequency.append(cell_get('ssbfrequency'))
        dod2_ssbfrequency = list(set(dod2_ssbfrequency))
        mask = ((self.df_gs.MOC.str.contains('CaCellProfileUeCfg=Base')) & (self.df_gs.Parameter == 'blockedSCellFreqList') &
                (self.df_gs.GSValue == '{SSBFREQUENCY}'))
        self.df_gs.loc[mask, 'GSValue'] = json.dumps(dod2_ssbfrequency)

    # def get_lte_umts_relations_data(self):
    #     freq_list, freq_rel_list = [], []
    #     for site_key in self.sites:
    #         site = self.sites.get(site_key)
    #         nw_mo = site.get_mos_with_parent_moc(parent=site.enb, moc='UtraNetwork')
    #         if len(nw_mo) == 0: continue
    #         for freq_mo in site.get_mos_with_parent_moc(parent=nw_mo[0], moc='UtranFrequency'):
    #             freq_list.append([site.siteid, freq_mo.split('=')[-1], site.get_mo_data(freq_mo).get('arfcnValueUtranDl'), freq_mo, True])
    #         for fdd_mo in site.get_mos_with_parent_moc(parent=site.enb, moc='EUtranCellFDD'):
    #             for mo_rel in site.get_mos_with_parent_moc(parent=fdd_mo, moc='UtranFreqRelation'):
    #                 mo_dict = {_.split('=')[0]: _.split('=')[1] for _ in mo_rel.split(',')}
    #                 full_freq_ref_mo = site.get_first_mo_from_ref_parameter(site.get_mo_data(mo_rel).get('utranFrequencyRef'))
    #                 arfcn = site.get_mo_data(full_freq_ref_mo).get('arfcnValueUtranDl')
    #                 freq_rel_list.append([site.siteid, mo_dict.get('EUtranCellFDD'), mo_dict.get('UtranFreqRelation'), arfcn, mo_rel, True])
    #
    #     self.df_lte_umts_freq = pd.DataFrame(freq_list, columns=['site', 'freq', 'arfcn', 'fdn', 'flag'])
    #     self.df_lte_umts_rel = pd.DataFrame(freq_rel_list, columns=['site', 'cell', 'relid', 'arfcn', 'fdn', 'flag'])
    #     self.df_lte_umts_rel = self.df_lte_umts_rel.merge(self.df_lte_umts_freq[['site', 'arfcn', 'freq']], on=['site', 'arfcn'], how='left')

    # # UMTS Removed
    # # Update UtranFrequency uarfcn_dict
    # temp_dict = {}
    # for arfcn in self.df_lte_umts_freq.arfcn.unique():
    #     arfcn, band = arfcn, '1900'
    #     f_type = 'FEMTO' if arfcn in self.umts_femto else 'MACRO'
    #     for key in self.utran_band_dict.keys():
    #         if key[0] <= int(arfcn) <= key[1]:
    #             band = str(self.utran_band_dict.get(key))
    #             break
    #     temp_dict[arfcn] = {'freq': arfcn, f_type: True, band: True, 'b_bw_l': F'{arfcn}-B{band}-{f_type}', 'USID_FREQ': True}
    # self.param_dict['uarfcn'] = copy.deepcopy(temp_dict)