import sys
import os
from unittest.mock import patch

# Ensure project root is on sys.path so `backend` package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.api.routes.context import fetch_context_for_query


def test_fetch_context_for_query_calls_openai_and_supabase():
    fake_embedding = [0.1, 0.2, 0.3]

    class FakeEmbResp:
        data = [type('E', (), {'embedding': fake_embedding})]

    class FakeOpenAI:
        def embeddings(self):
            raise RuntimeError("should not be used")

    with patch('backend.core.clients.get_openai_client') as mock_openai_client, \
         patch('backend.core.clients.get_supabase_client') as mock_supabase_client:
        mock_openai = mock_openai_client.return_value
        mock_openai.embeddings.create.return_value = FakeEmbResp()

        mock_supabase = mock_supabase_client.return_value
        mock_supabase.rpc.return_value.execute.return_value = type('R', (), {'data': [{'content': 'doc1'}]})

        res = fetch_context_for_query('hello world')
        assert isinstance(res, list)
        assert res[0]['content'] == 'doc1'
