import requests_mock

from wc2026.ingest.squads import FBrefScraper


def test_fbref():
    scraper = FBrefScraper(delay_sec=0.0)
    with requests_mock.Mocker() as m:
        html = '''<html>
        <table class="stats_table" id="stats_standard_10">
            <caption>Standard Stats</caption>
            <thead>
                <tr><th>Player</th><th>Pos</th><th>Age</th><th>Min</th></tr>
            </thead>
            <tbody>
                <tr><td>Player A</td><td>FW</td><td>25</td><td>90</td></tr>
                <tr><td>Squad Total</td><td></td><td></td><td>90</td></tr>
            </tbody>
        </table>
        </html>'''
        m.get("https://fbref.com/test", text=html)
        df = scraper.get_squad_minutes("https://fbref.com/test")
        assert not df.empty
        assert len(df) == 1
        assert df.iloc[0]['Player'] == 'Player A'
        
        # 429 logic
        m.get("https://fbref.com/test429", [{'status_code': 429, 'headers': {'Retry-After': '0'}}, {'text': html, 'status_code': 200}])
        df2 = scraper.get_squad_minutes("https://fbref.com/test429")
        assert len(df2) == 1
        
        # empty html
        m.get("https://fbref.com/empty", text="<html></html>")
        df3 = scraper.get_squad_minutes("https://fbref.com/empty")
        assert df3.empty
        
        # 500 error
        m.get("https://fbref.com/err", status_code=500)
        df4 = scraper.get_squad_minutes("https://fbref.com/err")
        assert df4.empty
