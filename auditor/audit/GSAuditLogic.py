import pandas as pd
from .__init__ import (__gs_market__)


class GSAuditLogic:
    def __init__(self, op_dict: dict):
        self.bool_dict = {True: True, False: False}
        self.op_dict = op_dict
        self.usid_level_vars = (['multiCarrier', 'EMBMS_designed_area', 'LTE_SA_Colo', 'NR_MB+_n77_Colo',
                                 'SA__and__NR_MB+_n77G___and__DoD2'] +
                                [F'market_{_}' for _ in __gs_market__])
        self.site_level_vars = (
                ['G1', 'G2', 'G3', 'G4', 'MSMM', 'TMBB',  'Pre-Production', 'Post-Production',
                 'UlCoMP', 'IDLe', 'MMBB', 'hicap', 'GPS', 'PTP', 'PTP_FREQ', 'PTP_TIME',
                 'IPV6', 'IPv4', 'PSHO', 'AASFDD', 'InterENBCA',
                 'mRBS', 'Radio2203', 'AIR1641', 'MultiCabinet', 'NRULCAHB', 'FirstNetHiCap',
                 'DaylightSavingMarket', '10_to_12_n77_Cells'] +
                ['s__=1cells'] +
                [F's__>{val}cells' for val in [1, 3, 6, 9, 12, 18]] +
                [F's__<={val}cells' for val in [1, 3, 6, 9, 12, 18]]
        )

    def get_dict_val(self, item, cell, site, mo_level=None):
        level, flip = ('cell', False) if cell is not None else ('site', False)
        ret_bool = False
        if type(item) == str:
            if item.startswith('non_'): item, flip = item[4:], True
            if item.endswith('_SITE'): item, level = item[:-5], 'site'
            elif item.endswith('_USID'): item, level = item[:-5], 'usid'
            elif item in self.site_level_vars and (site is not None): level = 'site'
            elif item in self.usid_level_vars: level = 'usid'

        if level == 'usid':
            ret_bool = self.op_dict.get('para').get(item, self.bool_dict.get(item, False))
        elif level == 'site':
            ret_bool = self.op_dict.get('sites').get(site).get('para').get(item, self.bool_dict.get(item, False))
            if (mo_level == 'site') and (ret_bool is False):
                ret_bool = max([self.op_dict['sites'][site]['cells'][_].get(item, self.bool_dict.get(item, False)) for _ in
                                self.op_dict['sites'][site]['cells'].keys()])
        elif mo_level == 'cell' and cell is not None:
            ret_bool = self.op_dict.get('sites').get(site).get('cells').get(cell, {}).get(item, self.bool_dict.get(item, False))
        elif mo_level in ['earfcn', 'uarfcn', 'ssbfreq']:
            ret_bool = self.op_dict.get(mo_level).get(cell).get(item, self.bool_dict.get(item, False))
        else:
            if cell is not None:
                ret_bool = self.op_dict.get('sites').get(site).get('cells').get(cell, {}).get(item, self.bool_dict.get(item, False))
                # ret_bool = self.op_dict.get('sites').get(site).get('cells').get(cell).get(item, self.bool_dict.get(item, False))
        return not ret_bool if flip is True else ret_bool

    def calculate_exp(self, op, left, right, cell=None, site=None, mo_level=None):
        if op == 'or' or op == '|':
            return self.get_dict_val(left, cell, site, mo_level) or self.get_dict_val(right, cell, site, mo_level)
        elif op == 'and' or op == '&':
            return self.get_dict_val(left, cell, site, mo_level) and self.get_dict_val(right, cell, site, mo_level)

    def get_op_val(self, expression, start):
        ret = ''
        while (start < len(expression)) and (expression[start] not in (' ', ')', '(')):
            ret = ret + expression[start]
            start += 1
        return ret, start

    def evaluate(self, expression, cell=None, site=None, mo_level=None):
        # print(F'expression:"{expression}" -- cell:{cell} -- site:{site} -- mo_level:{mo_level}')
        if pd.isnull(expression) or expression.strip() == '': return True
        expression = expression.strip()
        operator = []
        values = []
        index = 0
        while index < len(expression):
            if expression[index] == ' ':
                index += 1
            elif expression[index] == '(':
                operator.append(expression[index])
                index += 1
            elif expression[index] == ')':
                try:
                    while len(operator) > 0 and operator[-1] != '(':
                        op = operator.pop()
                        left = values.pop()
                        right = values.pop()
                        values.append(self.calculate_exp(op, left, right, cell, site, mo_level))
                    if len(operator) > 0:
                        operator.pop()
                except IndexError:
                    print(f"Syntax Error in Logic Expression: '{expression}'")
                    return False
                index += 1
            else:
                op_val, index = self.get_op_val(expression, index)
                if op_val.lower() in ('and', 'or', '|', '&'): operator.append(op_val.lower())
                elif op_val != '': values.append(op_val)
        
        try:
            while len(operator) != 0:
                op = operator.pop()
                left = values.pop()
                right = values.pop()
                values.append(self.calculate_exp(op, left, right, cell, site, mo_level))
        except IndexError:
            print(f"Syntax Error in Logic Expression: '{expression}'")
            return False
            
        return self.get_dict_val(values[0], cell, site, mo_level) if len(values) >= 1 else None
