import json

pmc_list = ["PMC2828183","PMC3082999","PMC3211372","PMC3284193"]

file = "v2/PMC3211372v2.json"
# subfield set {'Table/Content', 'text/None', 'Fig/Caption', 'Table/Caption'}
field_subfield_set = set()

with open(file) as f: data = json.load(f)
data = data[0]

content_dic = dict()
content_field_dic = dict()

for section_group in ["body_sections", "back_sections"]:
    for sec in data[section_group]:
        sec_id = sec["id"]
        sec_title = sec["title"]
        sec_label = sec["label"]
        sec_tag = sec.get("tag") or ""
        sec_caption = sec.get("caption") or ""
        if sec_title != "": print("INFO","section with title",sec_tag, sec_id, sec_title)        # <- many
        if sec_label != "": print("INFO","section with label",sec_tag, sec_id, sec_label)        # <- none
        if sec_caption != "": print("INFO","section with caption",sec_tag, sec_id, sec_caption)  # <- none

        for cnt in sec["contents"]:
            cnt_tag = cnt.get("tag") or ""
            cnt_id = cnt.get("id") or ("no_id???")
            cnt_txt = cnt.get("text") or ""
            cnt_cpt = cnt.get("caption") or ""
            cnt_foo = cnt.get("footer") or ""
            cnt_lbl = cnt.get("label") or ""
            cnt_col = cnt.get("table_columns") or []
            cnt_val = cnt.get("table_values") or []
            if cnt_txt != "":
                key = cnt_tag + "/text"
                if key not in content_field_dic: content_field_dic[key] = [] 
                content_field_dic[key].append(cnt_id)
            if cnt_cpt != "":
                key = cnt_tag + "/caption"
                if key not in content_field_dic: content_field_dic[key] = [] 
                content_field_dic[key].append(cnt_id)
            if cnt_foo != "":
                key = cnt_tag + "/footer"
                if key not in content_field_dic: content_field_dic[key] = [] 
                content_field_dic[key].append(cnt_id)
            if cnt_lbl != "":
                key = cnt_tag + "/label"
                if key not in content_field_dic: content_field_dic[key] = [] 
                content_field_dic[key].append(cnt_id)
            if len(cnt_col) != 0:
                key = cnt_tag + "/table_columns"
                if key not in content_field_dic: content_field_dic[key] = [] 
                content_field_dic[key].append(cnt_id)
            if len(cnt_val) != 0:
                key = cnt_tag + "/table_values"
                if key not in content_field_dic: content_field_dic[key] = [] 
                content_field_dic[key].append(cnt_id)

            if cnt_txt is not None:
                content_dic[cnt["id"]] = cnt_txt

annot_cnt = 0
error_cnt = 0

for annot in data["annotation"]:
    annot_cnt += 1
    subfield = annot.get("subfield") or "None"
    field = annot["field"]
    field_subfield_set.add(field + "/" + subfield)
    concept_form = annot["concept_form"]
    concept_offset = annot["concept_offset"]
    concept_length = annot["concept_length"]
    passage = annot["passage"]
    concept_by_length = passage[concept_offset:concept_offset+concept_length]
    if concept_form != concept_by_length:
        # print("WARN 1", "<" +concept_form + ">" , concept_offset, concept_length, "<" + concept_by_length + ">")
        concept_by_form = passage[concept_offset:concept_offset+len(concept_form)]
        if concept_form != concept_by_form:
            error_cnt += 1
            print("ERROR 1", "<" +concept_form + ">" , concept_offset, concept_length, "<" + concept_by_form + ">")
    
    if field == "text":
        passage_offset = annot["passage_offset"]
        concept_pos_in_content = passage_offset + concept_offset
        cnt_id = annot["content_id"]
        cnt_text = content_dic[cnt_id]
        concept_by_length = cnt_text[concept_pos_in_content:concept_pos_in_content+concept_length]
        if concept_by_length != concept_form:
            pass
            #print("ERROR 2", concept_form, cnt_id, concept_by_length)        
        if concept_by_length == concept_form and passage_offset>0:
            print("INFO", concept_form, cnt_id, passage_offset, concept_by_length)        

print("error cnt", error_cnt)
print("annot cnt", annot_cnt)
print("subfield set", field_subfield_set)

for k in content_dic:
    print(k, content_dic[k][0:80])

print("----------")
for k in content_field_dic:
    print("content typology", k, content_field_dic[k][0:10])

print("end")

