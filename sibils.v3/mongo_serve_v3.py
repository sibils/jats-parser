import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from mongo_pam_fetcher import MongoPamFetcher


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

        # get data from sibils v3 bib, ana, sen and reformat it for viewer (fetch_PAM equivalent)
        if self.path[0:21]=='/mongo/fetch/pam/pmc/':
            parts=self.path[21:].split('?')
            withCovoc = ('covoc' in self.path)
            pmcid = parts[0]
            if pmcid[0:3]!="PMC": pmcid= "PMC" + pmcid
            msg = 'getting sibils data for pmcid: ' + pmcid
            #obj = mongo_pam_fetcher.fetch_v3_data(pmcid)
            obj = mongo_pam_fetcher.fetch_pam_data(pmcid)
            response = self.buildSuccessResponseObject(self.path, obj)
            self.sendJsonResponse(response, 200)
            return

        # get data from sibils v3 bib, ana, sen (fetch v3 equivalent)
        elif self.path[0:20]=='/mongo/fetch/v3/pmc/':
            parts=self.path[20:].split('?')
            withCovoc = ('covoc' in self.path)
            pmcid = parts[0]
            if pmcid[0:3]!="PMC": pmcid= "PMC" + pmcid
            msg = 'getting sibils data for pmcid: ' + pmcid
            obj = mongo_pam_fetcher.fetch_v3_data(pmcid)
            response = self.buildSuccessResponseObject(self.path, obj)
            self.sendJsonResponse(response, 200)
            return
        # get data from some preprocessed sample files
        elif self.path[0:15]=='/sibils/v3/pmc/':
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
    
    # start http server
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Server running at localhost:' + str(port) + '...')
    httpd.serve_forever()

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Main
# - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':

    # init mongo db connection and collections to be fetched
    mongo_pam_fetcher = MongoPamFetcher(host="localhost", port=27018, db_name= "sibils_v3_1")
    mongo_pam_fetcher.set_collections(bibcol_name = "pmcbib23", anacol_name="pmcana23", sencol_name="pmcsen23" )
    # start http server
    run()
