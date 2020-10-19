# Pam June 2020
# Parsing plazi database records
# A subpart of the XML structure is mods namespace describe here: http://www.loc.gov/standards/mods/v3/

import sys
import codecs
import os
import re
from optparse import OptionParser
from datetime import datetime
from lxml import etree
from unidecode import unidecode


def build_time_collections():
    file_list = os.listdir(data_dir)
    dd_dic = dict()
    ct_dic = dict()
    cnt=0
    for f in file_list:
        if not f.endswith('xml'): continue
        file_name = data_dir + '/' + f
        xmlstr = get_file_content(file_name)
        try:
            root = etree.fromstring(xmlstr)
            dt1 = root.get('docDate')
            if dt1 not in dd_dic: dd_dic[dt1] = []
            dd_dic[dt1].append(f)

            tm = int(root.get('checkinTime')) / 1000
            dt2o = datetime.fromtimestamp(tm)
            dt2 = dt2o.strftime("%Y")
            if dt2 not in ct_dic: ct_dic[dt2] = []
            ct_dic[dt2].append(f)

            cnt += 1
            if cnt % 1000 == 0: print('processing ' + str(cnt) + ' / ' + str(len(file_list)) , flush=True)
        except:
            print('ERROR with ' + file_name, flush=True)

    print('processed  ' + str(cnt) + ' / ' + str(len(file_list)) )
    os.makedirs(output_dir, exist_ok=True)

    for k in sorted(dd_dic):
        fname = output_dir + '/doc-date-' + k
        with open(fname, 'w') as out:
            out.write('\n'.join(dd_dic[k]) + '\n')

    for k in sorted(ct_dic):
        fname = output_dir + '/checkin-time-' + k
        with open(fname, 'w') as out:
            out.write('\n'.join(ct_dic[k]) + '\n')

    print('end')


def do_it(file_list):

    #file_list = os.listdir(data_dir)
    full_path_dict = dict()
    full_elem_dict = dict()
    cnt=0
    for f in file_list:
        if not f.endswith('xml'): continue
        file_name = data_dir + '/' + f
        xmlstr = get_file_content(file_name)
        try:
            root = etree.fromstring(xmlstr)
            path_list=[simplify_ns('/' + root.tag)]
            build_path_list('', root, path_list)
            cnt += 1
            if cnt % 1000 == 0: print('processing ' + str(cnt) + ' / ' + str(len(file_list)) , flush=True)
            for pth in set(path_list):
                elem_list = pth.split('/')
                for el in elem_list:
                    if el=='' : continue
                    if el not in full_elem_dict: full_elem_dict[el] = {'cnt':0, 'samples': []}
                    value = full_elem_dict[el]
                    value['cnt'] = value['cnt'] + 1
                    if len(value['samples'])<3 : value['samples'].append(f)
                if pth not in full_path_dict:
                    full_path_dict[pth]= { 'cnt':0, 'samples': [], 'dup_list': get_duplicates(elem_list) }
                value = full_path_dict[pth]
                value['cnt']=value['cnt']+1
                if len(value['samples'])<1 : value['samples'].append(f)
        except:
            print('ERROR with ' + file_name, flush=True)

    print('processed  ' + str(cnt) + ' / ' + str(len(file_list)) )

    print('------')
    sorted_dict =  sorted_by_frequency(full_path_dict)
    for item in sorted_dict: print('path', item[1]['cnt'], len(item[1]['dup_list']), item[1]['dup_list'], item[0], item[1]['samples'])
    print('------')
    print('path set :' + str(len(full_path_dict)), flush=True)

    print('------')
    dup_dict = dict()
    for k in full_path_dict:
        for dup in full_path_dict[k]['dup_list']:
            if dup not in dup_dict: dup_dict[dup] = 0
            dup_dict[dup] += full_path_dict[k]['cnt']
    for it in sorted(dup_dict.items(), key=lambda item: item[1]):
        print('dupl', it[0], it[1])
    print('------')
    print('dup dict : ' + str(len(dup_dict)))
    print('------')


    print('------')
    sorted_dict = sorted_by_frequency(full_elem_dict)
    for item in sorted_dict: print('elem', item[1]['cnt'], item[0], item[1]['samples'])
    print('------')
    print('elem set :' + str(len(full_elem_dict)), flush=True)

    print('------')


def get_duplicates(some_list):
    seen = {}
    dupes = []
    for el in some_list:
        if el not in seen: seen[el] = 1
        else:
            if seen[el] == 1: dupes.append(el)
            seen[el] += 1
    return sorted(dupes)

def sorted_by_frequency(dict):
    return sorted(dict.items(), key=lambda item: item[1]['cnt'])

def sorted_by_key(dict):
    return sorted(dict.items(), key=lambda item: item[0])


def build_path_list(ancestors, parent_el, path_list):
    ancestors = ancestors + '/' + simplify_ns(parent_el.tag)
    for el in parent_el:
        path_list.append(ancestors + '/' + simplify_ns(el.tag))
        build_path_list(ancestors, el, path_list)

def simplify_ns(tag):
    if tag.startswith('{http://www.loc.gov/mods/v3}'):
        return 'mods:' + tag[28:]
    return tag

def get_file_content(name):
	f = open(name,'r')
	f_text = f.read()
	f.close()
	return f_text

def get_collection(name):
    str = get_file_content(output_dir + '/' + name)
    return str.split()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# globals
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

data_dir = '/Users/pam/Downloads/some_plazi'
data_dir = '/Users/pam/Downloads/plazi'
data_dir = '/Users/pam/Downloads/guido'
output_dir = './time_collections'
#coll_name = 'doc-date-2020'
#coll_name = 'checkin-time-2020'
#coll_name = 'full-set'

if __name__ == '__main__':
    #build_time_collections()
    coll_name = sys.argv[1]
    file_names = get_collection(coll_name)
    print('Analyzing collection ' + coll_name)
    do_it(file_names)
