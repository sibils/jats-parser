import os
import sys
import json
import tarfile
from ftplib import FTP
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
from process_xml import parse_PMC_XML,getPmcFtpUrl
from pseudo_annot import get_pseudo_annotations_for_text,get_pseudo_annotations_for_cell
from pmca_formatter import PmcaFormatter
from text_formatter import TextFormatter

def getSibilsPubli(pmcid, withCovoc):
    connection = http.client.HTTPSConnection("candy.hesge.ch")
    url = '/SIBiLS/PMC/fetch_PAM.jsp?ids=' + pmcid
    if withCovoc: url += '&covoc'
    connection.request("GET", url)
    response = connection.getresponse()
    output={}
    output["status"]=response.status
    output["reason"]=response.reason
    data = response.read().decode("utf-8")
    obj = json.loads(data)
    if len(obj)==1:
        obj = obj[0]
        #some reformatting
        if obj.get('annotations') is None and obj.get('annotation') is not None:
            obj['annotations'] = obj.pop('annotation')
    else:
        obj = None
    output["data"]= obj
    connection.close()
    return output


def getOtherXML(filename):
    xmlstr=None
    with open(filename, 'r') as nf:
        xmlstr = nf.read()
    if xmlstr is None:
        msg = 'Could not read content from extracted file: ' + filename
        return {'status':400, 'reason':msg, 'data':None}
    return {'status':200, 'reason':'OK', 'data':xmlstr}


def getPmcXml(pmcid):

    # create local cache dir if not yet exists
    tmpdir='tmp/PMC' + pmcid[0:2]
    os.makedirs(tmpdir, exist_ok=True)

    # try to get the name of the xml file in local cache
    nxmlfile = getXmlFilenameFromLocalCache(pmcid)

    # if xml file not found locally...
    if nxmlfile is None:

        # get archive name from remote oa service
        ftpurl = getFtpArchiveUrl(pmcid)
        if ftpurl is None:
            msg = 'Could not get an ftp archive for pmcid: ' + pmcid
            return {'status':400, 'reason':msg, 'data':None}
        # copy the ftp archive file (tar.gz) to local cache
        targzfile = saveFileFromFtp(ftpurl)
        if targzfile is None:
            msg = 'Could not get file from ftp url: ' + ftpurl
            return {'status':400, 'reason':msg, 'data':None}
        # extract nxml file from archive and save it locally
        nxmlfile = getXmlFileFromArchive(targzfile,pmcid)
        if nxmlfile is None:
            msg = 'Could not extract nxml file from archive: ' + targzfile
            return {'status':400, 'reason':msg, 'data':None}

    # return the content of the nxml file
    xmlstr=None
    with open(nxmlfile, 'r') as nf:
        xmlstr = nf.read()
    if xmlstr is None:
        msg = 'Could not read content from extracted file: ' + nxmlfile
        return {'status':400, 'reason':msg, 'data':None}
    return {'status':200, 'reason':'OK', 'data':xmlstr}


def getXmlFilenameFromLocalCache(pmcid):
    dir = 'tmp/PMC' + pmcid[0:2] + '/PMC' + pmcid + '/'
    if os.path.exists(dir):
        filenames = os.listdir(dir)
        for fname in filenames:
            if fname[-3:] == 'xml':
                fullname='file:///home/pmichel/work/jats-parser/tmp/PMC' + pmcid[0:2] + '/PMC' + pmcid + '/' + fname
                print("File found in local cache for " + pmcid + " : " +fullname)
                return dir + fname
    print("No file found in local cache for " + pmcid)
    return None


def getXmlFileFromArchive(archive,pmcid):
    with tarfile.open(archive, "r") as tar:
        for filename in tar.getnames():
            if filename[-4:] == 'nxml':
                subdir='tmp/PMC' + pmcid[0:2]
                tar.extract(filename, path=subdir)
                newname = filename[:-4] + 'xml'
                os.rename(subdir + '/' + filename, subdir + '/' + newname)
                return subdir + '/' + newname
    return None

def getFtpArchiveUrl(pmcid):
    connection = http.client.HTTPSConnection("www.ncbi.nlm.nih.gov")
    url = '/pmc/utils/oa/oa.fcgi?id=' + pmcid
    connection.request("GET", url)
    response = connection.getresponse()
    output={}
    output["status"]=response.status
    output["reason"]=response.reason
    output["data"]=response.read()
    connection.close()
    ftpurl = None
    if output["status"] == 200:
        ftpurl = getPmcFtpUrl(output["data"])
    return ftpurl

