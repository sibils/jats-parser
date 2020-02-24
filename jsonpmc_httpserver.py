import os
import json
import tarfile
from ftplib import FTP
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
from process_xml import parse_PMC_XML,getPmcFtpUrl
from pseudo_annot import get_pseudo_annotations_for_text,get_pseudo_annotations_for_cell

def getSibilsPubli(pmcid):
    connection = http.client.HTTPConnection("candy.hesge.ch")
    url = '/SIBiLS/PMC/fetch_deprecated.jsp?ids=' + pmcid + '&with_annotations'
    #url = '/SIBiLS/PMC/fetch_PAM.jsp?ids=' + pmcid + '&with_annotations'
    #url = '/SIBiLS/PMC/fetch.jsp?ids=' + pmcid + '&with_annotations'
    connection.request("GET", url)
    response = connection.getresponse()
    output={}
    output["status"]=response.status
    output["reason"]=response.reason
    data = response.read().decode("utf-8")
    #print("data:" + data[0:100] + " ... " + data[-100:len(data)])
    # some reformatting...
    obj = json.loads(data)
    if len(obj)==1:
        obj = obj[0]
        if obj.get('annotations') is None and obj.get('annotation') is not None:
            obj['annotations'] = obj.pop('annotation')
    else:
        obj = null
    output["data"]= obj
    connection.close()
    return output

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
                fullname='file:///Users/pam/Documents/work/heg/jats-parser/tmp/PMC' + pmcid[0:2] + '/PMC' + pmcid + '/' + fname
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

    def sendStringAsJsonResponse(self, str, statusCode):
        self._set_headers(statusCode, 'application/json')
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

        if self.path[0:12]=='/getxml/pmc/':
            parts=self.path[12:].split('?')
            pmcid = parts[0]
            msg='handle parsing of pmc file: ' + pmcid
            print(msg)
            output=getPmcXml(pmcid)
            if output['status']==200:
                xmlstr=output['data']
                self.sendXmlResponse(xmlstr, 200)
                return
            else:
                error_msg = str(output['status']) + ' - ' + output['reason']

        elif self.path[0:11]=='/parse/pmc/':
            parts=self.path[11:].split('?')
            pmcid = parts[0]
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

        elif self.path[0:12]=='/sibils/pmc/':
            parts=self.path[12:].split('?')
            pmcid = parts[0]
            if pmcid[0:3]!="PMC": pmcid= "PMC" + pmcid
            msg = 'getting sibils data for pmcid: ' + pmcid
            print(msg)
            output = getSibilsPubli(pmcid)
            if output['status']==200:
                obj=output['data']
                response = self.buildSuccessResponseObject(self.path, obj)
                self.sendJsonResponse(response, 200)
                return
            else:
                error_msg = str(output['status']) + ' - ' + output['reason']

        elif self.path[0:11]=='/annot/pmc/':
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
use_pseudo_annot=True
run()
