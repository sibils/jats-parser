class PmcaFormatter:

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def get_v2_field(self, sentence):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def get_v2_subfield(self, sentence):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def build_sentence_dic(self, data):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def build_v2_style(self, data):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        v2_annotations = list()
        sentence_dict = self.build_sentence_dic(data)
        for annot in data["annotations"]:
            sen_id = annot.get("sentence_number") or annot["id_sentence"]
            sen = sentence_dict[sen_id]
            sen_tag = sen.get("tag")
            # we ignore title, abstract annotations which all have a None tag
            # TEMP we ignore affiliations and keyword annotations which all have a None tag - TODO
            if sen_tag is None: continue
            sen_fld = sen["field"]
            # TEMP we ignore annotations on section titles - TODO
            if sen_fld == "section_title": continue
            annot["subfield"] = self.get_v2_subfield(sen)
            annot["field"] = self.get_v2_field(sen)
            annot["content_id"] = sen["content_id"]
            #annot["passage"] = sen["sentence"] # not needed, yeah !!!
            annot["passage_length"] = sen["sentence_length"]
            sen_offset = sen["sentence_offset"]
            annot["passage_offset"] = sen_offset
            cpt_pos = annot["start_index"]
            annot["concept_offset"] = cpt_pos
            annot["concept_offset_in_section"] = sen_offset + cpt_pos # wrongly named _in_section, should be in_contents
            v2_annotations.append(annot)        
        data["annotations"] = v2_annotations
        del data["sentences"]


    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def get_pmca_format(self, v3_data, collection):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        data = dict()

        # adapt data (especially medline to have a structured body_sections list)
        if collection == "medline":
            data = self.get_adapted_format_for_medline(v3_data)
        elif collection == "pmc":
            data = self.get_adapted_format_for_pmc(v3_data)
        elif collection == "plazi":
            data = self.get_adapted_format_for_plazi(v3_data)

        # trainsform v3 data into a v2 data structure known by the viewer
        v2_annotations = list()
        sentence_dict = self.build_sentence_dic(data)
        for annot in data["annotations"]:
            sen_id = annot.get("sentence_number") or annot["id_sentence"]
            sen = sentence_dict[sen_id]
            sen_tag = sen.get("tag")
            if sen_tag is None: continue
            sen_fld = sen["field"]
            # TEMP we ignore annotations on section titles
            if sen_fld == "section_title": continue
            annot["subfield"] = self.get_v2_subfield(sen)
            annot["field"] = self.get_v2_field(sen)
            annot["content_id"] = sen["content_id"]
            #annot["passage"] = sen["sentence"] # not needed, yeah !!!
            annot["passage_length"] = sen["sentence_length"]
            sen_offset = sen["sentence_offset"]
            annot["passage_offset"] = sen_offset
            cpt_pos = annot["start_index"]
            annot["concept_offset"] = cpt_pos
            annot["concept_offset_in_section"] = sen_offset + cpt_pos # wrongly named _in_section, should be in_contents
            v2_annotations.append(annot)

        pam_data = data["document"]  
        pam_data["annotations"] = v2_annotations
        return pam_data


    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def update_sentence(self, sentence, content_id, tag, field):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        sentence["content_id"] = content_id
        sentence["tag"] = tag
        sentence["field"] = field


    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def get_adapted_format_for_plazi(self, data):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        document = data["document"]
        body_sections = list()
        document["body_sections"] = []
        document["back_sections"] = []
        document["float_sections"] = []
        document["extra_sections"]  = []
        document["title"] = document["treatment_title"]
        document["abstract"] = document["text"]
        tbu = document["treatment-bank-uri"]
        if tbu.startswith("https://treatment.plazi.org/id/"): tbu = tbu[31:]
        elif tbu.startswith("http://treatment.plazi.org/id/"): tbu = tbu[30:]
        document["treatment_bank_uri"] = tbu
        zenodoi = document["zenodo-doi"]
        if zenodoi.startswith("https://dx.doi.org/"): zenodoi = zenodoi[19:]
        elif zenodoi.startswith("http://dx.doi.org/"): zenodoi = zenodoi[18:]
        document["zenodo_doi"] = zenodoi

        body_sections = document["body_sections"]

        title_contents = list()
        title_section = {"id": "1", "implicit": True, "label": "", "level": 1, 
                         "title": "Title", "contents": title_contents}        
        body_sections.append(title_section)

        abstract_contents = list()
        abstract_section = {"id": "2", "implicit": False, "label": "", "level": 1,  
                            "title": "Treatment", "caption":"", "tag": "abstract", "contents": abstract_contents } 
        body_sections.append(abstract_section)

        for sen in data["sentences"]:
            if sen["field"] == "treatment_title":
                id = "1." + str(len(title_contents) + 1)
                title_para = {"id": id, "tag": "p", "text": sen["sentence"]}
                title_contents.append(title_para)
                self.update_sentence(sen, id, "p", "text")
                print("treatment_title sentence:", sen)

            elif sen["field"] == "text":
                id = "2." + str(len(abstract_contents) + 1)
                abstract_para = {"id": id, "tag": "p", "text": sen["sentence"]}
                abstract_contents.append(abstract_para)
                self.update_sentence(sen, id, "p", "text")

        return data


    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def get_abstract_section_for_medline(self, document):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        abstract_section = {
            "id": "2", "implicit": False, "label": "", "level": 1, 
            "title": "Abstract", "caption":"", "tag": "abstract" } 
        content_list = list()
        para_num = 0
        for text in document["abstract"].split("\n"):
            if len(text.strip())==0: continue
            para_num += 1
            id = "2." + str(para_num)
            content = { "id": id, "tag": "p", "text": text }
            content_list.append(content)
        abstract_section["contents"] = content_list # [abstract_para]}
        return abstract_section


    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def find_sentence_content_id(self, section, sentence):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        for cnt in section["contents"]:
            if cnt["text"].find(sentence["sentence"]) >= 0:
                return cnt["id"]
        return "???"

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def get_adapted_format_for_medline(self, data):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        
        #data["document"]["coi_statement"]= "This is my beautiful coi statement"

        # iterate over sentences
        mesh_terms_count = 0
        chem_terms_count = 0
        key_terms_count = 0
        aff_count = 0
        print(data)
        abstract_section = self.get_abstract_section_for_medline(data["document"])
        for sen in data["sentences"]:
            # add missing information in sentence objects
            if sen["field"]=="title":
                self.update_sentence(sen, "1.1", "p", "text")
            elif sen["field"] == "abstract":
                cnt_id = self.find_sentence_content_id(abstract_section, sen)
                #print("sentence_number:", sen["sentence_number"], "content_id", cnt_id, sen["sentence"][0:20]+"...")
                self.update_sentence(sen, cnt_id, "p", "text")
            # i.e. medline 729227
            elif sen["field"] == "mesh_terms":
                mesh_terms_count += 1
                self.update_sentence(sen,  "3." + str(mesh_terms_count), "p", "text")
            # i.e. medline 699654, 699655
            elif sen["field"] == "chemicals":
                chem_terms_count += 1
                self.update_sentence(sen,  "4." + str(chem_terms_count), "p", "text")
            elif sen["field"] == "coi_statement":
                self.update_sentence(sen,  "10.1", "p", "text")
            # i.e. medline 725797, 729227
            elif sen["field"] == "keywords":
                key_terms_count += 1
                self.update_sentence(sen,  "5." + str(key_terms_count), "p", "text")
            # i.e. medline 724279, 724280, 724281 (many in single element)
            elif sen["field"] == "affiliations":
                aff_count += 1
                self.update_sentence(sen,  "1000." + str(aff_count), "p", "text")                


        # add body_sections for title, abstract, ...
        #fields = ["title", "abstract", "chemicals", "coi_statements", "keywords", "mesh_terms", ]
        document = data["document"]
        body_sections = list()
        document["body_sections"] = body_sections
        document["back_sections"] = []
        document["float_sections"] = []
        extra_sections = list()
        document["extra_sections"] = extra_sections

        # extra affiliation section
        affiliation_list = document["affiliations"]
        if affiliation_list is not None and len(affiliation_list)>0:
            contents = list()
            section = {"id": "1000", "implicit": True, "label": "", "level": 1, 
                        "title": "Affiliations", "caption":"", "tag": "affiliations", 
                        "contents": contents}
            idx = 0
            for item in affiliation_list:
                idx += 1
                contents.append({"id": "1000." + str(idx), "tag": "list-item", "text": item})
            extra_sections.append(section)

        # title section
        title_para = {"id": "1.1", "tag": "p", "text": document["title"]}
        title_section = {"id": "1", "implicit": True, "label": "", "level": 1, 
                         "title": "Title", "contents": [title_para]}
        body_sections.append(title_section)

        # abstract section
        abstract_section = self.get_abstract_section_for_medline(document)
        body_sections.append(abstract_section)

        # mesh terms section
        mesh_terms = document.get("mesh_terms")
        if mesh_terms is not None  and len(mesh_terms) > 0:
            contents = list()
            section = {"id": "3", "implicit": False, "label": "", "level": 1, 
                        "title": "MeSH terms", "caption":"", "tag": "mesh_terms", 
                        "contents": contents}
            idx = 0
            for item in mesh_terms:
                idx += 1
                contents.append({"id": "3." + str(idx), "tag": "list-item", "text": item})
            body_sections.append(section)

        # chemical terms section
        chem_terms = document.get("chemicals")
        if chem_terms is not None and len(chem_terms) > 0:
            contents = list()
            section = {"id": "4", "implicit": False, "label": "", "level": 1, 
                        "title": "Chemical terms", "caption":"", "tag": "chemicals", 
                        "contents": contents}
            idx = 0
            for item in chem_terms:
                idx += 1
                contents.append({"id": "4." + str(idx), "tag": "list-item", "text": item})
            body_sections.append(section)

        # keywords section
        key_terms = document.get("keywords")
        if key_terms is not None and len(key_terms) > 0:
            contents = list()
            section = {"id": "5", "implicit": False, "label": "", "level": 1, 
                        "title": "Keywords", "caption":"", "tag": "keywords", 
                        "contents": contents}
            idx = 0
            for item in key_terms:
                idx += 1
                contents.append({"id": "5." + str(idx), "tag": "list-item", "text": item})
            body_sections.append(section)

        # coi statement section
        coi = document.get("coi_statement")
        if coi is not None and len(coi) > 0:
            coi_para = {"id": "10.1", "tag": "p", "text": document["coi_statement"]}
            coi_section = {"id": "10", "implicit": False, "label": "", "level": 1, 
                                "title": "Conflicts of interest statement", "caption":"", "tag": "p", 
                                "contents": [coi_para]}
            body_sections.append(coi_section)


        return data

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def get_adapted_format_for_pmc(self, data):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        aff_count = 0
        key_terms_count = 0
        for sen in data["sentences"]:
            # add missing information in sentence objects
            if sen["field"] == "affiliations":
                aff_count += 1
                self.update_sentence(sen,  "1000." + str(aff_count), "p", "text")                
            elif sen["field"] == "keywords":
                key_terms_count += 1
                self.update_sentence(sen,  "1005." + str(key_terms_count), "p", "text")


        document = data["document"]
        extra_sections = list()
        document["extra_sections"] = extra_sections
        # extra affiliation section
        affiliation_list = document["affiliations"]
        if affiliation_list is not None and len(affiliation_list)>0:
            contents = list()
            section = {"id": "1000", "implicit": True, "label": "", "level": 1, 
                        "title": "Affiliation(s):", "caption":"", "tag": "affiliations", 
                        "contents": contents}
            idx = 0
            for item in affiliation_list:
                idx += 1
                #name = str(idx) + ". " + item["name"]
                name = item["name"]
                contents.append({"id": "1000." + str(idx), "tag": "list-item", "text": name, "index": idx })
            extra_sections.append(section)


        # keywords section
        key_terms = document.get("keywords")
        if key_terms is not None and len(key_terms) > 0:
            contents = list()
            section = {"id": "1005", "implicit": False, "label": "", "level": 1, 
                        "title": "Keywords", "caption":"", "tag": "keywords", 
                        "contents": contents}
            idx = 0
            for item in key_terms:
                idx += 1
                contents.append({"id": "1005." + str(idx), "tag": "list-item", "text": item})
            document["body_sections"].append(section)

        return data



# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    print("End")
