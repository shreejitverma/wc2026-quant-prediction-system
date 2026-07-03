"""FBref Squad and Player Minutes Scraper."""

import logging
import time

import pandas as pd
import requests

logger = logging.getLogger(__name__)

class FBrefScraper:
    """
    Polite scraper for FBref national team squads.
    Respects rate limits (Sports Reference asks for 1 request every 3 seconds).
    """
    def __init__(self, delay_sec: float = 3.1):
        self.delay_sec = delay_sec
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; WC2026-Bot/1.0; +http://example.com/bot)"
        })

    def get_squad_minutes(self, team_url: str) -> pd.DataFrame:
        """
        Fetches the standard stats table for a national team which includes
        player names, ages, and minutes played.
        """
        logger.info(f"Fetching squad data from {team_url}")
        
        try:
            resp = self.session.get(team_url, timeout=10)
            
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                logger.warning(f"Rate limited by FBref. Sleeping for {retry_after}s...")
                time.sleep(retry_after)
                resp = self.session.get(team_url, timeout=10)
                
            resp.raise_for_status()
            
            # Be polite to Sports Reference
            time.sleep(self.delay_sec)
            
            # Parse HTML for the specific table using BeautifulSoup and Pandas
            
            # Find the 'Standard Stats' table
            # FBref often hides tables in HTML comments to load via JS, but the primary squad table is usually raw
            from io import StringIO
            tables = pd.read_html(StringIO(resp.text), match="Standard Stats")
            
            if not tables:
                return pd.DataFrame()
                
            df = tables[0]
            
            # Flatten multi-index columns if they exist
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(0)
                
            # Filter and clean
            if 'Player' in df.columns and 'Min' in df.columns:
                df = df[['Player', 'Pos', 'Age', 'Min']].dropna(subset=['Player', 'Min'])
                # Remove the summary row at the bottom
                df = df[df['Player'] != 'Squad Total']
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Failed to scrape {team_url}: {e}")
            return pd.DataFrame()

