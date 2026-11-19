import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib import error, request

from aiops.service import OperationsService
from api_server import make_handler


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=OperationsService()
        cls.httpd=ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.service))
        cls.port=cls.httpd.server_port
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=4)

    def req(self,path,data=None,headers=None):
        payload=json.dumps(data).encode() if data is not None else None
        h={"Content-Type":"application/json"} if data is not None else {}
        h.update(headers or {})
        req=request.Request(f"http://127.0.0.1:{self.port}{path}",data=payload,headers=h)
        try:
            with request.urlopen(req,timeout=3) as res:
                return res.status,res.headers,json.loads(res.read()) if path.startswith("/api/") else res.read()
        except error.HTTPError as exc:
            return exc.code,exc.headers,json.loads(exc.read())

    def test_health_and_security_headers(self):
        status,headers,data=self.req("/api/health")
        self.assertEqual(status,200)
        self.assertEqual(data["aws_production"],"disabled")
        self.assertEqual(headers["X-Frame-Options"],"DENY")
        self.assertIn("frame-ancestors",headers["Content-Security-Policy"])

    def test_static_frontend_served(self):
        status,headers,body=self.req("/")
        self.assertEqual(status,200)
        self.assertIn(b"SentinelOps",body)

    def test_host_header_rejected(self):
        status,_,body=self.req("/api/overview",headers={"Host":"example.org"})
        self.assertEqual(status,403)

    def test_bad_origin_rejected(self):
        status,_,body=self.req("/api/reset",{},headers={"Origin":"https://evil.example"})
        self.assertEqual(status,403)

    def test_full_plan_api_flow(self):
        status,_,plan=self.req("/api/analyze",{"incident_id":"INC-2401"})
        self.assertEqual(status,200)
        status,_,bad=self.req("/api/execute",{"plan_id":plan["id"],"approval_token":"no"})
        self.assertEqual(status,400)
        status,_,approved=self.req("/api/approve",{"plan_id":plan["id"],"confirmation":plan["approval_phrase"],"acknowledged":True})
        self.assertEqual(status,200)
        status,_,result=self.req("/api/execute",{"plan_id":plan["id"],"approval_token":approved["approval_token"]})
        self.assertEqual(status,200)
        self.assertTrue(result["verified"])
        self.assertTrue(result["simulation"])
        self.req("/api/reset",{})

    def test_missing_endpoint(self):
        status,_,body=self.req("/api/unknown")
        self.assertEqual(status,404)
