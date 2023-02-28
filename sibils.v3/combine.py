import json

# - - - - - - - - - - - - - - - - - - - - - 
def get_merged_data(filename):
# - - - - - - - - - - - - - - - - - - - - - 
    with open(filename) as f:
         data = json.load(f)
         return data

# - - - - - - - - - - - - - - - - - - - - - 
def get_v2_field(sentence):
# - - - - - - - - - - - - - - - - - - - - - 
    sen_fld = sentence.get("field")
    # ordered by occurence frequency for efficiency
    if sen_fld == "text": return "text"
    # if sen_fld == "section_title": return "Title" not supported in v2
    if sen_fld == "fig_caption": return "Fig"
    if sen_fld == "table_value": return "Table"
    if sen_fld == "table_column": return "Table"
    if sen_fld == "table_caption": return "Table"
    if sen_fld == "table_footer": return "Table"
    raise Exception("Unexpected sentence field value: " + str(sen_fld), sentence)


# - - - - - - - - - - - - - - - - - - - - - 
def get_v2_subfield(sentence):
# - - - - - - - - - - - - - - - - - - - - - 
    sen_fld = sentence.get("field")
    # ordered by occurence frequency for efficiency
    if sen_fld == "text": return None
    # if sen_fld == "section_title": return "Title" not supported in v2
    if sen_fld == "fig_caption": return "Caption"
    if sen_fld == "table_value": return "Content"
    if sen_fld == "table_column": return "Content"
    if sen_fld == "table_caption": return "Caption"
    if sen_fld == "table_footer": return "Footer"
    raise Exception("Unexpected sentence field value: " + str(sen_fld), sentence)


# - - - - - - - - - - - - - - - - - - - - - 
def build_sentence_dic(data):
# - - - - - - - - - - - - - - - - - - - - - 

    sen_dic = dict()
    for sen in data["sentences"]:
        id = sen["sentence_number"]
        sen_dic[id] = sen
 
    # check key order is numeric order
    # TODO - remove this check, useless according to Julien
    prev_k = -1
    for k in sen_dic:
        if prev_k >= k:
            print("ERROR", "keys in sentence dictionary not properly sorted")
        prev_k = k

    # compute contents_offset of sentences
    # the offset is reset to 0 each time the content_id or the subfield value changes
    prev_cnt_key = None
    sen_offset = 0
    sen_idx = 0
    for k in sen_dic:
        sen = sen_dic[k]
        cnt_id = sen.get("content_id") or "None"
        cnt_fld = sen["field"]
        cnt_key = cnt_id + "/" + cnt_fld
        if cnt_key != prev_cnt_key:
            sen_offset = 0
            sen_idx = 0
            prev_cnt_key = cnt_key        
        sen["sentence_offset"] = sen_offset
        sen_lng = sen["sentence_length"]
        #print(k, cnt_key, sen_idx, sen_lng, sen_offset, sen["sentence"][0:40])
        if sen_lng > 0: sen_offset += sen_lng + 1
        sen_idx += 1

    return sen_dic

# - - - - - - - - - - - - - - - - - - - - - 
def build_v2_style(data):
# - - - - - - - - - - - - - - - - - - - - - 
    v2_annotations = list()
    sentence_dict = build_sentence_dic(data)
    for annot in data["annotations"]:
        sen_id = annot["id_sentence"]
        sen = sentence_dict[sen_id]
        sen_tag = sen.get("tag")
        # we ignore title, abstract annotations which all have a None tag
        # TEMP we ignore affiliations and keyword annotations which all have a None tag - TODO
        if sen_tag is None: continue
        sen_fld = sen["field"]
        # TEMP we ignore annotations on section titles - TODO
        if sen_fld == "section_title": continue
        annot["subfield"] = get_v2_subfield(sen)
        annot["field"] = get_v2_field(sen)
        annot["content_id"] = sen["content_id"]
        #annot["passage"] = sen["sentence"] # not needed, yeah !!!
        annot["passage_length"] = sen["sentence_length"]
        sen_offset = sen["sentence_offset"]
        annot["passage_offset"] = sen_offset
        cpt_pos = annot["start_index"]
        annot["concept_offset"] = cpt_pos
        annot["concept_offset_in_section"] = sen_offset + cpt_pos # wrongly named _in_section, should be in_contents
        v2_annotations.append(annot)
    
    print("v3 annot", len(data["annotations"]), "v2 annot", len(v2_annotations))
    data["annotations"] = v2_annotations
    del data["sentences"]

# - - - - - - - - - - - - - - - - - - - - - 
# main
# - - - - - - - - - - - - - - - - - - - - - 
files_in = ["PMC2828183","PMC3082999","PMC3211372","PMC3284193"]
for item in files_in:
    file_in = "merged/" + item + ".json"
    data = get_merged_data(file_in)
    build_v2_style(data)
    file_out = "v3_to_v2/" + item + "_v2.json"
    with open(file_out, "w") as fo:
        json.dump(data, fo)

print("End")
