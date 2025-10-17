import json

from urllib.request import urlopen 
from pmca_formatter import PmcaFormatter



url = "https://sibils.text-analytics.ch/api/fetch?ids=11552900&col=medline"
url = "https://sibils.text-analytics.ch/api/fetch?col=medline&ids=18478337"  
# store the response of URL 
response = urlopen(url) 
  
# storing the JSON response  
# from url in data 
data_json = json.loads(response.read()) 


formatter = PmcaFormatter()
doc_json = data_json["sibils_article_set"][0]
pmca_json = formatter.get_pmca_format(doc_json, "medline")


if 1==2:

    abstract_section = formatter.get_abstract_section_for_medline(data_json["sibils_article_set"][0]["document"])


    abstract = data_json["sibils_article_set"][0]["document"]["abstract"]

    sen_dict = dict()
    for sen in data_json["sibils_article_set"][0]["sentences"]:
        if sen["field"]=="abstract":
            sentence_number = sen["sentence_number"]
            sen_dict[sentence_number] = sen
            jusen = sen["sentence"] 
            abstract_offset = abstract.index(jusen)
            sen["abstract_offset"]=abstract_offset
            # print("abstract_offset: ", abstract_offset)    
            # print("sentence_number: ", sentence_number)    
            # print("sentence_length: ", sen["sentence_length"])
            # print(jusen)
            for sen_part in jusen.split("\n"):
                print("part:", sen_part)
                for content in abstract_section["contents"]:
                    pos = content["text"].find(sen_part)
                    if pos >= 0:
                        sen["content_id"] = content["id"]
                        sen["content_offset"] = pos -(jusen.index(sen_part))


    for sen in data_json["sibils_article_set"][0]["sentences"]:
        if sen["field"]=="abstract":
            print(sen)



    for annot in data_json["sibils_article_set"][0]["annotations"]:
        if annot["field"] != "abstract": continue
        sen_id = annot["sentence_number"]
        sen = sen_dict[sen_id]
        start_index = annot["start_index"]
        end_index = annot["end_index"]
        content_id = sen["content_id"]
        content_offset = sen["content_offset"]
        concept_form = annot["concept_form"]
        if concept_form != sen["sentence"][start_index: end_index]:
            print("ERROR unexpected pos of concept form in sentence")
            print("concept_form:", concept_form, "at start", start_index, "end", end_index)
            print("in sentence :", sen["sentence"][start_index: end_index])
        for content in abstract_section["contents"]:
            if content["id"] == sen["content_id"]:
                cnt_txt = content["text"]
                print("concept_form:", concept_form)
                cnt_part = cnt_txt[start_index: end_index]


    #for ch in str:
    #    print(ascii(ch), ord(ch))