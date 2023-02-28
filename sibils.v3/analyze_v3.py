import json

pmc_list = ["PMC2828183","PMC3082999","PMC3211372","PMC3284193"]

file = "merged/PMC3211372.json"

tag_field_dic = dict()
#
# sentence tag / field combinations
#
# a) regular contents with content_id, tag and text field
#
# p/text 245
# ack/text 4
# notes/text 2
# media/text 1

# => tested: OK

#
# b) without content_id nor tag
#
# None/title 2          <- to be ignored, same info available in contents of body section with id=1 
# None/abstract 8       <- to be ignored, same info available in contents of body section with id=2

# None/keywords 5       <- NEW annotated contents, not visible in viewer
# None/affiliations 3   <- NEW annotated contents, visible in viewer but not annotatable so far
#
# c) without content_id nor tag
#
# sec/section_title 28   <- equivalent in v2: tag: "sec" (ou autre) title = "some content" , nothing found in label nor caption fields, only in title
# fig/fig_caption 25
# table/table_caption 5

# table/table_footer 4
# table/table_column 21
# table/table_value 72

# Rules for v3

# - - - - - - - - - - - - - - - - - - - - - 
def get_content_source_field(sentence):
# - - - - - - - - - - - - - - - - - - - - - 
    source_fld = sentence.get("field")
    # ordered by occurence frequency for efficiency
    if source_fld == "text": return "text"
    if source_fld == "section_title": return "title"
    if source_fld == "fig_caption": return "caption"
    if source_fld == "table_value": return "table_values"
    if source_fld == "table_column": return "table_columns"
    if source_fld == "table_caption": return "caption"
    if source_fld == "table_footer": return "footer"
    #raise Exception("Unexpected sentence field value:" + str(source_fld), "sentence_id:" + str(sentence.get("sentence_number")))
    raise Exception("Unexpected sentence field value: " + str(source_fld), sentence)


# - - - - - - - - - - - - - - - - - - - - - 
def flatten_lists(obj):
# - - - - - - - - - - - - - - - - - - - - - 
    if type(obj)==list:
        res = ""
        for el in obj:
            flat_el = flatten_lists(el).strip()
            if len(flat_el)>0: res += " " + flat_el 
        return res.strip()
    else:
        return str(obj).strip()



# content typology p/text ['1.1', '2.1', '3.1.1', '3.1.2', '3.1.3', '3.1.4', '3.2.1.1', '3.2.1.2', '3.2.1.5', '3.2.2.1']
# content typology ack/text ['4.1']
# content typology notes/text ['4.2']
# content typology media/text ['4.3.1']
# content typology ref-list/text ['4.4.1']

# content typology fig/caption ['3.2.1.3', '3.2.2.2', '3.3.1.2', '3.3.2.4.2', '3.3.2.5.2', '3.3.2.5.4', '3.3.2.6.2', '3.3.2.6.3', '3.3.2.11.2']
# content typology fig/label ['3.2.1.3', '3.2.2.2', '3.3.1.2', '3.3.2.4.2', '3.3.2.5.2', '3.3.2.5.4', '3.3.2.6.2', '3.3.2.6.3', '3.3.2.11.2']
# content typology table/caption ['3.2.1.4', '3.3.1.4', '3.3.1.6', '3.3.2.3']
# content typology table/label ['3.2.1.4', '3.3.1.4', '3.3.1.6', '3.3.2.3']
# content typology table/table_columns ['3.2.1.4', '3.3.1.4', '3.3.1.6', '3.3.2.3']
# content typology table/table_values ['3.2.1.4', '3.3.1.4', '3.3.1.6', '3.3.2.3']



content_dic = dict()
sentence_dic = dict()

with open(file) as f: data = json.load(f)

# create dictionary of contents by id
for sections_group in ["body_sections", "back_sections"]:
    for sec in data[sections_group]:
        content_dic[sec["id"]] = sec
        for cnt in sec["contents"]:
            content_dic[cnt["id"]] = cnt

