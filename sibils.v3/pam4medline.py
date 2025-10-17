import http.client
import json
from mongo_pam_fetcher import MongoPamFetcher

def getSibilsPubli(id, col, formatPam=False, withCovoc=False):

    # https://sibils.text-analytics.ch/api/v3.3/fetch?ids=PMC4909023&col=pmc

    connection = http.client.HTTPSConnection("sibils.text-analytics.ch")
    url = '/api/v3.3/fetch?ids=' + id
    url += "&col=" + col
    if formatPam: url += '&format=PAM'
    if withCovoc: url += '&covoc'
    connection.request("GET", url)
    response = connection.getresponse()
    output={}
    output["status"]=response.status
    output["reason"]=response.reason
    data = response.read().decode("utf-8")
    obj = json.loads(data)
    output["data"]= obj
    connection.close()
    return output


def save(obj, file_name):
    f_out = open(file_name, "w")
    json.dump(obj, f_out, indent=4, sort_keys=True)
    f_out.close()

if __name__ == '__main__':

    focus = "medline"

    if focus == "medline":
        comb = set()
        response = getSibilsPubli("PMC4909023","pmc", formatPam = False)
        publi = response["data"]["sibils_article_set"][0]
        for sen in publi["sentences"]:
            id = sen.get("content_id")
            tg = sen.get("tag")
            fld = sen.get("field")
            key = str(tg) + "|" + str(fld) + "|pmc|" + str(id)
            comb.add(key)
        response = getSibilsPubli("37122198","medline", formatPam = False)
        publi = response["data"]["sibils_article_set"][0]
        for sen in publi["sentences"]:
            id = sen.get("content_id")
            tg = sen.get("tag")
            fld = sen.get("field")
            key = str(tg) + "|" + str(fld) + "|medline|" + str(id)
            comb.add(key)
        
        for k in comb:
            print(k)

        '''
        tag = None
        fld = abstract, affiliations, chemicals, coi_statement, keywords, mesh_terms, title
        id = None in medline
        id = 0 in pmc
        tag  fld      col     id  
        None|abstract|medline|None
        None|abstract|pmc|0
        None|affiliations|pmc|0
        None|affiliations|medline|None
        None|chemicals|medline|None
        None|coi_statement|medline|None
        None|keywords|medline|None
        None|keywords|pmc|0
        None|mesh_terms|medline|None
        None|title|medline|None
        None|title|pmc|0
        '''

    if focus == "pmc":
        response = getSibilsPubli("PMC4909023", "pmc", formatPam=True)
        publi_pam = response["data"]["sibils_article_set"][0]
        save(publi_pam, "PMC4909023.pam.json")

        response = getSibilsPubli("PMC4909023", "pmc", formatPam=False)
        publi = response["data"]["sibils_article_set"][0]
        save(publi, "PMC4909023.json")

        mpf = MongoPamFetcher(None,None,None)
        publi_local = mpf.get_pam_format(publi)
        save(publi_local, "PMC4909023.pam_local.json")

        print("pam.json == pam__local.json ?" , publi_pam==publi_local)
        # OK !!!
