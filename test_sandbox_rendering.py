import unittest
from app import app
from services.personas import DEMO_REGISTRY

class TestSandboxConfiguration(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        # Mocking user agent to be desktop to bypass mobile gate
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    def test_demo_selector_loading(self):
        """Verify that accessing /sandbox without args loads the selector page with all options."""
        response = self.client.get('/sandbox', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        
        # Check if the page is the selector
        self.assertIn("Select a Demo", html)
        
        # Check if it lists the registry items
        for key, demo in DEMO_REGISTRY.items():
            self.assertIn(demo['name'], html)
            self.assertIn(f"demo={key}", html)

    def test_sentinel_loading(self):
        """Verify Sentinel demo loads with correct backend data injection and 3D asset logic."""
        # Using the short code 'sentinel' which maps to 'sentinel_monitor'
        response = self.client.get('/sandbox?demo=sentinel', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')

        # 1. Verify Identity
        self.assertIn("let rawDemo = 'sentinel_monitor'", html) 
        
        # 2. Verify Name
        expected_name = DEMO_REGISTRY['sentinel_monitor']['name']
        # Relaxed check for name presence in the target div (ignoring attributes order)
        self.assertIn('id="target-system"', html)
        self.assertIn(expected_name, html)

        # 3. Verify THREE.js Library Load
        self.assertIn('three.min.js', html)

        # 4. Verify Sentinel Specific 3D Geometry Code
        # We check for the specific Three.js calls that build the mast
        self.assertIn("THREE.CylinderGeometry", html)
        self.assertIn("THREE.TorusGeometry", html)

    def test_robotics_loading(self):
        """Verify Robotics demo loads with correct backend data injection and 3D asset logic."""
        # Using the short code 'robotics' which maps to 'surge_vla'
        response = self.client.get('/sandbox?demo=robotics', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')

        # 1. Verify Identity
        self.assertIn("let rawDemo = 'surge_vla'", html)
        
        # 2. Verify Name
        expected_name = DEMO_REGISTRY['surge_vla']['name']
        # Relaxed check
        self.assertIn('id="target-system"', html)
        self.assertIn(expected_name, html)

        # 3. Verify Robotics Specific 3D Geometry Code
        # We check for the specific Three.js calls that build the hand
        self.assertIn("THREE.BoxGeometry", html)

    def test_mobile_gate(self):
        """Verify mobile users are redirected."""
        mobile_headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'}
        response = self.client.get('/sandbox', headers=mobile_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("mobile", response.data.decode('utf-8').lower())

if __name__ == '__main__':
    unittest.main()