# sentence fields
for sen in data["sentences"]:
    sen_id = sen["sentence_number"]
    sentence_dic[sen_id] = sen
    cnt_id = sen.get("content_id")
    if cnt_id is not None:
        cnt = content_dic.get(cnt_id)
        if cnt is None:
            print("WARNING", "id", cnt_id, "is not a key for contents")
            continue
        if cnt.get("sentences") is None: cnt["sentences"] = list()
        sen["index"]= len(cnt["sentences"])
        cnt["sentences"].append(sen)
 
for k in content_dic:
    rec = content_dic[k]
    sen_list = rec.get("sentences") or list()
    print(k, "tag", rec.get("tag"),  "sentences", len(sen_list))
    for sen in sen_list:
        print("- sentence", sen["field"] , sen["tag"], sen["index"], sen["sentence_number"], sen["sentence"][0:60])

print("content_dic", len(content_dic))
print("------------------")

for k in sentence_dic:
    rec = sentence_dic[k] 
    print(k, rec["sentence_number"], rec["sentence"][0:60])
print("------------------")
print("sentence_dic", len(sentence_dic))

annot_cnt = 0
for annot in data["annotations"]:
    annot_cnt += 1
    cpt_str = annot["concept_form"]
    cpt_pos = annot["start_index"]
    cpt_lng = annot["concept_length"]
    cpt_end = annot["end_index"]

    # check concept string position and length
    if len(cpt_str) != cpt_lng:
        print("ERROR", "Unexpected concept_length", cpt_lng, "for concept form", cpt_str)
    if cpt_end - cpt_pos != cpt_lng:
        print("ERROR", "Inconsistent concept_length", cpt_lng, "for start_index", start_index,  "end_index", end_index, "for concept form", cpt_str)

    # check concept string position within sentence
    sentence_id = annot["id_sentence"]
    sen = sentence_dic[sentence_id]
    sen_str = sen["sentence"]
    cpt_from_sentence = sen_str[cpt_pos:cpt_end]
    if cpt_str != cpt_from_sentence:
        print("ERROR", "concept location problem", "cpt_str", cpt_str, "cpt_from_sentence", cpt_from_sentence)

    # check concept position in content for regular content with text property
    cnt_id = sen.get("content_id")
    sen_tag = sen.get("tag")
    sen_field = sen.get("field")
    if cnt_id is None: 
        print("INFO", "No content_id for sentence", sentence_id, "tag:", sen_tag, "field:" , sen_field )
        continue

    #if sen_field != "text": continue
    source_field = get_content_source_field(sen)
    cnt = content_dic[cnt_id]
    offset = 0
    found = False
    for s in cnt["sentences"]:
        if s["sentence_number"] != sentence_id:
            if get_content_source_field(s) != source_field: continue
            lng = s["sentence_length"]
            if lng>0: offset += s["sentence_length"] + 1
        else:
            found = True
            #print("content", cnt.get("tag"), cnt.get("field"), "cpt_str", cpt_str, "sentence", s )
            #cnt_str = cnt["text"]           
            cnt_str = cnt[source_field]
            if (source_field in ["table_columns", "table_values"]):
                cnt_str = flatten_lists(cnt_str)
            cpt_from_content = cnt_str[offset + cpt_pos : offset + cpt_end]
            if cpt_from_content != cpt_str:
                print("ERROR", "tag", sen_tag, "field", source_field, "cnt", cnt_id, "sen_idx", s["index"] ,"cpt_str", cpt_str, "cpt_from_content", cpt_from_content)
                #print(cnt_str)
    if not found:
        print("ERROR", "sentence ", sentence_id, "not found in", cnt_id)    

    # # nice examples
    # if sen["index"] > 0:
    #     offset = 0
    #     for s in cnt["sentences"]:
    #         offset += s["sentence_length"] + 1
    #         print(s["sentence_number"], s["sentence_length"], offset, s["sentence"])
    #         if s["sentence_number"] == sentence_id: 
    #             print("concept", cpt_str, cpt_pos, cpt_pos+offset)
    #             break



print("annot_count",annot_cnt)
print("Done")


print(flatten_lists(["toto", "tutu"]))