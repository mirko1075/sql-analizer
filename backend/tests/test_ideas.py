import sys
import os
from unittest.mock import patch

# Ensure project root is on sys.path so `backend` package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.api.routes.ideas import analyze_idea


class Req:
    def __init__(self, idea_text):
        self.idea_text = idea_text


def test_analyze_idea_returns_parsed_json():
    fake_context = [{'content': 'c1'}, {'content': 'c2'}]
    fake_parsed = {'summary': 's', 'relevance_score': 90, 'suggested_feature': 'f', 'reasoning': 'r'}

    with patch('backend.api.routes.ideas.fetch_context_for_query') as mock_fetch, \
         patch('backend.core.clients.get_openai_client') as mock_openai_client:
        mock_fetch.return_value = fake_context
        mock_openai = mock_openai_client.return_value
        # Emulate responses.create returning an object with output_parsed
        mock_openai.responses.create.return_value = type('R', (), {'output_parsed': fake_parsed})

        resp = analyze_idea(Req('my idea'))
        assert resp == fake_parsed
