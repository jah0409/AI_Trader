import unittest
from api.analyze import app

class TestAnalyzeAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_chat_empty_dict_json(self):
        """Test sending an empty JSON object which evaluates to False in 'if not data:'."""
        response = self.app.post('/api/chat', json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "No JSON body."})

    def test_chat_no_question_or_image(self):
        """Test sending JSON with 'history' but missing both 'question' and 'image_data'."""
        response = self.app.post('/api/chat', json={"history": []})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "No question or image."})

    def test_chat_empty_question_no_image(self):
        """Test sending JSON with an empty/whitespace 'question' and no 'image_data'."""
        response = self.app.post('/api/chat', json={"question": "   ", "history": []})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "No question or image."})

if __name__ == '__main__':
    unittest.main()
