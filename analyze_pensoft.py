# Pam June 2020
# Parsing pensoft database records
# A subpart of the XML structure is mods namespace describe here: http://www.loc.gov/standards/mods/v3/

import sys
import codecs
import os
import re
from optparse import OptionParser
from datetime import datetime
from lxml import etree
from unidecode import unidecode

def do_it(file_list):

    #file_list = os.listdir(data_dir)
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
            if cnt % 100 == 0: print('processing ' + str(cnt) + ' / ' + str(len(file_list)) , flush=True)
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
        except Exception as e:
            print('ERROR with ' + file_name, flush=True)
            print(e)

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
    for k in tag2text_list:
        print("=======================================")
        print("tag", k, len(tag2text_list[k]), "occurences")
        print("=======================================")
        count=0
        for txt in tag2text_list[k]:
            count+=1
            if count>10: continue
            print('tagtext', k)
            print(txt, flush=True)
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

def handle_examples(el, tag):
    if tag == "taxpub:taxon-treatment": return  # ignored, contains everything
    if tag not in tag2text_list: 
        tag2text_list[tag] = list()
    target_list = tag2text_list[tag]
    #if len(target_list) < 10:
    embedded_text = etree.tostring(el, method = "text", encoding="utf-8").strip()
    target_list.append(embedded_text.decode())

def build_path_list(ancestors, parent_el, path_list):
    simple_tag = simplify_ns(parent_el.tag)
    if simple_tag.startswith('taxpub:'):
        handle_examples(parent_el, simple_tag)
    ancestors = ancestors + '/' + simple_tag
    for el in parent_el:
        if isinstance(el, etree._Comment): continue
        if isinstance(el, etree._XSLTProcessingInstruction): continue
        if isinstance(el, etree._ProcessingInstruction): continue
        path_list.append(ancestors + '/' + simplify_ns(el.tag))
        build_path_list(ancestors, el, path_list)

def simplify_ns(tag):
    if tag.startswith('{http://www.loc.gov/mods/v3}'):
        return 'mods:' + tag[28:]
    elif tag.startswith('{http://www.w3.org/1998/Math/MathML}'):
        return 'math:' + tag[36:]
    elif tag.startswith('{http://www.plazi.org/taxpub}'):
        return 'taxpub:' + tag[29:]
    return tag

def get_file_content(name):
    f = open(name,'r')
    first_line = f.readline()
    if "encoding" in first_line:
        #print("Ignoring first line of", name)
        f_text = f.read()
    else:
        f_text = first_line + f.read()
    f.close()
    return f_text


def test1():
    xmlstr="""<root><p>aaaa<q>bbbb</q>cccc</p><p2><p3>hey</p3></p2></root>"""
    root = etree.fromstring(xmlstr)
    #etree.strip_tags(root,'xref')
    #etree.strip_elements(root, 'sup', with_tail=False)
    #stuff=handle_paragrap('1111',root.find('p'))
    node = root.find('p')
    x = etree.tostring(node,  pretty_print = True, method = "text")
    print(x.decode())
    print(node.text)
	#stuff=handle_xxx(root.find('p'))
	#print(json.dumps(stuff, sort_keys=True, indent=2))


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# globals
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

data_dir = './data.pensoft'
output_dir = './out.pensoft'

if __name__ == '__main__':

    #test1()
    #sys.exit()

    tag2text_list = dict()
    full_path_dict = dict()
    full_elem_dict = dict()

    file_names = os.listdir(data_dir)
    print('Analyzing collection of', len(file_names), "items")
    do_it(file_names)
    print("End")
