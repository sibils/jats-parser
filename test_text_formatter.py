import http.client
from text_formatter import TextFormatter



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
    return list(pmcid_set)



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
            print(f"ERROR - Got {status} on trying to get json for {pmcid}: {response.reason}")
            return None
        else:
            print(f"INFO - Got OK on trying to get json for {pmcid}")
            return data
    except Exception as e:
        connection.close()
        print(f"ERROR - ", e)


# ============================================
if __name__ == '__main__':
# ============================================
    #pmcids = list(get_pmid2pmcid().values())
    pmcids = get_some_valid_pmcids()
    print(f"INFO - Found {len(pmcids)} pmcid(s)")
    count = 0
    for pmcid in pmcids:
        count += 1
        print(f"INFO - Getting json for publi {pmcid}")
        json_obj = get_json_for_publi(pmcid)

    print("INFO end")
