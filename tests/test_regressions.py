from types import SimpleNamespace
from unittest.mock import Mock, patch
import logging

import pytest
import requests

from app import app
from utils import main_utils as utils


def pair(address, base, quote, native, usd=1, chain='solana'):
    return SimpleNamespace(
        pair_address=address, base_token=SimpleNamespace(name=base, address=base),
        quote_token=SimpleNamespace(name=quote, address=quote), price_native=native,
        price_usd=usd, liquidity={'usd': 1000000, 'base': 100000, 'quote': 100000},
        chain_id=chain, dex_id='dex', url='https://dexscreener.com/' + address)


@pytest.mark.parametrize('field,value', [
    ('initial_investment', '0'), ('initial_investment', '-1'),
    ('initial_investment', 'nan'), ('initial_investment', 'inf'),
    ('slippage', '-0.1'), ('slippage', '1'), ('slippage', 'nan'),
    ('fee_percentage', '1'), ('fee_percentage', '-1'), ('fee_percentage', 'bad')])
def test_invalid_inputs_never_fetch(field, value):
    with patch.object(utils, 'process_arbitrage_data') as process:
        response = app.test_client().post('/landing_page_data', data={field: value})
    assert response.status_code == 400
    process.assert_not_called()


def test_empty_search_uses_default_and_http_methods_are_preserved():
    with patch.object(utils, 'process_arbitrage_data', return_value=[]) as process:
        assert app.test_client().post('/landing_page_data', data={'search': '  '}).status_code == 200
        assert process.call_args.kwargs['search_address']
    assert app.test_client().post('/health').status_code == 405


def test_nullable_market_data():
    market = pair('pool', 'A', 'B', None, usd=None)
    market.liquidity = None
    normalized = utils.process_token_pairs([market])
    assert normalized[0]['price_usd'] == 0
    assert utils.find_arbitrage_opportunities(normalized, 0, 0, 100, []) == []


def test_scan_triangle_profit_and_distinct_closing_pools():
    markets = [pair('ab', 'A', 'B', 2, 2), pair('ac', 'A', 'C', 6, 2)]
    closing = [pair('bc', 'B', 'C', 2), pair('bc2', 'B', 'C', 2.5)]
    def fetch(query):
        return markets if query == 'A' else closing
    with patch.object(utils, 'fetch_and_cache_pairs', side_effect=fetch):
        result = utils.process_arbitrage_data([], 100, 0, 0, 'A')
    assert len(result) == 2
    assert [r['int_profit'] for r in result] == pytest.approx([50, 20])
    assert len({r['pool_pair3_address'] for r in result}) == 2


def test_balanced_triangle_has_no_profit():
    markets = [pair('ab', 'A', 'B', 2, 2), pair('ac', 'A', 'C', 6, 2)]
    with patch.object(utils, 'fetch_and_cache_pairs', side_effect=lambda q:
                      markets if q == 'A' else [pair('bc', 'B', 'C', 3)]):
        assert utils.process_arbitrage_data([], 100, .001, .003, 'A') == []


def test_direct_opportunities_survive_without_a_third_pool():
    markets = [pair('ab', 'A', 'B', 1), pair('ab2', 'A', 'B', 1.1, 1.1)]
    with patch.object(utils, 'fetch_and_cache_pairs', return_value=markets):
        result = utils.process_arbitrage_data([], 100, 0, 0, 'A')
    assert len(result) == 1
    assert result[0]['int_profit'] == pytest.approx(10)


def test_usd_snapshot_difference_alone_is_not_an_arbitrage():
    markets = [pair('ab', 'A', 'B', 1), pair('ab2', 'A', 'B', 1, 2)]
    assert utils.find_arbitrage_opportunities(utils.process_token_pairs(markets), 0, 0, 100, []) == []


def test_direct_cost_breakdown_reconciles():
    markets = [pair('ab', 'A', 'B', 1), pair('ab2', 'A', 'B', 1.1, 1.1)]
    with patch.object(utils, 'fetch_and_cache_pairs', return_value=markets):
        results = utils.process_arbitrage_data([], 100, 0, .01, 'A', include_unprofitable=True)
    assert len(results) == 2
    winner = results[0]
    assert winner['economics'] == pytest.approx({'investment':100, 'revenue':110, 'fees':2})
    assert winner['int_profit'] == pytest.approx(8)
    assert results[1]['int_profit'] < 0


def test_triangle_cost_breakdown_and_all_routes_mode():
    markets = [pair('ab', 'A', 'B', 2, 2), pair('ac', 'A', 'C', 6, 2)]
    with patch.object(utils, 'fetch_and_cache_pairs', side_effect=lambda q:
                      markets if q == 'A' else [pair('bc', 'B', 'C', 2)]):
        result = utils.process_arbitrage_data([], 100, 0, .01, 'A', include_unprofitable=True)
    assert len(result) == 1
    assert result[0]['economics']['revenue'] == pytest.approx(150)
    assert result[0]['economics']['fees'] == pytest.approx(4.45515)
    assert result[0]['int_profit'] == pytest.approx(45.54485)


def test_balanced_triangle_is_returned_for_review_when_requested():
    markets = [pair('ab', 'A', 'B', 2, 2), pair('ac', 'A', 'C', 6, 2)]
    with patch.object(utils, 'fetch_and_cache_pairs', side_effect=lambda q:
                      markets if q == 'A' else [pair('bc', 'B', 'C', 3)]):
        result = utils.process_arbitrage_data([], 100, 0, 0, 'A', include_unprofitable=True)
    assert len(result) == 1
    assert result[0]['int_profit'] == pytest.approx(0)


def test_cross_chain_and_same_pool_are_excluded():
    market = pair('ab', 'A', 'B', 1)
    markets = [market, market, pair('ab2', 'A', 'B', 2, 2, chain='ethereum')]
    assert utils.find_arbitrage_opportunities(utils.process_token_pairs(markets), 0, 0, 100, []) == []


def test_tiny_native_prices_keep_precision():
    opportunity = {f'pair{n}_price': 1e-10 for n in (1, 2, 3)}
    for n in (1, 2, 3):
        opportunity.update({f'pair{n}_priceNative': 1e-10,
                            f'pair{n}_priceNative_round': '0.0',
                            f'pair{n}_quoteToken_address': 'B'})
    utils.calculate_usd_prices(opportunity)
    assert opportunity['quote_price_usd_3'] == '$1'


def test_upstream_errors_are_retried_and_not_hidden_as_empty_results():
    response = Mock(status_code=429)
    response.raise_for_status.side_effect = requests.HTTPError(response=response)
    with patch.object(utils.requests, 'get', return_value=response) as get, patch.object(utils.time, 'sleep'):
        with pytest.raises(requests.HTTPError):
            utils.fetch_and_cache_pairs('A')
    assert get.call_count == 3
    assert get.call_args.kwargs['timeout'] == (5, 15)


def test_logs_are_bounded():
    handler = utils.ClientLoggingHandler()
    for n in range(600):
        handler.handle(logging.LogRecord('scan', logging.INFO, '', 0, str(n), (), None))
    logs = handler.get_logs()
    assert len(logs) == 500
    assert logs[0] == '100'
    assert handler.get_logs() == []
