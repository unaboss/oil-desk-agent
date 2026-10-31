from data.fetcher_cot import _parse_cot_html


def test_parse_valid_cot_html():
    html = """
    <html><body><table>
    <tr><th>Non-Comm Long</th><th>Non-Comm Short</th><th>Comm Long</th><th>Comm Short</th><th></th></tr>
    <tr><td>Managed Money</td><td colspan="2">LONG ONLY</td><td>100000</td><td>50000</td><td></td><td></td></tr>
    </table></body></html>
    """
    result = _parse_cot_html(html)
    assert result is None


def test_parse_no_managed_money_row():
    html = """
    <html><body><table>
    <tr><th>Header</th><th>Header2</th></tr>
    <tr><td>Commercial</td><td>Data</td><td>123</td><td>456</td></tr>
    </table></body></html>
    """
    result = _parse_cot_html(html)
    assert result is None


def test_parse_garbage_html():
    result = _parse_cot_html("not even html")
    assert result is None


def test_parse_empty_html():
    result = _parse_cot_html("")
    assert result is None
