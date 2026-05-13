import os
import re
import pandas as pd


def read_n_list_items(f, members):
    ret_list = []
    cnt = 0
    while cnt < members:
        line = f.readline()
        if '============================================' in line: cnt = members
        if '>>>' not in line: continue
        line = line.strip().strip(' >>> ')
        line_sp = line.split()
        if line.startswith('Struct'):
            a, b, d_members, c = line_sp
            ret_list.append(read_n_dict_items(f, int(d_members)))
        else:
            ret_list.append(line.split(' =')[1].strip())
        cnt = cnt + 1
    return ret_list


def read_n_dict_items(f, members):
    ret_dict = {}
    cnt = 0
    while cnt < members:
        line = f.readline().strip().strip(' >>> ')
        line_sp = line.split(' =')
        key_val = line_sp[1].strip()
        if (' (' not in key_val) and not key_val.endswith(')') and (len(key_val.split()) > 1): key_val = key_val.split()
        elif ' (' in key_val and key_val.endswith(')'):
            if len(re.match(r'.*\((.*)\)$', key_val).group(1).split()) <= 1: pass
            else: key_val = re.match(r'.*\((.*)\)$', key_val).group(1).split()
        # CLI Update
        # if (' (' not in key_val) and (len(key_val.split()) > 1): key_val = key_val.split()
        # elif ' (' in key_val:
        #     if re.match('.*\((.*)\)$', key_val): key_val = re.match('.*\((.*)\)$', key_val).group(1).split()
        ret_dict[line_sp[0].split('.')[1]] = key_val
        cnt = cnt + 1
    return ret_dict


def parse_dcg_file(infile):
    mo_start = False
    start_site = False
    parsed_dict = None
    # ',SecM=',
    removed_mo_list = [',Fm=', ',BrM=', ',PmEventM=', ',PmEventSigM=', ',Pm=', ',HwInventory=', ',SwInventory=', ',LogM=']
    with open(infile, 'r', encoding='utf-8', errors='ignore') as f:
        while True:
            line = f.readline()
            if line == '': break
            if (start_site == False) & line.startswith('Connected to') & ('MeContext' in line):
                site_id = [_ for _ in line.split('(')[1].split(')')[0].split(',') if 'MeContext' in _][0].split('=')[1]
                parsed_dict = {}
                parsed_dict[site_id] = {}
                start_site = True
            if (start_site == True) & ('Proxy Id' in line):
                if len(line.split()) != 3: continue
                proxy_id = int(line.split()[-1])
                line = f.readline()
                if line.startswith('MO         '):
                    mo_dict = {}
                    mo_dict['Proxy ID'] = proxy_id
                    line_sp = line.split()
                    mo_name = '' if len(line_sp) == 1 else line_sp[1]
                    mo_start = False if len([removed_mos for removed_mos in removed_mo_list if removed_mos in mo_name]) > 0 else True
                if mo_start: f.readline()
            while mo_start:
                line = f.readline()
                line_sp = line.split()
                if '=================================' in line:
                    mo_start = False
                    if len([mosss for mosss in removed_mo_list if mosss in mo_name]) == 0:
                        parsed_dict[site_id][mo_name] = mo_dict
                    continue
                # Reading key/value pair dict items
                if not (line.startswith(' ') | line.startswith('Struct') | line_sp[0].endswith(']')):
                    if len(line_sp) == 1: mo_dict[line_sp[0]] = None
                    else: mo_dict[line_sp[0]] = ' '.join(line_sp[1:])
                # Reading dictionary items
                elif line.startswith('Struct'):
                    _, key, _, members, _, = line_sp
                    mo_dict[key] = read_n_dict_items(f, int(members))

                elif line_sp[0].endswith('[0]'):
                    mo_dict[line_sp[0][:-3]] = []
                elif line_sp[0].endswith(']'):
                    if 'FqBands[' in line_sp[0][-10:-2]: continue
                    if len(line_sp) > 1:
                        if (' (') in line:
                            key_val = ' '.join(line_sp[1:])
                            mo_dict[line_sp[0].split('[')[0]] = re.match(r'.*\((.*)\)$', key_val).group(1).split() if \
                                re.match(r'.*\((.*)\)$', key_val) else line_sp[1:]
                        else:
                            mo_dict[line_sp[0].split('[')[0]] = line_sp[1:]
                    else:
                        members = line_sp[0].split('[')[1].split(']')[0]
                        mo_dict[line_sp[0].split('[')[0]] = read_n_list_items(f, int(members))
    return parsed_dict if parsed_dict else {}


