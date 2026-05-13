import json
import pandas as pd


class GSAuditBase:
    def __init__(self, usid):
        self.usid = usid
        self.logic = self.usid.logic
        self.log = self.usid.log
        self.s_type = str(self.__class__.__name__)[7:]
        self.df_gs = self.usid.df_gs.copy().loc[self.usid.df_gs.type.isin([self.s_type])]
        self.df_gs = self.df_gs[['MOC', 'Parameter', 'Suffix', 'Logic', 'GSValue', 'InitialValue', 'Permission']]
        self.df_gs.reset_index(inplace=True, drop=True)
        self.r_list, self.process_list = [], []
        self.skip_moc = []
        self.air = 0
        self.run_audit_report()

    def generate_audit_report(self): pass
    
    @staticmethod
    def noarmalize_val(site_val):
        if type(site_val) == str:
            if '(' in site_val: return site_val.split()[0]
            else: return '' if site_val.lower() == 'none' else site_val
        else:
            if type(site_val) not in (dict, list) and pd.isnull(site_val): return ''
            if type(site_val) == list:
                for index in range(len(site_val)):
                    if (type(site_val[index]) == dict) and site_val[index].get('qciProfileRef') is not None:
                        if 'ManagedElement' in site_val[index].get('qciProfileRef'):
                            item = site_val[index].get('qciProfileRef').split(',')
                            modified_item = ','.join(item[item.index([_ for _ in item if 'ManagedElement' in _][0]) + 1:])
                            site_val[index]['qciProfileRef'] = modified_item
                    elif type(site_val[index] == str) and 'ManagedElement' in site_val[index]:
                        item = site_val[index].split(',')
                        modified_item = ','.join(item[item.index([_ for _ in item if 'ManagedElement' in _][0]) + 1:])
                        site_val[index] = modified_item
                return site_val
            return site_val

    def compare_values(self, site_val, gs_val):
        # site_val = site.get_mo_para(mo, param)
        site_val_type = type(site_val)
        if gs_val == 'Not_Auditable': return True
        # print(F'{mo}---{param}---{site_val}---{site_val_type}-----------{gs_val}')
        op = 'eq'
        if (type(gs_val) == str) and not (gs_val.startswith('[') or gs_val.startswith('{')):
            if '=' in gs_val: pass
            elif ',' in gs_val: gs_val, op = gs_val.split(','), 'in'
            elif gs_val.count('..') == 1:
                start, end = [int(_) for _ in gs_val.split('..')]
                gs_val, op = [start, end], 'between'
        if site_val_type in (dict, list):
            if (type(gs_val) == str) and (gs_val != ''):
                if "'" in gs_val: gs_val = gs_val.replace("'", '"')
                gs_val = json.loads(gs_val)
        return False if site_val == 'N/F' else self.evaluate_site_value_gs_value(site_val, gs_val, op, site_val_type)
    
    def evaluate_site_value_gs_value(self, site_val, gs_val, op, site_val_type):
        if site_val_type not in (dict, str, list): site_val = str(site_val)
        if op == 'in': return self.noarmalize_val(site_val) in gs_val
        elif op == 'eq':
            param_val_norm = self.noarmalize_val(gs_val)
            site_val_norm = self.noarmalize_val(site_val)
            if (type(site_val_norm) == str) and (type(param_val_norm) == str) and (param_val_norm != '') and \
                    ('ManagedElement' in site_val_norm) and (site_val_norm.endswith(param_val_norm)):
                return True
            elif type(site_val_norm) == list and (sum([type(_) == dict for _ in site_val_norm]) == len(site_val_norm)) and \
                    type(param_val_norm) == list and (sum([type(_) == dict for _ in param_val_norm]) == len(param_val_norm)):
                return set([str(_) for _ in site_val_norm]).difference(set([str(_) for _ in param_val_norm])) == \
                       set([str(_) for _ in param_val_norm]).difference(set([str(_) for _ in site_val_norm]))
            else: return site_val_norm == param_val_norm
        elif op == 'between':
            if site_val in [None, 'None', '']: return False
            site_val_new = int(site_val) if '(' not in site_val else int(site_val.split(' ')[0])
            return True if (site_val_new >= gs_val[0]) and (site_val_new <= gs_val[-1]) else False

    def run_audit_report(self):
        self.generate_audit_report()
        if len(self.r_list) == 0: return
        columns_list = ['OnAir', 'Site', 'MO', 'Parameter', 'CurrentValue', 'GSValue', 'InitialValue', 'Permission', 'Suffix', 'flag']
        df_report = pd.DataFrame(self.r_list, columns=columns_list)
        df_report = df_report.groupby(['Site', 'MO', 'Parameter'], sort=False, as_index=False).head(1)
        df_report['Type'] = self.s_type
        df_report['MOC'] = df_report.MO.str.extract(r'.*,(.*)=[^,=].*').squeeze()
        df_report['Type'] = self.s_type
        if self.s_type == 'LTE':
            df_report.loc[(df_report.MOC == 'RATFreqPrio'), 'Type'] = F'{self.s_type}_RATFreqPrio'
        elif self.s_type in ['LTERelation', 'NRRelation']:
            df_report['Type'] = df_report[['Type', 'MOC']].apply(lambda x: '_'.join(x.astype(str)), axis=1)
        df_report['flag'] = df_report.flag.astype(str)
        self.usid.df_report = pd.concat([self.usid.df_report, df_report], join='inner', ignore_index=True)
        
    def norm_gold_val(self, gold_val):
        if pd.isnull(gold_val) or not (gold_val.startswith('[') or gold_val.startswith('{')) or (gold_val == ''):
            # if ':' in gold_val and gold_val.startswith('t_'): return gold_val[2:]
            return gold_val
        else:
            try: return self.norm_gold_val_json(json.loads(gold_val))
            except: return self.norm_gold_val_json({"XXXXXX": "CHECK GS SHEET"})

    def norm_gold_val_json(self, gold_val):
        if type(gold_val) == dict: return ','.join([F"{key}={self.norm_gold_val_json(gold_val.get(key))}" for key in gold_val])
        elif type(gold_val) == list:
            if sum([type(_) == dict for _ in gold_val]) == 0: return ' '.join([self.norm_gold_val_json(_) for _ in gold_val])
            else: return ';'.join([self.norm_gold_val_json(_) for _ in gold_val])
        else: return str(gold_val)

    @staticmethod
    def split_source_target(instr):
        if '--->' not in instr: return instr.strip(), ''
        source, target = instr[:instr.index('--->')].strip(), instr[instr.index('--->') + 4:].strip()
        return source, target

    def r_list_for_gs_para(self, siteid, mo, s_val, row_gs):
        self.r_list.append([self.air, siteid, mo, row_gs.Parameter, s_val, row_gs.GSValue, row_gs.InitialValue, row_gs.Permission,
                            row_gs.Suffix, self.compare_values(s_val, row_gs.GSValue)])
        self.process_list.append(F'{mo}.{row_gs.Parameter}')
    
    def r_list_for_missing_gs_para(self, siteid, mo, site_val, row_gs):
        self.r_list.append([self.air, siteid, mo, row_gs, site_val, 'GS_Error', '', 'Not Auditable', '', False])
        self.process_list.append(F'{mo}.{row_gs}')
