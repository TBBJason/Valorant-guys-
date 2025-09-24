import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
from concurrent.futures import ThreadPoolExecutor
import csv
import random
from urllib.parse import urljoin, urlparse
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VLRScraper:
    def __init__(self, delay=1.0):
        """
        Initialize the VLR scraper
        
        Args:
            delay (float): Delay between requests to be respectful to the server
        """
        self.base_url = "https://www.vlr.gg"
        self.delay = delay
        self.session = requests.Session()
        # Add headers to appear as a regular browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def get_page(self, url, max_retries=3):
        """
        Get a page with error handling and retries
        
        Args:
            url (str): URL to fetch
            max_retries (int): Maximum number of retries
            
        Returns:
            BeautifulSoup object or None if failed
        """
        for attempt in range(max_retries):
            try:
                # Add random delay to avoid being blocked
                time.sleep(self.delay + random.uniform(0.1, 0.5))
                
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                logger.info(f"Successfully fetched: {url}")
                return soup
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None

    def get_matches(self, num_pages=5):
        """
        Scrape recent matches from VLR.gg
        
        Args:
            num_pages (int): Number of pages to scrape
            
        Returns:
            list: List of match dictionaries
        """
        matches = []
        
        for page in range(1, num_pages + 1):
            url = f"{self.base_url}/matches/results"
            if page > 1:
                url += f"?page={page}"
            
            logger.info(f"Scraping matches page {page}")
            soup = self.get_page(url)
            
            if not soup:
                continue
            
            # Find match containers
            match_cards = soup.find_all('div', class_='wf-card')
            
            for card in match_cards:
                match_data = self.extract_match_data(card)
                if match_data:
                    matches.append(match_data)
        
        logger.info(f"Scraped {len(matches)} matches")
        return matches

    def extract_match_data(self, match_card):
        """
        Extract data from a match card element
        
        Args:
            match_card: BeautifulSoup element containing match data
            
        Returns:
            dict: Match data or None if extraction failed
        """
        try:
            match_data = {}
            
            # Extract match link and ID
            match_link = match_card.find('a', class_='match-item')
            if match_link and match_link.get('href'):
                match_data['match_url'] = urljoin(self.base_url, match_link['href'])
                # Extract match ID from URL
                match_id = re.search(r'/(\d+)/', match_link['href'])
                match_data['match_id'] = match_id.group(1) if match_id else None
            
            # Extract teams
            teams = match_card.find_all('div', class_='match-item-vs-team-name')
            if len(teams) >= 2:
                match_data['team1'] = teams[0].get_text(strip=True)
                match_data['team2'] = teams[1].get_text(strip=True)
            
            # Extract score
            scores = match_card.find_all('div', class_='match-item-vs-team-score')
            if len(scores) >= 2:
                match_data['team1_score'] = scores[0].get_text(strip=True)
                match_data['team2_score'] = scores[1].get_text(strip=True)
            
            # Extract tournament
            tournament_elem = match_card.find('div', class_='match-item-event')
            if tournament_elem:
                tournament_text = tournament_elem.get_text(strip=True)
                match_data['tournament'] = tournament_text
            
            # Extract date/time
            time_elem = match_card.find('div', class_='match-item-time')
            if time_elem:
                match_data['match_time'] = time_elem.get_text(strip=True)
            
            # Extract format (Bo1, Bo3, etc.)
            format_elem = match_card.find('div', class_='match-item-vs-note')
            if format_elem:
                match_data['format'] = format_elem.get_text(strip=True)
            
            return match_data if match_data.get('team1') and match_data.get('team2') else None
            
        except Exception as e:
            logger.error(f"Error extracting match data: {e}")
            return None

    def get_detailed_match_stats(self, match_url):
        """
        Get detailed statistics for a specific match
        
        Args:
            match_url (str): URL of the match page
            
        Returns:
            dict: Detailed match statistics
        """
        soup = self.get_page(match_url)
        if not soup:
            return None
        
        try:
            match_stats = {}
            
            # Extract map results
            maps_data = []
            map_stats = soup.find_all('div', class_='vm-stats-game')
            
            for map_stat in map_stats:
                map_data = {}
                
                # Map name
                map_name_elem = map_stat.find('div', class_='map')
                if map_name_elem:
                    map_data['map_name'] = map_name_elem.get_text(strip=True)
                
                # Scores for this map
                score_elems = map_stat.find_all('span', class_='score')
                if len(score_elems) >= 2:
                    map_data['team1_score'] = score_elems[0].get_text(strip=True)
                    map_data['team2_score'] = score_elems[1].get_text(strip=True)
                
                maps_data.append(map_data)
            
            match_stats['maps'] = maps_data
            
            # Extract player statistics
            player_stats = []
            stats_tables = soup.find_all('table', class_='wf-table-inset')
            
            for table in stats_tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 8:  # Ensure we have enough columns
                        player_data = {
                            'player_name': cells[0].get_text(strip=True),
                            'agent': cells[1].get_text(strip=True),
                            'acs': cells[2].get_text(strip=True),
                            'kills': cells[3].get_text(strip=True),
                            'deaths': cells[4].get_text(strip=True),
                            'assists': cells[5].get_text(strip=True),
                            'kd_diff': cells[6].get_text(strip=True),
                            'adr': cells[7].get_text(strip=True)
                        }
                        player_stats.append(player_data)
            
            match_stats['players'] = player_stats
            return match_stats
            
        except Exception as e:
            logger.error(f"Error extracting detailed match stats: {e}")
            return None

    def save_to_csv(self, data, filename):
        """
        Save data to CSV file
        
        Args:
            data (list): List of dictionaries to save
            filename (str): Output filename
        """
        if not data:
            logger.warning("No data to save")
            return
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        logger.info(f"Saved {len(data)} records to {filename}")

# Example usage and demonstration
def main():
    print("VLR.gg Valorant Pro Match Scraper")
    print("=" * 50)
    
    # Initialize scraper
    scraper = VLRScraper(delay=1.0)
    
    # Scrape recent matches
    print("Scraping recent matches...")
    matches = scraper.get_matches(num_pages=3)
    
    if matches:
        # Save matches to CSV
        scraper.save_to_csv(matches, 'valorant_matches.csv')
        
        # Display sample data
        print(f"\nFound {len(matches)} matches. Sample data:")
        print("-" * 50)
        for i, match in enumerate(matches[:5]):
            print(f"Match {i+1}:")
            print(f"  Teams: {match.get('team1', 'N/A')} vs {match.get('team2', 'N/A')}")
            print(f"  Score: {match.get('team1_score', 'N/A')} - {match.get('team2_score', 'N/A')}")
            print(f"  Tournament: {match.get('tournament', 'N/A')}")
            print(f"  Format: {match.get('format', 'N/A')}")
            print()
        
        # Get detailed stats for first match with URL
        match_with_url = next((m for m in matches if m.get('match_url')), None)
        if match_with_url:
            print(f"Getting detailed stats for: {match_with_url['team1']} vs {match_with_url['team2']}")
            detailed_stats = scraper.get_detailed_match_stats(match_with_url['match_url'])
            
            if detailed_stats and detailed_stats.get('players'):
                print(f"Found {len(detailed_stats['players'])} player records")
                
                # Save player stats to CSV
                scraper.save_to_csv(detailed_stats['players'], 'valorant_player_stats.csv')
    
    else:
        print("No matches found. Check your connection or the website structure may have changed.")

if __name__ == "__main__":
    main()