def parse_intmonlog(infile):
    extract_start = False
    start_site = False
    parsed_dict = {}
    with open(infile, 'r', encoding='utf-8', errors='ignore') as f:
        while True:
            line = f.readline()
            if line == '': break
            line = line.strip()
            if (start_site == False) & line.startswith('Connected to') & ('MeContext' in line):
                site_id = [_ for _ in line.split('(')[1].split(')')[0].split(',') if 'MeContext' in _][0].split('=')[1]
                parsed_dict = {}
                parsed_dict[site_id] = {}
                start_site = True
            if start_site & line.startswith('MO        '):
                extract_start = True
                line = f.readline()
            while extract_start:
                line = str(f.readline()).strip()
                if line.startswith('======================================================='): extract_start = False
                else:
                    line_sp = line.split()
                    if parsed_dict[site_id].get(line_sp[0]) is None: parsed_dict[site_id][line_sp[0]] = {}
                    if len(line_sp) == 2:
                        parsed_dict[site_id][line_sp[0]][line_sp[1]] = None
                    if len(line_sp) == 3:
                        parsed_dict[site_id][line_sp[0]][line_sp[1]] = line_sp[2]
                    if len(line_sp) > 3:
                        parsed_dict[site_id][line_sp[0]][line_sp[1]] = ' '.join(line_sp[2:])
    return parsed_dict


def parse_rnclog(infile):
    extract_start = False
    start_site = False
    parsed_dict = {}
    with open(infile, 'r', encoding='utf-8', errors='ignore') as f:
        while True:
            line = f.readline()
            if line == '': break
            line = line.strip()
            if (start_site == False) & line.startswith('Connected to') & ('MeContext' in line):
                site_id = [_ for _ in line.split('(')[1].split(')')[0].split(',') if 'MeContext' in _][0].split('=')[1]
                sc_mo = line.split('(')[1].split(')')[0] + ',SystemConstants=1'
                parsed_dict = {site_id: {sc_mo: {}}}
                start_site = True
            if start_site & line.startswith('coli>/fruacc/lhsh 000100 /cm/sysconread all'):
                extract_start = True
            while extract_start:
                line = str(f.readline()).strip()
                if line.startswith('======================================================='): extract_start = False
                else:
                    line_sp = line.split()
                    if len(line_sp) == 3 and len(line_sp[1]) > 2:
                        parsed_dict[site_id][sc_mo][line_sp[1][1:-1]] = line_sp[2]
    return parsed_dict


def parse_showall_file(infile, mo_filter=None):
    mo_start = False
    start_site = False
    removed_mo_list = ['Fm', 'BrM', 'PmEventM', 'PmEventSigM', 'PmEventSigM', 'Pm', 'SecM', 'HwInventory', 'SwInventory', 'SctpAssociation']
    if mo_filter is None: removed_mo_list = []
    else: removed_mo_list = mo_filter
    mo_name = ''
    mo_par_list = []
    excluded_lines = []
    with open(infile, 'r', encoding='utf-8', errors='ignore') as f:
        while True:
            line = f.readline().rstrip('\n')
            if line.strip() == '': continue
            if line.startswith('Log close'): break
            if (start_site is False) & line.startswith('>show all verbose ManagedElement='):
                start_site = True
            if (start_site is True) & line.strip()[0].isupper() & ('=' in line):
                sps = ('' if re.search(r'\s+', line) is None else ' ' * re.search(r'\s+', line).end()) + '    '
                line = line.strip()
                mo_name = line.rsplit('=', 1)[0]
                mo_name_id = line.rsplit('=', 1)[1]
                mo_start = False if mo_name in removed_mo_list else True
                if (mo_name == 'ENodeBFunction') or (mo_name == 'GNBDUFunction') or (mo_name == 'GNBCUCPFunction') or \
                        (mo_name == 'GNBCUUPFunction') or (mo_name == 'ENodeBFunction'):
                    removed_mo_list = []
                removed_mo_list.append(mo_name)
                line = f.readline().rstrip('\n')
            if mo_start:
                if line.startswith(sps):
                    excluded_lines.append([mo_name, mo_name_id, line])
                    continue
                line = line.strip()
                line_sp = []
                if ('<deprecated>' in line) or ('<read-only>' in line) or ('<obsolete>' in line) or ('<preliminary>' in line):
                    excluded_lines.append([mo_name, mo_name_id, line, None])
                    continue
                if '=' in line: line_sp = line.split('=', 1)
                elif '[' in line: line_sp = line.split('[', 1)
                else: line_sp = line.split(' ', 1)

                if len(line_sp) > 1: mo_par_list.append([mo_name, mo_name_id, line_sp[0], line_sp[1]])
                elif len(line_sp) == 1: mo_par_list.append([mo_name, mo_name_id, line_sp[0], None])
                else: excluded_lines.append([mo_name, mo_name_id, line])
    df_data = pd.DataFrame(mo_par_list, columns=['moc', 'moid', 'parameter', 'value'])
    df_data = df_data.drop_duplicates(subset=['moc', 'parameter'])
    df_remove = pd.DataFrame(excluded_lines)
    data = {'showall': df_data.copy(), 'showall_removed': df_remove}
    return data


def parse_file(infile):
    basename = os.path.basename(infile)
    if basename.endswith('dcg_k.log'): return parse_dcg_file(infile)
    elif basename.startswith('intmomlog'): return parse_intmonlog(infile)
    elif basename.startswith('rnclog.txt'): return parse_rnclog(infile)
    else: return {}
