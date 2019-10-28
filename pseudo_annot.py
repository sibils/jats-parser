import random

def get_pseudo_annotations(sometext, id):
    passages = split_text(sometext);
    print('nb.psg: ' + str(len(passages)))
    annotations = list()
    offset=0
    for p in passages:
        print('> psg: ' + p)
        annotations.extend(get_annotations(p, offset, id))
        offset = offset + len(p) + 2
    return annotations

def split_text(txt):
    return txt.split('. ')

def get_annotations(psg, offset, id):
    annotations = list()
    words = psg.split(' ')
    word_cnt = len(words)
    if word_cnt < 3: return list()
    print('nb.words: ' + str(word_cnt))

    max_annot = int(word_cnt / 3)
    if max_annot > 3: max_annot = 3
    sample = random.sample( range(0, word_cnt-1) , max_annot)
    sample.sort()
    print(sample)
    w_offset=0
    w_idx=0
    for w in words:
        if w_idx in sample:
            annot = build_annot(w, w_offset, psg, offset, id)
            annotations.append(annot)
        w_offset = w_offset + len(w) + 1
        w_idx = w_idx + 1
    return annotations

def build_annot(w, w_offset, psg, offset, id):
    annot=dict()
    annot['type']='TYP:MyTyo'
    annot['concept_source']='SRC:MySrc'
    annot['version']='28-10-2019'
    annot['concept_id']='ID:myId'
    annot['special_id']='SPID:special'
    annot['concept_form']=w
    annot['preferred_term']=w
    annot['passage']=psg
    annot['content_id']=id
    annot['concept_offset']=w_offset
    annot['concept_length']=len(w)
    annot['passage_offset']=offset
    annot['passage_length']=len(psg)
    return annot

if __name__ == '__main__':
    print('--------------------')
    print(get_pseudo_annotations('Hello my name is Jack', '1.1.1'))
    print('--------------------')
    print(get_pseudo_annotations('''Some people do what they are told to. Some other don't like it.''', '1.2.3'))
    print('--------------------')
    print('end')
