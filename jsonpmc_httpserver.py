from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import http.client
from process_xml import parse_PMC_XML


def getPmcXml(pmcid):
    connection = http.client.HTTPSConnection("www.ebi.ac.uk")
    url = '/europepmc/webservices/rest/PMC' + pmcid + '/fullTextXML'
    connection.request("GET", url)
    response = connection.getresponse()
    output={}
    output["status"]=response.status
    output["reason"]=response.reason
    output["data"]=response.read()
    connection.close()
    return output


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
            print(output)
            if output['status']==200:
                xmlstr=output['data']
                obj = parse_PMC_XML(xmlstr)
                response = self.buildSuccessResponseObject(self.path, obj)
                self.sendResponse(response, 200)
                return
            else:
                error_msg  ='EuropePMC server said '
                error_msg += str(output['status']) + ' - ' + output['reason']

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
