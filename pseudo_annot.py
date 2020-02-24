import random
import json

def get_fld_subfld_for(cnt, prop_name):
    tag = cnt.get('tag').lower()
    fld = 'text'
    if tag == 'fig': fld = 'Fig'
    if tag == 'table': fld = 'Table'
    prop = prop_name.lower()
    sub_fld = None
    if prop == 'caption': sub_fld = 'Caption'
    if prop == 'footer': sub_fld = 'Footer'
    if prop == 'table_values': sub_fld = 'Content'
    return fld, sub_fld

def get_pseudo_annotations_for_text(cnt, prop_name):
    sometext = cnt.get(prop_name)
    if sometext is None: return list()
    id = cnt.get('id')
    passages = split_text(sometext)
    #print('nb.psg: ' + str(len(passages)))
    annotations = list()
    offset=0
    fld, sub_fld = get_fld_subfld_for(cnt, prop_name)
    for p in passages:
        #print('> psg: ' + p)
        annotations.extend(get_annotations(p, offset, id, fld, sub_fld))
        offset = offset + len(p) + 2
    return annotations

def get_pseudo_annotations_for_cell(cnt, max):
    values = cnt.get('table_values')
    if values is None: return list()
    id = cnt.get('id')
    words = []
    for row in values:
        for col in row:
            words.extend([str(w) for w in col.split(' ')])
    annotations = list()
    somewords = random.sample(words, random.randint(1,max))
    for w in somewords:
        psg = "fake passage"  # ignored
        offset = 3523523535   # ignored
        annot = build_annot(w, w, psg, offset, id, 'Table', 'Content')
        annotations.append(annot)
    return annotations


def split_text(txt):
    return txt.split('. ')

def get_annotations(psg, offset, id, fld, sub_fld):
    annotations = list()
    words = psg.split(' ')
    word_cnt = len(words)
    if word_cnt < 3: return list()
    #print('nb.words: ' + str(word_cnt))

    max_annot = int(word_cnt / 3)
    if max_annot > 3: max_annot = 3
    sample = random.sample( range(0, word_cnt-1) , max_annot)
    sample.sort()
    #print(sample)
    w_offset=0
    w_idx=0
    for w in words:
        if w_idx in sample:
            annot = build_annot(w, w_offset, psg, offset, id, fld, sub_fld)
            annotations.append(annot)
        w_offset = w_offset + len(w) + 1
        w_idx = w_idx + 1
    return annotations

def build_annot(w, w_offset, psg, offset, id, fld, sub_fld):
    annot=dict()
    annot['type']='TYP:MyType'
    annot['concept_source']='SRC:MySrc'
    annot['version']='28-10-2019'
    cpt_id = str(random.randint(10000,99999))
    annot['concept_id']='ID:' + cpt_id
    annot['special_id']='SPID:special'
    annot['concept_form']=w
    annot['preferred_term']=w
    annot['passage']=psg
    annot['content_id']=id
    annot['concept_offset']=w_offset
    annot['concept_offset_in_section'] = -1 # unused by me
    annot['concept_length']=len(w)
    annot['passage_offset']=offset
    annot['passage_length']=len(psg)
    annot['field'] = fld
    if sub_fld is not None: annot['subfield'] = sub_fld
    return annot




if __name__ == '__main__':
    print('--------------------')
    cnt={'id': '1.2.3.4', 'tag': 'p', 'text': 'Hello my name is jack' }
    annots=get_pseudo_annotations_for_text(cnt, 'text')
    print(json.dumps(annots, indent=4, sort_keys=True))
    print('--------------------')
    cnt={'id': '1.2.3.5', 'tag': 'Fig', 'Caption': '''Some people do what they are told to. Some other don't like it.''' }
    annots = get_pseudo_annotations_for_text(cnt, 'Caption')
    print(json.dumps(annots, indent=4, sort_keys=True))
    print('--------------------')
    values = [["toto chez les tutus","youps"],["chmol gloups","ddd"],["eee","ggg"],["jjj","kk ll mm nn op"]]
    cnt={'id': '1.2.3.6', 'tag': 'Table', 'table_values': values }
    annots = get_pseudo_annotations_for_cell(cnt, 5)
    print(json.dumps(annots, indent=4, sort_keys=True))
    print('--------------------')
    with open('da', 'w') as outfile:
        json.dump(annots, outfile, indent=4)
    print('end')
