from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import http.client
from ftplib import FTP
from process_xml import parse_PMC_XML,getPmcFtpUrl
import tarfile
import os

def getPmcXml(pmcid):

    os.makedirs('tmp', exist_ok=True)

    ftpurl = getFtpArchiveUrl(pmcid)
    if ftpurl is None:
        msg = 'Could not get an ftp archive for pmcid: ' + pmcid
        return {'status':400, 'reason':msg, 'data':None}
    targzfile = saveFileFromFtp(ftpurl)
    if targzfile is None:
        msg = 'Could not get file from ftp url: ' + ftpurl
        return {'status':400, 'reason':msg, 'data':None}
    nxmlfile = getNxmlFileFromArchive(targzfile)
    if nxmlfile is None:
        msg = 'Could not extract nxml file from archive: ' + targzfile
        return {'status':400, 'reason':msg, 'data':None}
    xmlstr=None
    with open(nxmlfile, 'r') as nf:
        xmlstr = nf.read()
    if xmlstr is None:
        msg = 'Could not read content from extracted file: ' + nxmlfile
        return {'status':400, 'reason':msg, 'data':None}

    return {'status':200, 'reason':'OK', 'data':xmlstr}


def getNxmlFileFromArchive(archive):
    with tarfile.open(archive, "r") as tar:
        for filename in tar.getnames():
            if filename[-4:] == 'nxml':
                print(filename)
                tar.extract(filename, path='tmp')
                return 'tmp/' + filename
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
    localfile = 'tmp/' + remotefile
    with FTP(domain, 'anonymous', 'pamichel@infomaniak.ch') as ftp:
        if remotedir != '' : ftp.cwd(remotedir)
        with open(localfile, 'wb') as f:
            ftp.retrbinary('RETR ' + remotefile, f.write)
    return localfile

class GP(BaseHTTPRequestHandler):
    def _set_headers(self,statusCode):
        self.send_response(statusCode)
        self.send_header('Content-type', 'application/json')
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

    def sendResponse(self, obj, statusCode):
        str = json.dumps(obj, sort_keys=True, indent=2)
        self._set_headers(statusCode)
        self.wfile.write(bytes(str,'utf-8'))

    def do_GET(self):

        error_msg='ERROR, invalid URL: ' + self.path

        if self.path[0:11]=='/parse/pmc/':
            parts=self.path[11:].split('?')
            pmcid = parts[0]
            msg='handle parsing of pmc file: ' + pmcid
            print(msg)
            output=getPmcXml(pmcid)
            if output['status']==200:
                xmlstr=output['data']
                obj = parse_PMC_XML(xmlstr)
                response = self.buildSuccessResponseObject(self.path, obj)
                self.sendResponse(response, 200)
                return
            else:
                error_msg = str(output['status']) + ' - ' + output['reason']

        elif self.path[0:11]=='/annot/pmc/':
            parts=self.path[11:].split('?')
            pmcid = parts[0]
            msg = 'getting annotations of pmc file: ' + pmcid
            print(msg)
            obj = self.buildSuccessResponseObject(self.path, msg)
            self.sendResponse(obj, 200)
            return

        print(error_msg)
        obj = self.buildErrorResponseObject(self.path, error_msg)
        self.sendResponse(obj,400)


def run(server_class=HTTPServer, handler_class=GP, port=8088):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Server running at localhost:8088...')
    httpd.serve_forever()

run()
