import pytest
from unittest.mock import Mock, patch
from custom_components.handballnet.api import HandballNetAPI


class TestHandballNetAPI:
    """Test suite for HandballNetAPI class"""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance"""
        hass = Mock()
        return hass

    @pytest.fixture
    def api_client(self, mock_hass):
        """Create HandballNetAPI instance for testing"""
        return HandballNetAPI(mock_hass)

    @pytest.mark.asyncio
    async def test_get_team_info_success_with_logo(self, api_client):
        """Test successful team info retrieval with logo"""
        mock_response_data = {
            "data": {
                "id": "12345",
                "name": "Test Team",
                "logo": "//example.com/logo.png",
                "league": "Test League"
            }
        }
        
        with patch.object(api_client, '_make_request', return_value=mock_response_data):
            with patch('custom_components.handballnet.api.normalize_logo_url', 
                      return_value="https://example.com/logo.png") as mock_normalize:
                
                result = await api_client.get_team_info("12345")
                
                assert result is not None
                assert result["id"] == "12345"
                assert result["name"] == "Test Team"
                assert result["logo"] == "https://example.com/logo.png"
                assert result["league"] == "Test League"
                mock_normalize.assert_called_once_with("//example.com/logo.png")

    @pytest.mark.asyncio
    async def test_get_team_info_success_without_logo(self, api_client):
        """Test successful team info retrieval without logo"""
        mock_response_data = {
            "data": {
                "id": "12345",
                "name": "Test Team",
                "league": "Test League"
            }
        }
        
        with patch.object(api_client, '_make_request', return_value=mock_response_data):
            with patch('custom_components.handballnet.api.normalize_logo_url') as mock_normalize:
                
                result = await api_client.get_team_info("12345")
                
                assert result is not None
                assert result["id"] == "12345"
                assert result["name"] == "Test Team"
                assert result["league"] == "Test League"
                assert "logo" not in result or result.get("logo") is None
                mock_normalize.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_team_info_no_data(self, api_client):
        """Test team info retrieval with no data in response"""
        mock_response_data = {"data": None}
        
        with patch.object(api_client, '_make_request', return_value=mock_response_data):
            result = await api_client.get_team_info("12345")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_team_info_failed_request(self, api_client):
        """Test team info retrieval with failed API request"""
        with patch.object(api_client, '_make_request', return_value=None):
            result = await api_client.get_team_info("12345")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_team_info_empty_response(self, api_client):
        """Test team info retrieval with empty response"""
        mock_response_data = {}
        
        with patch.object(api_client, '_make_request', return_value=mock_response_data):
            result = await api_client.get_team_info("12345")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_team_info_logo_normalization_called(self, api_client):
        """Test that logo normalization is called when logo exists"""
        mock_response_data = {
            "data": {
                "id": "12345",
                "name": "Test Team",
                "logo": "relative/path/logo.png"
            }
        }
        
        with patch.object(api_client, '_make_request', return_value=mock_response_data):
            with patch('custom_components.handballnet.api.normalize_logo_url', 
                      return_value="https://normalized.com/logo.png") as mock_normalize:
                
                result = await api_client.get_team_info("12345")
                
                assert result["logo"] == "https://normalized.com/logo.png"
                mock_normalize.assert_called_once_with("relative/path/logo.png")