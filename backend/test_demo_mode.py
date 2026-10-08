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
        # Even if 404, we want to see that it's NOT a 403 Forbidden
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
        # Might return 422 Unprocessable Entity due to missing payload, but NOT 403
        self.assertNotEqual(response.status_code, 403)
        
    def test_delete_is_blocked(self):
        response = self.client.delete("/api/projects/1")
        self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
