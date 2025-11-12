"""
HTTP proxy for forwarding requests to backend services.
"""
import logging
from typing import Optional, Dict, Any
import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


class ProxyClient:
    """
    HTTP proxy client for forwarding requests to backend services.

    Handles:
    - Request forwarding with headers
    - Response streaming
    - Error handling
    - Timeout management
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize proxy client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    async def forward_request(
        self,
        request: Request,
        target_url: str,
        additional_headers: Optional[Dict[str, str]] = None
    ) -> Response:
        """
        Forward HTTP request to target service.

        Args:
            request: Incoming FastAPI request
            target_url: Target service URL (including path)
            additional_headers: Additional headers to add

        Returns:
            FastAPI Response with proxied content
        """
        try:
            # Prepare headers
            headers = dict(request.headers)

            # Remove hop-by-hop headers
            hop_by_hop_headers = [
                'connection', 'keep-alive', 'proxy-authenticate',
                'proxy-authorization', 'te', 'trailers',
                'transfer-encoding', 'upgrade', 'host'
            ]
            for header in hop_by_hop_headers:
                headers.pop(header, None)

            # Add additional headers
            if additional_headers:
                headers.update(additional_headers)

            # Get request body
            body = await request.body()

            # Forward request
            logger.debug(f"Forwarding {request.method} {target_url}")

            response = await self.client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )

            # Prepare response headers
            response_headers = dict(response.headers)

            # Remove hop-by-hop headers from response
            for header in hop_by_hop_headers:
                response_headers.pop(header, None)

            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type')
            )

        except httpx.TimeoutException:
            logger.error(f"Timeout forwarding request to {target_url}")
            return Response(
                content='{"error": "Gateway timeout - backend service did not respond in time"}',
                status_code=504,
                media_type="application/json"
            )

        except httpx.ConnectError:
            logger.error(f"Connection error forwarding request to {target_url}")
            return Response(
                content='{"error": "Bad gateway - unable to connect to backend service"}',
                status_code=502,
                media_type="application/json"
            )

        except Exception as e:
            logger.error(f"Error forwarding request to {target_url}: {e}")
            return Response(
                content=f'{{"error": "Gateway error: {str(e)}"}}',
                status_code=500,
                media_type="application/json"
            )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