def add_pseudo_annot(obj):
    annotations=list()
    obj['annotations']=annotations
    annotated_para=0
    annotated_capt=0
    annotated_cell=0
    for s in obj['body_sections']:
        for c in s['contents']:
            if c['tag'] == 'p':
                if annotated_para > 10: continue
                a_list = get_pseudo_annotations_for_text(c, 'text') # c['text'], c['id'])
                annotations.extend(a_list)
                annotated_para = annotated_para + 1
            if c['tag'] == 'fig' or c['tag'] == 'table':
                if annotated_capt > 10: continue
                a_list = get_pseudo_annotations_for_text(c, 'caption') # c['caption'], c['id'])
                annotations.extend(a_list)
                annotated_capt = annotated_capt + 1
            if c['tag'] == 'table':
                if annotated_cell > 10: continue
                a_list = get_pseudo_annotations_for_cell(c, 5) # c['table_values'], c['id'], 10-annotated_cell)
                annotated_cell = annotated_cell + len(a_list)
                annotations.extend(a_list)
                annotated_capt = annotated_capt + 1


def saveFileFromFtp(ftpurl):
    #
    # extract domain, path and filename from url.
    # Example:
    # ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/20/f2/PMC4804230.tar.gz
    # ['ftp:', '', 'ftp.ncbi.nlm.nih.gov', 'pub', 'pmc', 'oa_package', '20', 'f2', 'PMC4804230.tar.gz']
    #
    url_els=ftpurl.split('/')
    if len(url_els) < 4: return None
    domain = url_els[2]
    remotedir = '/'.join(url_els[3:-1])
    remotefile = url_els[-1]
    subdir=remotefile[0:5]

    localfile = 'tmp/' + subdir + '/' + remotefile
    with FTP(domain, 'anonymous', 'pamichel@infomaniak.ch') as ftp:
        if remotedir != '' : ftp.cwd(remotedir)
        with open(localfile, 'wb') as f:
            ftp.retrbinary('RETR ' + remotefile, f.write)
    return localfile

