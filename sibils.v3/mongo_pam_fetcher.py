from pymongo import MongoClient


class MongoPamFetcher:

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def __init__(self, host="localhost", port=27017, db_name="sibils_v3_1"):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        client = MongoClient(host=host, port=port)
        self.mongo_db = client[db_name]

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def set_collections(self, bibcol_name = "pmcbib23", anacol_name = "pmcana23", sencol_name = "pmcsen23"):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.bibcol_name = bibcol_name
        self.anacol_name = anacol_name
        self.sencol_name = anacol_name
        self.bibcol = self.mongo_db[bibcol_name]
        self.anacol = self.mongo_db[anacol_name]
        self.sencol = self.mongo_db[sencol_name]
        
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def fetch_v3_data(self, pmcid):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        obj = self.bibcol.find_one({'_id': pmcid}, no_cursor_timeout=True)
        ana = self.anacol.find_one({'_id': pmcid}, no_cursor_timeout=True)
        sen = self.sencol.find_one({'_id': pmcid}, no_cursor_timeout=True)
        obj["annotations"] = ana["annotations"]
        obj["sentences"] = sen["sentences"]
        return obj

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def fetch_pam_data(self, pmcid):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        obj = self.fetch_v3_data(pmcid)
        self.build_v2_style(obj)
        return obj

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
            sen_id = annot["id_sentence"]
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
        print("v3 annot", len(data["annotations"]), "v2 annot", len(v2_annotations))
        data["annotations"] = v2_annotations
        del data["sentences"]


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    
    pmc_list = ["PMC2828183","PMC3082999","PMC3211372","PMC3284193"]

    # init mongo db connection and collections to be fetched
    mongo_pam_fetcher = MongoPamFetcher(host="localhost", port=27018, db_name= "sibils_v3_1")
    mongo_pam_fetcher.set_collections(bibcol_name = "pmcbib23", anacol_name="pmcana23", sencol_name="pmcsen23" )

    # get an object in "sibils-like" fetch v3 raw format
    obj = mongo_pam_fetcher.fetch_v3_data(pmc_list[0])
    print("pmcid", obj.get("pmcid"))
    print("anotations", 0 if obj.get("annotations") is None else len(obj.get("annotations")) )
    print("sentences", 0 if obj.get("sentences") is None else len(obj.get("sentences")) )

    # get an object in "sibils-like" fetch_PAM format
    obj = mongo_pam_fetcher.fetch_pam_data(pmc_list[0])
    print("pmcid", obj.get("pmcid"))
    print("anotations", 0 if obj.get("annotations") is None else len(obj.get("annotations")) )
    print("sentences", 0 if obj.get("sentences") is None else len(obj.get("sentences")) )

    print("End")
