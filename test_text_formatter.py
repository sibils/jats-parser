import http.client
from text_formatter import TextFormatter
import json
import sys
import os


# - - - - - - - - - - - - - - - - - - - - - - 
# Find a subset of pmid - pmcid pairs
# - - - - - - - - - - - - - - - - - - - - - - 
def get_pmid2pmcid():
# - - - - - - - - - - - - - - - - - - - - - - 
    stream = open("../rdf4sibils/v2/out/colls/merged-mapping.txt")
    # ignore first line with field names pmid : medline : pmc
    line = stream.readline() 
    pmid2pmcid_dict = dict()
    while True:
        line = stream.readline()
        if line == "": break
        fields = line.strip().split(" : ")
        if "PMC" in fields[1]:
            pmid2pmcid_dict[fields[0]] = fields[1]
            print(fields[0], " => ", fields[1])
        elif "PMC" in fields[2]:
            pmid2pmcid_dict[fields[0]] = fields[2]
            print(fields[0], " => ", fields[2])
    stream.close()
    return pmid2pmcid_dict

# - - - - - - - - - - - - - - - - - - - - - - 
# PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
# PREFIX fabio: <http://purl.org/spar/fabio/>
# select ?pmcid where {
#   ?publi sibilo:inCollection "pmc" .
#   ?publi dcterms:isReferencedBy sibils:Cellosaurus  . 
#   ?publi fabio:hasPubMedCentralId ?pmcid .
# }
# - - - - - - - - - - - - - - - - - - - - - - 
def get_some_valid_pmcids():
# - - - - - - - - - - - - - - - - - - - - - - 
    stream = open("valid-pmcids.txt")
    line = stream.readline() 
    pmcid_set = set()
    while True:
        line = stream.readline()
        if line == "": break
        pmcid_set.add(line.strip())
    stream.close()
    return sorted(list(pmcid_set))



# - - - - - - - - - - - - - - - - - - - - - - 
def get_json_for_publi(pmcid):
# - - - - - - - - - - - - - - - - - - - - - - 
    # use json_httpserver to download xml and get generated json file
    try:
        connection = http.client.HTTPConnection("localhost:8088")
        url = f"/pseudo/api/fetch?col=pmc&id={pmcid}"
        connection.request("GET", url)
        response = connection.getresponse()
        status = response.status
        data = response.read().decode("utf-8")
        connection.close()
        if status != 200:
            print(f"ERROR - Got {status} on getting json for {pmcid}: {response.reason}")
            return None
        else:
            print(f"INFO - Got OK on getting json for {pmcid}")
            return json.loads(data)
    except Exception as e:
        connection.close()
        print(f"ERROR - Got ERROR on getting json for {pmcid}", e)
        return None


# - - - - - - - - - - - - - - - - - - - - - - 
def save_publi_with_pmcid():
# - - - - - - - - - - - - - - - - - - - - - - 
    pmid2pmcid = get_pmid2pmcid()
    newlines = list()

#   with open("cl-single-publi.tsv") as stream:
    with open("cl-single-publi-0-xref.tsv") as stream:
        newlines.append(stream.readline().strip() + "\tpmcid")
        while True:
            line = stream.readline()
            if line == "": break
            line = line.strip()
            fields = line.split("\t")
            if not fields[5].startswith("PubMed="):
                print("WARNING", "No PubMed identifier at line: ", line)
                continue
            pmid = fields[5][7:]
            if pmid not in pmid2pmcid:
                print("WARNING", "No mapping to a known pmcid at line: ", line)
                continue
            pmcid = pmid2pmcid[pmid]
            filename = f"data_txt/{pmcid}.txt"
            if not os.path.exists(filename):
                print("WARNING", "No text file for pmcid mapped to line: ", line)
                continue
            newlines.append(line + "\t" + pmcid)

    with open("cl-single-publi-with-pmcid.tsv", "w") as stream:
        stream.write("\n".join(newlines))


# ============================================
if __name__ == '__main__':
# ============================================

    save_publi_with_pmcid()

    if 1==2:
        pmcids = get_some_valid_pmcids()
        #pmcids = list(get_pmid2pmcid().values())
        print(f"INFO - Found {len(pmcids)} pmcid(s)")
        count = 0
        for pmcid in pmcids:
            count += 1
            print(f"INFO - Getting json for publi {pmcid}")
            json_obj = get_json_for_publi(pmcid)
            if json_obj is None: continue
            publi_obj = json_obj["sibils_article_set"][0]
            formatter = TextFormatter(publi_obj)
            txt = formatter.get_text_format()
            filename = f"data_txt/{pmcid}.txt"
            with open(filename, "w") as stream: stream.write(txt)

    print("INFO end")
