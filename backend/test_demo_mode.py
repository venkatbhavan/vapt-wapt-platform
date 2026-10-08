import os
import unittest
from fastapi.testclient import TestClient

# Must set DEMO_MODE before importing the app so the middleware reads it
os.environ["DEMO_MODE"] = "true"

from app.main import app

class TestDemoMode(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
    def test_get_is_allowed(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        
    def test_post_scan_job_is_blocked(self):
        response = self.client.post(
            "/api/assessments/1/scan-jobs", 
            json={"active_scan_confirmed": True}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Action disabled in read-only Demo Mode.", response.json()["detail"])
        
    def test_post_ai_analyst_is_allowed(self):
        # AI Analyst uses POST to send context but it is read-only logically
        response = self.client.post("/api/assessments/1/ai-analysis")
        self.assertNotEqual(response.status_code, 403)
        
    def test_post_ai_analyst_invalid_route_blocked(self):
        # Prevent bypasses via prefix/suffix manipulation
        response = self.client.post("/api/assessments/1/ai-analysis/hack")
        self.assertEqual(response.status_code, 403)
        
        response = self.client.post("/api/assessments/1/ai-analysis?bypass=true")
        self.assertNotEqual(response.status_code, 403) # Query param doesn't affect url.path
        
    def test_put_is_blocked(self):
        response = self.client.put("/api/projects/1")
        self.assertEqual(response.status_code, 403)
        
    def test_patch_is_blocked(self):
        response = self.client.patch("/api/assessments/1")
        self.assertEqual(response.status_code, 403)
        
    def test_delete_is_blocked(self):
        response = self.client.delete("/api/projects/1")
        self.assertEqual(response.status_code, 403)

    def test_post_retest_is_blocked(self):
        response = self.client.post("/api/findings/1/retests")
        self.assertEqual(response.status_code, 403)

    def test_post_report_share_is_blocked(self):
        response = self.client.post("/api/reports/1/shares")
        self.assertEqual(response.status_code, 403)
        
    def test_post_assessment_is_blocked(self):
        response = self.client.post("/api/projects/1/assessments")
        self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
