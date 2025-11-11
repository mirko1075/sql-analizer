"""
SaaS Backend HTTP Client.
Securely communicates with DBPower AI Cloud SaaS backend.
"""
import requests
from typing import List, Dict, Any, Optional
import logging
import time
from datetime import datetime
import json

from ..collectors.base import SlowQuery


logger = logging.getLogger(__name__)


class SaaSClientError(Exception):
    """Exception raised for SaaS client errors."""
    pass


class SaaSClient:
    """
    HTTP client for DBPower AI Cloud SaaS backend.

    Handles:
    - API key authentication
    - Retry logic with exponential backoff
    - Request/response logging
    - Error handling
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        agent_id: str,
        verify_ssl: bool = True,
        timeout: int = 30,
        retry_attempts: int = 3,
        retry_delay: int = 5
    ):
        """
        Initialize SaaS client.

        Args:
            api_url: Base URL of SaaS API
            api_key: Organization API key
            agent_id: Client agent ID
            verify_ssl: Verify SSL certificates
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.agent_id = agent_id
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # Statistics
        self.stats = {
            'requests_sent': 0,
            'requests_failed': 0,
            'requests_succeeded': 0,
            'queries_sent': 0,
            'last_request_time': None,
            'last_error': None,
        }

    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for requests.

        Returns:
            Dictionary of headers
        """
        return {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
            'X-Agent-ID': self.agent_id,
            'User-Agent': f'DBPower-Client-Agent/{self.agent_id}',
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: Request body (for POST/PUT)
            params: Query parameters

        Returns:
            Response object

        Raises:
            SaaSClientError: If request fails after all retries
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        for attempt in range(1, self.retry_attempts + 1):
            try:
                logger.debug(f"Request attempt {attempt}/{self.retry_attempts}: {method} {url}")

                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    verify=self.verify_ssl,
                    timeout=self.timeout
                )

                self.stats['requests_sent'] += 1
                self.stats['last_request_time'] = datetime.utcnow()

                # Check for errors
                if response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(error_msg)

                    # Don't retry client errors (4xx), only server errors (5xx)
                    if response.status_code < 500:
                        self.stats['requests_failed'] += 1
                        self.stats['last_error'] = error_msg
                        raise SaaSClientError(error_msg)

                    # Retry server errors
                    if attempt < self.retry_attempts:
                        wait_time = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                        logger.info(f"Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.stats['requests_failed'] += 1
                        self.stats['last_error'] = error_msg
                        raise SaaSClientError(error_msg)

                # Success
                self.stats['requests_succeeded'] += 1
                logger.debug(f"Request succeeded: {response.status_code}")
                return response

            except requests.exceptions.Timeout:
                error_msg = f"Request timeout after {self.timeout}s"
                logger.warning(error_msg)

                if attempt < self.retry_attempts:
                    logger.info(f"Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    self.stats['requests_failed'] += 1
                    self.stats['last_error'] = error_msg
                    raise SaaSClientError(error_msg)

            except requests.exceptions.RequestException as e:
                error_msg = f"Request failed: {str(e)}"
                logger.error(error_msg)

                if attempt < self.retry_attempts:
                    logger.info(f"Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    self.stats['requests_failed'] += 1
                    self.stats['last_error'] = error_msg
                    raise SaaSClientError(error_msg)

        # Should never reach here
        raise SaaSClientError("Max retries exceeded")

    def send_slow_queries(
        self,
        queries: List[SlowQuery],
        organization_id: int,
        team_id: int,
        identity_id: int
    ) -> Dict[str, Any]:
        """
        Send slow queries to SaaS backend.

        Args:
            queries: List of SlowQuery objects
            organization_id: Organization ID
            team_id: Team ID
            identity_id: Identity ID

        Returns:
            Response data from server

        Raises:
            SaaSClientError: If request fails
        """
        if not queries:
            logger.warning("No queries to send")
            return {'queries_received': 0}

        # Convert queries to dicts
        queries_data = [q.to_dict() for q in queries]

        # Prepare payload
        payload = {
            'agent_id': self.agent_id,
            'organization_id': organization_id,
            'team_id': team_id,
            'identity_id': identity_id,
            'queries': queries_data,
            'timestamp': datetime.utcnow().isoformat(),
        }

        logger.info(f"Sending {len(queries)} slow queries to SaaS backend")

        try:
            response = self._make_request('POST', '/client/queries', data=payload)
            result = response.json()

            self.stats['queries_sent'] += len(queries)

            logger.info(f"Successfully sent {len(queries)} queries")
            return result

        except SaaSClientError as e:
            logger.error(f"Failed to send queries: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on SaaS backend.

        Returns:
            Health check response

        Raises:
            SaaSClientError: If health check fails
        """
        try:
            response = self._make_request('GET', '/health')
            return response.json()

        except SaaSClientError as e:
            logger.error(f"Health check failed: {e}")
            raise

    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get agent status from SaaS backend.

        Returns:
            Agent status information

        Raises:
            SaaSClientError: If request fails
        """
        try:
            response = self._make_request('GET', f'/client/agents/{self.agent_id}')
            return response.json()

        except SaaSClientError as e:
            logger.error(f"Failed to get agent status: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.

        Returns:
            Statistics dictionary
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset client statistics."""
        self.stats = {
            'requests_sent': 0,
            'requests_failed': 0,
            'requests_succeeded': 0,
            'queries_sent': 0,
            'last_request_time': None,
            'last_error': None,
        }
