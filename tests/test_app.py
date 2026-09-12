import pytest
from flask import url_for
import json
from unittest.mock import patch, Mock
from app import app
from utils.main_utils import process_arbitrage_data

@pytest.fixture
def client():
    """
    Fixture that creates a test client for the Flask application.

    Returns:
        FlaskClient: A test client instance with testing mode enabled

    Side effects:
        - Configures the Flask app for testing
    """
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """
    Test the index route of the application.

    Args:
        client (FlaskClient): The test client fixture

    Test cases:
        1. GET request to the root path ('/')

    Expected outputs:
        - 200 status code
        - Response contains HTML doctype

    Side effects: None

    Assertions:
        - Response status code is 200
        - Response data contains '<!DOCTYPE html>'
    """
    response = client.get('/')
    assert response.status_code == 200
    assert b'<!DOCTYPE html>' in response.data

def test_health_check(client):
    """
    Test the health check endpoint of the application.

    Args:
        client (FlaskClient): The test client fixture

    Test cases:
        1. GET request to '/health' endpoint

    Expected outputs:
        - 200 status code
        - JSON response with status and timestamp

    Side effects: None

    Assertions:
        - Response status code is 200
        - Response contains 'status' field with value 'healthy'
        - Response contains 'timestamp' field
    """
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert data['status'] == 'healthy'
    assert 'timestamp' in data

@patch('utils.main_utils.process_arbitrage_data')
def test_fetch_arbitrage_opportunities(mock_process, client):
    """
    Test the endpoint for fetching arbitrage opportunities.

    Args:
        mock_process (MagicMock): Mocked process_arbitrage_data function
        client (FlaskClient): The test client fixture

    Test cases:
        1. POST request to '/landing_page_data' with valid data

    Inputs:
        - initial_investment: '10000'
        - slippage: '0.0005'
        - fee_percentage: '0.0003'
        - search: '0x123'

    Mock behavior:
        - process_arbitrage_data returns a list with one opportunity

    Expected outputs:
        - 200 status code
        - JSON response containing list of opportunities

    Assertions:
        - Response status code is 200
        - Response is a list
        - Response contains expected opportunity fields
    """
    mock_process.return_value = [
        {
            'pair1': 'Token1/Token2',
            'pair2': 'Token2/Token3',
            'profit': '$100.00'
        }
    ]

    data = {
        'initial_investment': '10000',
        'slippage': '0.0005',
        'fee_percentage': '0.0003',
        'search': '0x123'
    }

    response = client.post('/landing_page_data', data=data)
    assert response.status_code == 200

    result = json.loads(response.data)
    assert isinstance(result, list)
    assert len(result) > 0
    assert 'pair1' in result[0]
    assert 'profit' in result[0]

def test_fetch_arbitrage_opportunities_invalid_input(client):
    """
    Test the arbitrage opportunities endpoint with invalid input data.

    Args:
        client (FlaskClient): The test client fixture

    Test cases:
        1. POST request with invalid investment amount

    Inputs:
        - initial_investment: 'invalid' (non-numeric)
        - Other valid parameters

    Expected outputs:
        - 500 status code
        - JSON response with error message

    Side effects: None

    Assertions:
        - Response status code is 500
        - Response contains 'error' field
    """
    data = {
        'initial_investment': 'invalid',
        'slippage': '0.0005',
        'fee_percentage': '0.0003',
        'search': '0x123'
    }

    response = client.post('/landing_page_data', data=data)
    assert response.status_code == 400

    result = json.loads(response.data)
    assert 'error' in result

@patch('app.client_handler')
def test_get_logs(mock_client_handler, client):
    """
    Test the logs retrieval endpoint.

    Args:
        mock_client_handler (MagicMock): Mocked client handler
        client (FlaskClient): The test client fixture

    Test cases:
        1. GET request to '/get_logs'

    Mock behavior:
        - client_handler.get_logs returns a list of log entries

    Expected outputs:
        - 200 status code
        - JSON response containing list of logs

    Assertions:
        - Response status code is 200
        - Response is a list with expected length
    """
    mock_client_handler.get_logs.return_value = ['Log entry 1', 'Log entry 2']

    response = client.get('/get_logs')
    assert response.status_code == 200

    result = json.loads(response.data)
    assert isinstance(result, list)
    assert len(result) == 2

def test_error_handlers(client):
    """
    Test various error handlers in the application.

    Args:
        client (FlaskClient): The test client fixture

    Test cases:
        1. 404 Not Found error (nonexistent route)
        2. 500 Internal Server Error (simulated error in process_arbitrage_data)

    Mock behavior:
        - process_arbitrage_data raises an exception for 500 error test

    Expected outputs:
        - 404 response for nonexistent route
        - 500 response for internal server error
        - JSON responses with appropriate error messages

    Assertions:
        - Response status codes match expected errors
        - Error messages are correct
    """
    response = client.get('/nonexistent_route')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Not Found'

    with patch('utils.main_utils.process_arbitrage_data') as mock_process:
        mock_process.side_effect = Exception('Test error')
        response = client.post('/landing_page_data', data={
            'initial_investment': '10000',
            'slippage': '0.0005',
            'fee_percentage': '0.0003',
            'search': '0x123'
        })
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Internal Server Error'

@pytest.mark.integration
def test_end_to_end_flow(client):
    """
    Integration test for testing the complete application flow.

    Args:
        client (FlaskClient): The test client fixture

    Test cases:
        1. Health check
        2. Fetch arbitrage opportunities
        3. Retrieve logs

    Mock behavior:
        - process_arbitrage_data returns mock opportunities
        - client_handler.get_logs returns mock logs

    Expected outputs:
        - Successful responses from all endpoints
        - Correct data structure in responses

    Side effects: None

    Assertions:
        - All responses have 200 status code
        - Responses contain expected data structure
    """
    health_response = client.get('/health')
    assert health_response.status_code == 200

    with patch('utils.main_utils.process_arbitrage_data') as mock_process:
        mock_process.return_value = [
            {
                'pair1': 'Token1/Token2',
                'pair2': 'Token2/Token3',
                'profit': '$100.00'
            }
        ]

        data = {
            'initial_investment': '10000',
            'slippage': '0.0005',
            'fee_percentage': '0.0003',
            'search': '0x123'
        }

        response = client.post('/landing_page_data', data=data)
        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result) > 0

    with patch('app.client_handler') as mock_client_handler:
        mock_client_handler.get_logs.return_value = ['Test log entry']
        logs_response = client.get('/get_logs')
        assert logs_response.status_code == 200
        logs = json.loads(logs_response.data)
        assert len(logs) > 0
