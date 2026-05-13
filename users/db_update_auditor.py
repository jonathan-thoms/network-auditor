import sys
import os
import pandas as pd
from django.db import transaction
from auditor.models import AuditSoftware, AuditMarket, LTEBandBWLayer, LTEearfcnBandBWLayer, LTECAPair, UMTSBand, NRBand
from common_func.custom_log import Custom_Log


class DBUpdateAuditor:
    def __init__(self, db_update_file: str, custom_log: Custom_Log):
        self.db_update_file = pd.ExcelFile(db_update_file)
        self.custom_log = custom_log
        self.status = False
        try:
            self.load_auditor_sw()
            self.load_auditor_market()
            self.load_lte_band_bwlayer()
            self.load_lte_earfcn_band_bw_layer()
            self.load_lte_ca_pair()
            self.load_umts_band()
            self.load_nr_band()
            self.custom_log.log.info(F'Activity Successful!!!')
            self.status = True
        except Exception as e:
            self.custom_log.log.info(F'Error: {e}')
            self.custom_log.log.info(F'Activity Failed!!!')
            self.db_update_file.close()
        self.db_update_file.close()
    def data_process_form_excell(self, sheets_name: str):
        df_sheet = pd.DataFrame([])
        if sheets_name in self.db_update_file.sheet_names:
            df_sheet = self.db_update_file.parse(sheets_name).astype(str)
            if len(df_sheet.index):
                df_sheet = df_sheet.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df_sheet

    @transaction.atomic
    def load_auditor_sw(self):
        table_name = 'AuditSoftware'
        df = self.data_process_form_excell(sheets_name=table_name)
        if len(df.index) > 0:
            df = df[['sw']]
            df['sw'] = df.sw.astype(str)
            for index, row in df.iterrows():
                o_d = row.to_dict()
                obj, created = AuditSoftware.objects.update_or_create(sw=o_d.get("sw"), defaults=o_d)
                self.custom_log.log.info(F'{table_name}--{created}---{obj}')
            self.custom_log.log.info(F'{table_name} Updated Complete!!!')
        else:
            self.custom_log.log.info(F'--------------> No Data for {table_name} <--------------')

    @transaction.atomic
    def load_auditor_market(self):
        table_name = 'AuditMarket'
        df = self.data_process_form_excell(sheets_name=table_name)
        if len(df.index) > 0:
            df = df[['market', 'TimeZone']]
            df['market'] = df.market.astype(str)
            df['TimeZone'] = df.TimeZone.astype(str)
            for index, row in df.iterrows():
                o_d = row.to_dict()
                obj, created = AuditMarket.objects.update_or_create(market=o_d.get("market"), defaults=o_d)
                self.custom_log.log.info(F'{table_name}--{created}---{obj}')
            self.custom_log.log.info(F'{table_name} Updated Complete!!!')
        else:
            self.custom_log.log.info(F'--------------> No Data for {table_name} <--------------')

    @transaction.atomic
    def load_lte_band_bwlayer(self):
        table_name = 'LTEBandBWLayer'
        df = self.data_process_form_excell(sheets_name=table_name)
        if len(df.index) > 0:
            df = df[['band', 'bandwidth', 'layer']]
            df['band'] = df.band.astype(int)
            df['bandwidth'] = df.bandwidth.astype(int)
            for index, row in df.iterrows():
                o_d = row.to_dict()
                obj, created = LTEBandBWLayer.objects.update_or_create(band=o_d.get("band"), bandwidth=o_d.get("bandwidth"), defaults=o_d)
                self.custom_log.log.info(F'{table_name}--{created}---{obj}')
            self.custom_log.log.info(F'{table_name} Updated Complete!!!')
        else:
            self.custom_log.log.info(F'--------------> No Data for {table_name} <--------------')

    @transaction.atomic
    def load_lte_earfcn_band_bw_layer(self):
        table_name = 'LTEearfcnBandBWLayer'
        df = self.data_process_form_excell(sheets_name=table_name)
        if len(df.index) > 0:
            df = df[['earfcndl', 'band', 'bandwidth']]
            df['earfcndl'] = df.earfcndl.astype(int)
            df['band'] = df.band.astype(int)
            df['bandwidth'] = df.bandwidth.astype(int)
            for index, row in df.iterrows():
                o_d = row.to_dict()
                obj, created = LTEearfcnBandBWLayer.objects.update_or_create(earfcndl=o_d.get('earfcndl'), defaults=o_d)
                self.custom_log.log.info(F'{table_name}--{created}---{obj}')
            self.custom_log.log.info(F'{table_name} Updated Complete!!!')
        else:
            self.custom_log.log.info(F'--------------> No Data for {table_name} <--------------')

    @transaction.atomic
    def load_lte_ca_pair(self):
        table_name = 'LTECAPair'
        df = self.data_process_form_excell(sheets_name=table_name)
        if len(df.index) > 0:
            df = df[['pcell', 'scell']]
            for index, row in df.iterrows():
                o_d = row.to_dict()
                obj, created = LTECAPair.objects.update_or_create(pcell=o_d.get('pcell'), scell=o_d.get('scell'), defaults=o_d)
                self.custom_log.log.info(F'{table_name}--{created}---{obj}')
            self.custom_log.log.info(F'{table_name} Updated Complete!!!')
        else:
            self.custom_log.log.info(F'--------------> No Data for {table_name} <--------------')

    @transaction.atomic
    def load_umts_band(self):
        # UMTSBand
        table_name = 'UMTSBand'
        df = self.data_process_form_excell(sheets_name=table_name)
        if len(df.index) > 0:
            df = df[['start', 'end', 'band']]
            for index, row in df.iterrows():
                o_d = row.to_dict()
                obj, created = UMTSBand.objects.update_or_create(start=o_d.get('start'), end=o_d.get('end'), defaults=o_d)
                self.custom_log.log.info(F'{table_name}--{created}---{obj}')
            self.custom_log.log.info(F'{table_name} Updated Complete!!!')
        else:
            self.custom_log.log.info(F'--------------> No Data for {table_name} <--------------')


    @transaction.atomic
    def load_nr_band(self):
        table_name = 'NRBand'
        df = self.data_process_form_excell(sheets_name=table_name)
        if len(df.index) > 0:
            df = df[['market', 'arfcndl', 'bschannelbwdl', 'ssbfrequency', 'ssboffset', 'ssbduration', 'ssbperiodicity', 'ssbsubcarrierspacing']]
            for index, row in df.iterrows():
                o_d = row.to_dict()
                obj, created = NRBand.objects.update_or_create(market=o_d['market'], arfcndl=o_d['arfcndl'], bschannelbwdl=o_d['bschannelbwdl'],
                                                               defaults=o_d)
                self.custom_log.log.info(F'{table_name}--{created}---{obj}')
            self.custom_log.log.info(F'NRBand Updated Complete!!!')
