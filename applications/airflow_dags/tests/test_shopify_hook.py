"""
Comprehensive tests for ShopifyHook throttling resilience features.

This test suite covers the enhanced ShopifyHook with improved rate limiting,
exponential backoff, and throttle retry mechanisms.
"""

import pytest
import time
import random
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import HTTPError, RequestException
import json

from airflow.exceptions import AirflowException

# Import the ShopifyHook we're testing
from src.hooks.shopify_hook import ShopifyHook


class TestShopifyHookThrottling:
    """Test suite for ShopifyHook throttling resilience features."""

    def setup_method(self):
        """Setup test environment."""
        self.mock_shop_domain = "test-shop"
        self.mock_access_token = "test-token"
        self.mock_query = "query { shop { name } }"

        # Mock successful response
        self.mock_success_response = {
            "data": {"shop": {"name": "Test Shop", "myshopifyDomain": "test-shop.myshopify.com"}}
        }

        # Mock 429 response
        self.mock_429_response = Mock()
        self.mock_429_response.status_code = 429
        self.mock_429_response.headers = {"Retry-After": "5"}
        self.mock_429_response.json.return_value = {"errors": [{"message": "Throttled"}]}

    def test_hook_initialization_with_throttle_params(self):
        """Test ShopifyHook initialization with throttle parameters."""
        hook = ShopifyHook(
            shop_domain=self.mock_shop_domain,
            access_token=self.mock_access_token,
            throttle_retry_attempts=10,
            throttle_backoff_factor=3.0,
            max_throttle_wait=120,
        )

        assert hook.throttle_retry_attempts == 10
        assert hook.throttle_backoff_factor == 3.0
        assert hook.max_throttle_wait == 120
        assert "throttle_retries" in hook._metrics
        assert "throttle_retry_successes" in hook._metrics

    def test_hook_initialization_with_defaults(self):
        """Test ShopifyHook initialization with default throttle parameters."""
        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token)

        assert hook.throttle_retry_attempts == 5  # default
        assert hook.throttle_backoff_factor == 2.0  # default
        assert hook.max_throttle_wait == 60  # default

    @patch("random.uniform")
    def test_calculate_throttle_backoff_with_retry_after(self, mock_random):
        """Test backoff calculation when Retry-After header is provided."""
        mock_random.return_value = 0.3

        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, max_throttle_wait=60)

        # Test with Retry-After header
        backoff_time = hook._calculate_throttle_backoff(attempt=1, retry_after=10)

        # Should use retry_after + jitter, capped at max_throttle_wait
        expected = min(10 + 0.3, 60)
        assert backoff_time == expected
        mock_random.assert_called_once_with(0.1, 0.5)

    @patch("random.uniform")
    def test_calculate_throttle_backoff_exponential(self, mock_random):
        """Test exponential backoff calculation without Retry-After header."""
        mock_random.return_value = 0.2

        hook = ShopifyHook(
            shop_domain=self.mock_shop_domain,
            access_token=self.mock_access_token,
            throttle_backoff_factor=2.0,
            max_throttle_wait=60,
        )

        # Test different attempts
        backoff_1 = hook._calculate_throttle_backoff(attempt=1)
        backoff_2 = hook._calculate_throttle_backoff(attempt=2)
        backoff_3 = hook._calculate_throttle_backoff(attempt=3)

        # Expected: 1 * (2^0) + jitter = 1 + 0.2 = 1.2
        # Expected: 1 * (2^1) + jitter = 2 + 0.4 = 2.4
        # Expected: 1 * (2^2) + jitter = 4 + 0.8 = 4.8

        assert backoff_1 == 1.0 + (0.2 * 1.0)  # base + jitter
        assert backoff_2 == 2.0 + (0.2 * 2.0)  # exponential + jitter
        assert backoff_3 == 4.0 + (0.2 * 4.0)  # exponential + jitter

    @patch("random.uniform")
    def test_calculate_throttle_backoff_max_cap(self, mock_random):
        """Test that backoff time is capped at max_throttle_wait."""
        mock_random.return_value = 0.2

        hook = ShopifyHook(
            shop_domain=self.mock_shop_domain,
            access_token=self.mock_access_token,
            throttle_backoff_factor=2.0,
            max_throttle_wait=5,  # Very low cap for testing
        )

        # High attempt should be capped
        backoff_time = hook._calculate_throttle_backoff(attempt=10)
        assert backoff_time == 5  # Should be capped at max_throttle_wait

    @patch("src.hooks.shopify_hook.time.sleep")
    @patch("requests.Session.post")
    def test_execute_graphql_success_no_retry(self, mock_post, mock_sleep):
        """Test successful GraphQL execution without retries."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_success_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, enable_metrics=True)

        result = hook.execute_graphql(self.mock_query)

        assert result == self.mock_success_response
        assert hook._metrics["successful_requests"] == 1
        assert hook._metrics["throttle_retries"] == 0
        assert hook._metrics["throttle_retry_successes"] == 0
        mock_sleep.assert_not_called()

    @patch("src.hooks.shopify_hook.time.sleep")
    @patch("requests.Session.post")
    def test_execute_graphql_429_retry_success(self, mock_post, mock_sleep):
        """Test 429 error with successful retry."""
        # First call returns 429, second call succeeds
        mock_429_response = Mock()
        mock_429_response.status_code = 429
        mock_429_response.headers = {"Retry-After": "2"}

        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = self.mock_success_response
        mock_success_response.raise_for_status = Mock()

        mock_post.side_effect = [mock_429_response, mock_success_response]

        hook = ShopifyHook(
            shop_domain=self.mock_shop_domain,
            access_token=self.mock_access_token,
            enable_metrics=True,
            throttle_retry_attempts=3,
        )

        with patch.object(hook, "_calculate_throttle_backoff", return_value=1.0) as mock_backoff:
            result = hook.execute_graphql(self.mock_query)

        assert result == self.mock_success_response
        assert hook._metrics["rate_limit_hits"] == 1
        assert hook._metrics["throttle_retries"] == 1
        assert hook._metrics["throttle_retry_successes"] == 1
        assert hook._metrics["successful_requests"] == 1

        # Verify backoff was calculated and sleep was called
        mock_backoff.assert_called_once_with(1, 2)  # attempt 1, retry_after 2
        mock_sleep.assert_called_once_with(1.0)

    @patch("src.hooks.shopify_hook.time.sleep")
    @patch("requests.Session.post")
    def test_execute_graphql_429_retry_exhausted(self, mock_post, mock_sleep):
        """Test 429 error with exhausted retries."""
        # All calls return 429
        mock_429_response = Mock()
        mock_429_response.status_code = 429
        mock_429_response.headers = {"Retry-After": "2"}
        mock_post.return_value = mock_429_response

        hook = ShopifyHook(
            shop_domain=self.mock_shop_domain,
            access_token=self.mock_access_token,
            enable_metrics=True,
            throttle_retry_attempts=2,  # Low number for testing
        )

        with patch.object(hook, "_calculate_throttle_backoff", return_value=1.0):
            with pytest.raises(AirflowException) as exc_info:
                hook.execute_graphql(self.mock_query)

        assert "Rate limited (429) - exceeded 2 retry attempts" in str(exc_info.value)
        assert hook._metrics["rate_limit_hits"] == 3  # Three 429 responses (initial + 2 retries)
        assert hook._metrics["throttle_retries"] == 2  # Two retry attempts
        assert hook._metrics["throttle_retry_successes"] == 0
        assert hook._metrics["failed_requests"] == 1  # Final exhaustion counts as failure

        # Should have slept twice (for 2 retry attempts)
        assert mock_sleep.call_count == 2

    @patch("requests.Session.post")
    def test_execute_graphql_non_429_error_no_retry(self, mock_post):
        """Test that non-429 HTTP errors are not retried."""
        # Mock 500 error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, enable_metrics=True)

        with pytest.raises(AirflowException) as exc_info:
            hook.execute_graphql(self.mock_query)

        assert "HTTP error" in str(exc_info.value)
        assert hook._metrics["failed_requests"] == 1
        assert hook._metrics["throttle_retries"] == 0

        # Should only have made one call (no retries)
        assert mock_post.call_count == 1

    @patch("requests.Session.post")
    def test_execute_graphql_request_exception_no_retry(self, mock_post):
        """Test that RequestException errors are not retried."""
        mock_post.side_effect = RequestException("Network error")

        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, enable_metrics=True)

        with pytest.raises(AirflowException) as exc_info:
            hook.execute_graphql(self.mock_query)

        assert "HTTP request failed" in str(exc_info.value)
        assert hook._metrics["failed_requests"] == 1
        assert hook._metrics["throttle_retries"] == 0

        # Should only have made one call (no retries)
        assert mock_post.call_count == 1

    @patch("src.hooks.shopify_hook.time.sleep")
    @patch("requests.Session.post")
    def test_execute_graphql_multiple_429_retries(self, mock_post, mock_sleep):
        """Test multiple 429 errors followed by success."""
        # Mock responses: 429, 429, success
        mock_429_response = Mock()
        mock_429_response.status_code = 429
        mock_429_response.headers = {}  # No Retry-After header

        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = self.mock_success_response
        mock_success_response.raise_for_status = Mock()

        mock_post.side_effect = [mock_429_response, mock_429_response, mock_success_response]

        hook = ShopifyHook(
            shop_domain=self.mock_shop_domain,
            access_token=self.mock_access_token,
            enable_metrics=True,
            throttle_retry_attempts=5,
        )

        with patch.object(hook, "_calculate_throttle_backoff", side_effect=[1.0, 2.0]) as mock_backoff:
            result = hook.execute_graphql(self.mock_query)

        assert result == self.mock_success_response
        assert hook._metrics["rate_limit_hits"] == 2  # Two 429s
        assert hook._metrics["throttle_retries"] == 2  # Two retry attempts
        assert hook._metrics["throttle_retry_successes"] == 1  # Final success
        assert hook._metrics["successful_requests"] == 1

        # Verify backoff was calculated for each retry
        assert mock_backoff.call_count == 2
        mock_backoff.assert_any_call(1, None)  # First retry, no Retry-After
        mock_backoff.assert_any_call(2, None)  # Second retry, no Retry-After

        # Verify sleep was called twice
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    @patch("requests.Session.post")
    def test_execute_graphql_json_decode_error_no_retry(self, mock_post):
        """Test that JSON decode errors are not retried."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response

        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, enable_metrics=True)

        with pytest.raises(AirflowException) as exc_info:
            hook.execute_graphql(self.mock_query)

        assert "Failed to parse JSON response" in str(exc_info.value)
        assert hook._metrics["failed_requests"] == 1
        assert hook._metrics["throttle_retries"] == 0

    @patch("requests.Session.post")
    def test_execute_graphql_graphql_errors_no_retry(self, mock_post):
        """Test that GraphQL errors are not retried."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"errors": [{"message": "Field 'invalid' doesn't exist"}]}
        mock_post.return_value = mock_response

        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, enable_metrics=True)

        with pytest.raises(AirflowException) as exc_info:
            hook.execute_graphql(self.mock_query)

        assert "GraphQL errors" in str(exc_info.value)
        assert "Field 'invalid' doesn't exist" in str(exc_info.value)
        assert hook._metrics["failed_requests"] == 1
        assert hook._metrics["throttle_retries"] == 0

    def test_reset_metrics_includes_throttle_metrics(self):
        """Test that reset_metrics includes new throttle metrics."""
        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, enable_metrics=True)

        # Modify metrics
        hook._metrics["throttle_retries"] = 5
        hook._metrics["throttle_retry_successes"] = 3

        # Reset metrics
        hook.reset_metrics()

        assert hook._metrics["throttle_retries"] == 0
        assert hook._metrics["throttle_retry_successes"] == 0
        assert "throttle_retries" in hook._metrics
        assert "throttle_retry_successes" in hook._metrics

    def test_get_performance_metrics_includes_throttle_data(self):
        """Test that performance metrics include throttle data."""
        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, enable_metrics=True)

        # Set some test metrics
        hook._metrics["total_requests"] = 10
        hook._metrics["successful_requests"] = 8
        hook._metrics["failed_requests"] = 2
        hook._metrics["throttle_retries"] = 3
        hook._metrics["throttle_retry_successes"] = 2

        metrics = hook.get_performance_metrics()

        assert metrics["throttle_retries"] == 3
        assert metrics["throttle_retry_successes"] == 2
        assert metrics["success_rate"] == 0.8  # 8/10
        assert metrics["failure_rate"] == 0.2  # 2/10

    @patch("src.hooks.shopify_hook.time.sleep")
    @patch("requests.Session.post")
    def test_execute_graphql_with_retry_after_header(self, mock_post, mock_sleep):
        """Test that Retry-After header is respected in backoff calculation."""
        mock_429_response = Mock()
        mock_429_response.status_code = 429
        mock_429_response.headers = {"Retry-After": "10"}

        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = self.mock_success_response
        mock_success_response.raise_for_status = Mock()

        mock_post.side_effect = [mock_429_response, mock_success_response]

        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token)

        # Mock the backoff calculation to return a specific value
        with patch.object(hook, "_calculate_throttle_backoff", return_value=5.5) as mock_backoff:
            result = hook.execute_graphql(self.mock_query)

        assert result == self.mock_success_response

        # Verify that Retry-After value was passed to backoff calculation
        mock_backoff.assert_called_once_with(1, 10)  # attempt 1, retry_after 10
        mock_sleep.assert_called_once_with(5.5)

    @patch("src.hooks.shopify_hook.time.sleep")
    @patch("requests.Session.post")
    def test_execute_graphql_without_retry_after_header(self, mock_post, mock_sleep):
        """Test backoff calculation when no Retry-After header is present."""
        mock_429_response = Mock()
        mock_429_response.status_code = 429
        mock_429_response.headers = {}  # No Retry-After header

        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = self.mock_success_response
        mock_success_response.raise_for_status = Mock()

        mock_post.side_effect = [mock_429_response, mock_success_response]

        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token)

        with patch.object(hook, "_calculate_throttle_backoff", return_value=2.5) as mock_backoff:
            result = hook.execute_graphql(self.mock_query)

        assert result == self.mock_success_response

        # Verify that None was passed for retry_after
        mock_backoff.assert_called_once_with(1, None)  # attempt 1, no retry_after
        mock_sleep.assert_called_once_with(2.5)

    def test_hook_initialization_logging_includes_throttle_config(self):
        """Test that initialization logging includes throttle configuration."""
        with patch("src.hooks.shopify_hook.logger") as mock_logger:
            hook = ShopifyHook(
                shop_domain=self.mock_shop_domain,
                access_token=self.mock_access_token,
                throttle_retry_attempts=8,
                max_throttle_wait=90,
            )

        # Check that the info log was called with throttle config
        mock_logger.info.assert_called()
        log_message = mock_logger.info.call_args[0][0]
        assert "throttle_retries: 8" in log_message
        assert "max_throttle_wait: 90s" in log_message


class TestShopifyHookThrottlingEdgeCases:
    """Test edge cases and boundary conditions for throttling."""

    def setup_method(self):
        """Setup test environment."""
        self.mock_shop_domain = "test-shop"
        self.mock_access_token = "test-token"

    def test_zero_retry_attempts(self):
        """Test behavior with zero retry attempts."""
        hook = ShopifyHook(
            shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, throttle_retry_attempts=0
        )

        assert hook.throttle_retry_attempts == 0

        with patch("requests.Session.post") as mock_post:
            mock_429_response = Mock()
            mock_429_response.status_code = 429
            mock_429_response.headers = {}
            mock_post.return_value = mock_429_response

            with pytest.raises(AirflowException) as exc_info:
                hook.execute_graphql("query { shop { name } }")

            assert "Rate limited (429) - exceeded 0 retry attempts" in str(exc_info.value)
            # Should only make one call (no retries)
            assert mock_post.call_count == 1

    def test_very_high_retry_attempts(self):
        """Test behavior with very high retry attempts (should still respect max_throttle_wait)."""
        hook = ShopifyHook(
            shop_domain=self.mock_shop_domain,
            access_token=self.mock_access_token,
            throttle_retry_attempts=100,
            max_throttle_wait=1,  # Very low to test capping
        )

        # Test that high attempts still get capped
        backoff_time = hook._calculate_throttle_backoff(attempt=50)
        assert backoff_time <= 1  # Should be capped at max_throttle_wait

    @patch("random.uniform")
    def test_backoff_factor_edge_cases(self, mock_random):
        """Test backoff calculation with edge case factors."""
        mock_random.return_value = 0.0  # No jitter for predictable testing

        # Test with backoff factor of 1.0 (no exponential growth)
        hook = ShopifyHook(
            shop_domain=self.mock_shop_domain,
            access_token=self.mock_access_token,
            throttle_backoff_factor=1.0,
            max_throttle_wait=60,
        )

        backoff_1 = hook._calculate_throttle_backoff(attempt=1)
        backoff_2 = hook._calculate_throttle_backoff(attempt=2)
        backoff_3 = hook._calculate_throttle_backoff(attempt=3)

        # With factor 1.0, all should be base_delay (1.0)
        assert backoff_1 == 1.0
        assert backoff_2 == 1.0
        assert backoff_3 == 1.0

    def test_metrics_disabled(self):
        """Test that throttle functionality works when metrics are disabled."""
        hook = ShopifyHook(shop_domain=self.mock_shop_domain, access_token=self.mock_access_token, enable_metrics=False)

        assert not hook.enable_metrics

        with patch("src.hooks.shopify_hook.time.sleep"), patch("requests.Session.post") as mock_post:

            mock_429_response = Mock()
            mock_429_response.status_code = 429
            mock_429_response.headers = {"Retry-After": "1"}

            mock_success_response = Mock()
            mock_success_response.status_code = 200
            mock_success_response.json.return_value = {"data": {"shop": {"name": "Test"}}}
            mock_success_response.raise_for_status = Mock()

            mock_post.side_effect = [mock_429_response, mock_success_response]

            # Should still work without throwing errors
            result = hook.execute_graphql("query { shop { name } }")
            assert result["data"]["shop"]["name"] == "Test"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short", "--color=yes"])