class GP(BaseHTTPRequestHandler):

    def _set_headers(self,statusCode, content_type):
        self.send_response(statusCode)
        #self.send_header('Content-type', 'application/json')
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_HEAD(self):
        self._set_headers(200)

    def buildErrorResponseObject(self, query, msg):
        response={}
        response['query']=query
        response['success']=False
        error={}
        error['message']=msg
        response['error']=error
        return response

    def buildSuccessResponseObject(self, query, data):
        response={}
        response['query']=query
        response['success']=True
        response['data']=data
        return response

    def sendTextResponse(self, str, statusCode):
        self._set_headers(statusCode, 'text/plain')
        self.wfile.write(bytes(str,'utf-8'))

    def sendJsonResponse(self, obj, statusCode):
        str = json.dumps(obj, sort_keys=True, indent=2)
        self._set_headers(statusCode, 'application/json')
        self.wfile.write(bytes(str,'utf-8'))

    def sendXmlResponse(self, somexml, statusCode):
        self._set_headers(statusCode, 'application/xml; charset=utf-8')
        self.wfile.write(bytes(somexml,'utf-8'))

    def do_GET(self):

        error_msg='ERROR, invalid URL: ' + self.path
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
        if self.path[0:12]=='/getxml/pmc/':
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
            parts=self.path[12:].split('?')
            pmcid = parts[0]
            if pmcid[0:3]=="PMC": pmcid=pmcid[3:]
            msg='handle parsing of pmc file: ' + pmcid
            print(msg)
            output=getPmcXml(pmcid)
            if output['status']==200:
                xmlstr=output['data']
                self.sendXmlResponse(xmlstr, 200)
                return
            else:
                error_msg = str(output['status']) + ' - ' + output['reason']

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
        elif self.path[0:11]=='/parse/pmc/':
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
            parts=self.path[11:].split('?')
            pmcid = parts[0]
            if pmcid[0:3]=="PMC": pmcid=pmcid[3:]
            msg='handle parsing of pmc file: ' + pmcid
            print(msg)
            output=getPmcXml(pmcid)
            if output['status']==200:
                xmlstr=output['data']
                obj = parse_PMC_XML(xmlstr)
                if use_pseudo_annot: add_pseudo_annot(obj)
                response = self.buildSuccessResponseObject(self.path, obj)
                self.sendJsonResponse(response, 200)
                return
            else:
                error_msg = str(output['status']) + ' - ' + output['reason']

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
        elif self.path[0:17]=='/pseudo/api/fetch':
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
            formatPam = False
            formatTxt = False
            withCovoc = False
            id="none"
            col="none"
            params = self.path[17:]
            print(">>>params", params, flush=True)
            for param in self.path.split('?')[1].split("&"):
                print("URL params:", ">"+ param + "<")
                nv = param.split("=")
                if nv[0] == "id":  id = nv[1]
                if nv[0] == "ids":  id = nv[1]
                if nv[0] == "col": col = nv[1]
                if param.lower() == "format=pam" : formatPam = True
                if param.lower() == "format=txt" : formatTxt = True
                if param.lower() == "covoc" : withCovoc = True

            pmcid = id
            if pmcid[0:3]=="PMC": pmcid=pmcid[3:]
            msg='handle parsing of pmc file: ' + pmcid
            print(msg)
            output=getPmcXml(pmcid)
            if output['status']==200:
                xmlstr=output['data']
                obj = parse_PMC_XML(xmlstr)
                doc = { "_id": obj["_id"], "document": obj, "sentences": [], "annotations": [] }

                # pseudo response from fetch service
                response = {"sibils_version": "local", "success": True, "error": "", "warning": "", "collection": "pmc", 
                            "collection_version": "local", "sibils_article_set": [ doc ] }

                if formatTxt==True:
                    print("We are building format txt locally...")
                    publi = response["sibils_article_set"][0]
                    collection = response["collection"]
                    formatter = TextFormatter(publi)
                    full_text = formatter.get_text_format()
                    self.sendTextResponse(full_text, 200)
                    return

                if formatPam==True:
                    print("We are building format pam locally...")
                    publi = response["sibils_article_set"][0]
                    collection = response["collection"]
                    formatter = PmcaFormatter()
                    publi_pam = formatter.get_pmca_format(publi, collection)
                    response["sibils_article_set"][0] = publi_pam

                self.sendJsonResponse(response, 200)
                return
            else:
                error_msg = str(output['status']) + ' - ' + output['reason']

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
        elif self.path[0:13]=='/parse/other/':
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
            fname=self.path[13:]
            msg='handle parsing of file: ' + fname
            print(msg)
            output = getOtherXML(fname)
            if output['status']==200:
                xmlstr=output['data']
                json_publi = parse_PMC_XML(xmlstr)
                json_publi["annotations"] =   [];
                if use_pseudo_annot: add_pseudo_annot(obj)
                json_response = {
                    "sibils_version": "v4.2.5", 
                    "success": True, 
                    "error": "", 
                    "warnings": "", 
                    "collection": "pmc", 
                    "sibils_article_set": [json_publi]
                }
                self.sendJsonResponse(json_response, 200)
                return
            else:
                error_msg = str(output['status']) + ' - ' + output['reason']


        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
        elif self.path[0:12]=='/sibils/pmc/':
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
            parts=self.path[12:].split('?')
            withCovoc = ('covoc' in self.path)
            pmcid = parts[0]
            if pmcid[0:3]!="PMC": pmcid= "PMC" + pmcid
            msg = 'getting sibils data for pmcid: ' + pmcid
            print(msg)
            output = getSibilsPubli(pmcid, withCovoc)
            if output['status']==200:
                obj=output['data']
                response = self.buildSuccessResponseObject(self.path, obj)
                self.sendJsonResponse(response, 200)
                return
            else:
                error_msg = str(output['status']) + ' - ' + output['reason']

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
        elif self.path[0:11]=='/annot/pmc/':
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
            parts=self.path[11:].split('?')
            pmcid = parts[0]
            msg = 'getting annotations of pmc file: ' + pmcid
            print(msg)
            obj = self.buildSuccessResponseObject(self.path, msg)
            self.sendJsonResponse(obj, 200)
            return

        print(error_msg)
        obj = self.buildErrorResponseObject(self.path, error_msg)
        self.sendJsonResponse(obj,400)


def run(server_class=HTTPServer, handler_class=GP, port=8088):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Server running at localhost:8088...')
    httpd.serve_forever()

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Main
# - - - - - - - - - - - - - - - - - - - - - - - - - -
use_pseudo_annot=False
run()
