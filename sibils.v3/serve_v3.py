import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


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

        if self.path[0:15]=='/sibils/v3/pmc/':
            parts=self.path[15:].split('?')
            withCovoc = ('covoc' in self.path)
            pmcid = parts[0]
            if pmcid[0:3]!="PMC": pmcid= "PMC" + pmcid
            msg = 'getting sibils data for pmcid: ' + pmcid
            filename = 'v3_to_v2/' + pmcid + '_v2.json' 
            f_in = open(filename, 'r')
            obj = json.load(f_in)
            f_in.close
            response = self.buildSuccessResponseObject(self.path, obj)
            self.sendJsonResponse(response, 200)
            return

        print(error_msg)
        obj = self.buildErrorResponseObject(self.path, error_msg)
        self.sendJsonResponse(obj,400)


def run(server_class=HTTPServer, handler_class=GP, port=8089):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Server running at localhost:' + str(port) + '...')
    httpd.serve_forever()

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Main
# - - - - - - - - - - - - - - - - - - - - - - - - - -
run()
