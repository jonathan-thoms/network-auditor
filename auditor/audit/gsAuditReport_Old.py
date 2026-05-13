import os
import pandas as pd


def highlight_even_row(*, row) -> list:
    return ['background-color: lightgreen; ' if _ % 2 == 1 else 'background-color: ivory' for _ in range(len(row))]
    #     border: 1px solid


def gs_audit_report_color_rows(*, row) -> list:
    if row['flag'] in ['True', 'TRUE', True]:
        return ['' for _ in row]
    else:
        if row['GSValue'].startswith('GS_Error'):
            return ['background-color: red; color: white; border: 2px solid green' for _ in row]
        elif row['Permission'].lower().startswith('global'):
            return ['background-color: coral' for _ in row]
        elif row['Permission'].lower().startswith('local'):
            return ['background-color: cyan' for _ in row]
        elif row['Permission'].lower().startswith('not auditable'):
            return ['background-color: gray' for _ in row]
        else:
            return ['background-color: crimson' for _ in row]


class GSAuditReport:
    def __init__(self, usid, gs_admin=False):
        self.usid = usid
        self.audit_file = os.path.join(self.usid.outdir, F'{self.usid.site_id}_GS_Report.xlsx')
        df_temp = self.usid.df_report.copy(deep=True)
        
        if len(df_temp.index) > 0:
            wb_final = pd.ExcelWriter(self.audit_file, engine='openpyxl')
            df_temp = df_temp[['Site', 'MO', 'MOC', 'Type', 'Parameter', 'CurrentValue', 'GSValue', 'InitialValue', 'Permission', 'Suffix', 'flag']]
            df_temp.MO = df_temp.MO.str.extract(r'.*,ManagedElement=\w+,(.*)').squeeze()
            # Complete Report Sheet
            df = df_temp.style.apply(lambda x: highlight_even_row(row=x))
            df = df.apply(lambda x: gs_audit_report_color_rows(row=x), axis=1)
            df.to_excel(wb_final, sheet_name='Audit_Report', index=False)
            wb_final.sheets['Audit_Report'].auto_filter.ref = wb_final.sheets['Audit_Report'].calculate_dimension()
            wb_final.sheets['Audit_Report'].auto_filter.enable = True
            # GS_Error
            if gs_admin:
                df = df_temp.loc[(~df_temp.flag) & (df_temp.GSValue != 'GS_Error')]
                if len(df.index) > 0:
                    df = df.style.apply(lambda x: highlight_even_row(row=x))
                    df = df.apply(lambda x: gs_audit_report_color_rows(row=x), axis=1)
                    df.to_excel(wb_final, sheet_name='GS_Delta', index=False)
                    wb_final.sheets['GS_Delta'].auto_filter.ref = wb_final.sheets['GS_Delta'].calculate_dimension()
                    wb_final.sheets['GS_Delta'].auto_filter.enable = True
                df = df_temp.loc[df_temp.GSValue == 'GS_Error']
                if len(df.index) > 0:
                    df = df.style.apply(lambda x: highlight_even_row(row=x))
                    df = df.apply(lambda x: gs_audit_report_color_rows(row=x), axis=1)
                    df.to_excel(wb_final, sheet_name='GS_Error', index=False)
                    wb_final.sheets['GS_Error'].auto_filter.ref = wb_final.sheets['GS_Error'].calculate_dimension()
                    wb_final.sheets['GS_Error'].auto_filter.enable = True
            wb_final.close()
        if gs_admin:
            wb_para = pd.ExcelWriter(os.path.join(self.usid.outdir, F'{self.usid.site_id}_Logic.xlsx'), engine='openpyxl')
            para_dict = {'USID': 'para', 'SITE': 'sites', 'CELL': 'cells', 'EARFCN': 'earfcn', 'UARFCN': 'uarfcn', 'ARFCN': 'ssbfreq'}
            # 'NR_CELL': 'nr_cells',
            df_temp = pd.DataFrame([])
            for sheet in para_dict.keys():
                if sheet == 'USID':
                    df_temp = pd.DataFrame([self.usid.param_dict.get(para_dict[sheet], {})])
                elif sheet == 'SITE':
                    df_temp = pd.DataFrame([self.usid.param_dict.get(para_dict[sheet]).get(site).get('para')
                                            for site in self.usid.param_dict.get(para_dict[sheet], {}).keys()])
                elif sheet == 'CELL':
                    temp_list = []
                    for site in self.usid.param_dict.get('sites').keys():
                        for cell in self.usid.param_dict.get('sites').get(site).get(para_dict[sheet], {}).keys():
                            temp_list.append(self.usid.param_dict.get('sites').get(site).get(para_dict[sheet]).get(cell))
                    df_temp = pd.DataFrame(temp_list)
                elif sheet in ['EARFCN', 'UARFCN', 'ARFCNNR']:
                    temp_list = []
                    for key in self.usid.param_dict.get(para_dict[sheet], {}).keys():
                        tmp = self.usid.param_dict.get(para_dict[sheet], {}).get(key)
                        tmp['freq'] = key
                        temp_list.append(tmp)
                    df_temp = pd.DataFrame(temp_list)
                if len(df_temp.index) > 0:
                    df_temp.columns = df_temp.columns.astype(str)
                    df_temp = df_temp.add_prefix('_')
                    df_temp = df_temp.style.apply(lambda x: highlight_even_row(row=x))
                    df_temp.to_excel(wb_para, sheet_name=sheet, index=False)
                    wb_para.sheets[sheet].auto_filter.ref = wb_para.sheets[sheet].calculate_dimension()
                    wb_para.sheets[sheet].auto_filter.enable = True
            para_dict = {'lte_freq': self.usid.df_lte_freq, 'lte_rel': self.usid.df_lte_rel, 'lte_crel': self.usid.df_lte_crel,
                         # 'lte_umts_freq': self.usid.df_lte_umts_freq, 'lte_umts_rel': self.usid.df_lte_umts_rel,
                         'lte_nr_freq': self.usid.df_lte_nr_freq, 'lte_nr_rel': self.usid.df_lte_nr_rel, 'lte_nr_crel': self.usid.df_lte_nr_crel,
                         'nr_freq': self.usid.df_nr_freq, 'nr_rel': self.usid.df_nr_rel, 'nr_crel': self.usid.df_nr_crel}
            for sheet in para_dict.keys():
                df_temp = para_dict[sheet].copy(deep=True)
                if len(df_temp.index) > 0:
                    df_temp.columns = df_temp.columns.astype(str)
                    df_temp = df_temp.style.apply(lambda x: highlight_even_row(row=x))
                    df_temp.to_excel(wb_para, sheet_name=sheet, index=False)
                    wb_para.sheets[sheet].auto_filter.ref = wb_para.sheets[sheet].calculate_dimension()
                    wb_para.sheets[sheet].auto_filter.enable = True
            # if save_flag: wb_para.save()
            wb_para.close()
