# VLR.gg Valorant Pro Match Scraper
# Comprehensive web scraper for Valorant professional match data

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
from datetime import datetime
import json
import re
import random
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vlr_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ValorantProScraper:
    """
    Comprehensive scraper for VLR.gg Valorant professional match data
    
    Features:
    - Scrape completed matches with detailed statistics
    - Scrape upcoming matches for betting analysis
    - Extract player performance data
    - Team performance metrics
    - Tournament information
    - Rate limiting and respectful scraping
    """
    
    def __init__(self, delay=1.5, max_workers=3):
        """
        Initialize the Valorant Pro Scraper
        
        Args:
            delay (float): Delay between requests in seconds
            max_workers (int): Maximum concurrent threads
        """
        self.base_url = "https://www.vlr.gg"
        self.delay = delay
        self.max_workers = max_workers
        self.session = requests.Session()
        
        # Set headers to appear as a regular browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })

    def safe_get_text(self, element, default=""):
        """Safely extract text from a BeautifulSoup element"""
        if element:
            return element.get_text(strip=True)
        return default

    def extract_number(self, text):
        """Extract number from text, handling various formats"""
        if not text:
            return None
        number_str = re.sub(r'[^\d.-]', '', str(text))
        try:
            return float(number_str) if '.' in number_str else int(number_str)
        except (ValueError, TypeError):
            return None

    def get_page_with_retry(self, url, max_retries=3):
        """
        Fetch page with retry logic and rate limiting
        
        Args:
            url (str): URL to fetch
            max_retries (int): Maximum retry attempts
            
        Returns:
            BeautifulSoup object or None
        """
        for attempt in range(max_retries):
            try:
                # Rate limiting with random jitter
                time.sleep(self.delay + random.uniform(0.1, 0.5))
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    logger.info(f"Successfully fetched: {url}")
                    return soup
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None

    def scrape_completed_matches(self, num_pages=3, detailed_stats=True):
        """
        Scrape completed matches from VLR.gg results
        
        Args:
            num_pages (int): Number of pages to scrape
            detailed_stats (bool): Whether to fetch detailed match statistics
            
        Returns:
            list: List of match dictionaries
        """
        logger.info(f"Starting to scrape {num_pages} pages of completed matches")
        all_matches = []
        
        for page in range(1, num_pages + 1):
            url = f"{self.base_url}/matches/results"
            if page > 1:
                url += f"?page={page}"
            
            soup = self.get_page_with_retry(url)
            if not soup:
                continue
            
            # Find match links
            match_links = soup.find_all('a', class_='wf-module-item')
            
            logger.info(f"Found {len(match_links)} matches on page {page}")
            
            for link in match_links[:10]:  # Limit per page to avoid overloading
                if not link.get('href'):
                    continue
                
                match_url = self.base_url + link['href']
                
                if detailed_stats:
                    match_data = self.get_detailed_match_info(match_url)
                else:
                    match_data = self.extract_basic_match_info(link, match_url)
                
                if match_data:
                    all_matches.append(match_data)
        
        logger.info(f"Scraped {len(all_matches)} completed matches total")
        return all_matches

    def scrape_upcoming_matches(self, limit=20):
        """
        Scrape upcoming matches for betting analysis
        
        Args:
            limit (int): Maximum number of matches to scrape
            
        Returns:
            list: List of upcoming match dictionaries
        """
        logger.info("Scraping upcoming matches for betting analysis")
        url = f"{self.base_url}/matches"
        soup = self.get_page_with_retry(url)
        
        if not soup:
            return []
        
        matches = []
        match_cards = soup.find_all('a', class_='wf-module-item')[:limit]
        
        for card in match_cards:
            try:
                match_data = {}
                
                # Extract match URL and ID
                if card.get('href'):
                    match_data['match_url'] = self.base_url + card['href']
                    match_id = re.search(r'/(\d+)/', card['href'])
                    match_data['match_id'] = match_id.group(1) if match_id else None
                
                # Extract teams
                team_elements = card.find_all('div', class_='match-item-vs-team-name')
                if len(team_elements) >= 2:
                    match_data['team1'] = self.safe_get_text(team_elements[0])
                    match_data['team2'] = self.safe_get_text(team_elements[1])
                
                # Extract tournament info
                event_elem = card.find('div', class_='match-item-event-series')
                if event_elem:
                    match_data['tournament'] = self.safe_get_text(event_elem)
                
                # Extract time
                time_elem = card.find('div', class_='match-item-time')
                if time_elem:
                    match_data['scheduled_time'] = self.safe_get_text(time_elem)
                
                # Extract format (Bo1, Bo3, etc.)
                format_elem = card.find('div', class_='match-item-vs-note')
                if format_elem:
                    match_data['format'] = self.safe_get_text(format_elem)
                
                # Add betting relevance score
                match_data['betting_relevance'] = self.calculate_betting_relevance(match_data)
                
                if match_data.get('team1') and match_data.get('team2'):
                    matches.append(match_data)
                    
            except Exception as e:
                logger.error(f"Error extracting upcoming match data: {e}")
                continue
        
        logger.info(f"Found {len(matches)} upcoming matches")
        return matches

    def get_detailed_match_info(self, match_url):
        """
        Extract comprehensive information from a match page
        
        Args:
            match_url (str): URL of the match page
            
        Returns:
            dict: Detailed match information
        """
        soup = self.get_page_with_retry(match_url)
        if not soup:
            return None
        
        try:
            match_data = {'match_url': match_url}
            
            # Extract match header info
            header = soup.find('div', class_='match-header')
            if header:
                # Team names
                teams = header.find_all('div', class_='match-header-vs-team-name')
                if len(teams) >= 2:
                    match_data['team1'] = self.safe_get_text(teams[0])
                    match_data['team2'] = self.safe_get_text(teams[1])
                
                # Scores
                scores = header.find_all('div', class_='match-header-vs-team-score')
                if len(scores) >= 2:
                    match_data['team1_score'] = self.extract_number(self.safe_get_text(scores[0]))
                    match_data['team2_score'] = self.extract_number(self.safe_get_text(scores[1]))
                
                # Match format
                format_elem = header.find('div', class_='match-header-vs-note')
                if format_elem:
                    match_data['format'] = self.safe_get_text(format_elem)
            
            # Extract tournament info
            tournament_elem = soup.find('div', class_='match-header-event')
            if tournament_elem:
                match_data['tournament'] = self.safe_get_text(tournament_elem)
            
            # Extract match date/time
            date_elem = soup.find('div', class_='match-header-date')
            if date_elem:
                match_data['match_date'] = self.safe_get_text(date_elem)
            
            # Extract map data
            maps_data = []
            map_headers = soup.find_all('div', class_='vm-stats-game-header')
            
            for map_header in map_headers:
                map_info = {}
                
                # Map name
                map_name = map_header.find('div', class_='map')
                if map_name:
                    map_name_text = self.safe_get_text(map_name)
                    # Clean up map name (remove "PICK" etc.)
                    map_info['map_name'] = re.sub(r'PICK.*', '', map_name_text).strip()
                
                # Map scores
                map_scores = map_header.find_all('span', class_='score')
                if len(map_scores) >= 2:
                    map_info['team1_rounds'] = self.extract_number(self.safe_get_text(map_scores[0]))
                    map_info['team2_rounds'] = self.extract_number(self.safe_get_text(map_scores[1]))
                
                # Determine map winner
                if map_info.get('team1_rounds') and map_info.get('team2_rounds'):
                    if map_info['team1_rounds'] > map_info['team2_rounds']:
                        map_info['winner'] = match_data.get('team1', 'team1')
                    else:
                        map_info['winner'] = match_data.get('team2', 'team2')
                
                maps_data.append(map_info)
            
            match_data['maps'] = maps_data
            match_data['total_maps'] = len(maps_data)
            
            # Calculate additional metrics
            if match_data.get('team1_score') is not None and match_data.get('team2_score') is not None:
                match_data['total_maps_played'] = match_data['team1_score'] + match_data['team2_score']
                match_data['winner'] = match_data['team1'] if match_data['team1_score'] > match_data['team2_score'] else match_data['team2']
                match_data['was_upset'] = self.detect_upset(match_data)
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error extracting detailed match info from {match_url}: {e}")
            return None

    def extract_basic_match_info(self, card_element, match_url):
        """Extract basic match information from a match card"""
        try:
            match_data = {'match_url': match_url}
            
            # Extract teams
            teams = card_element.find_all('div', class_='match-item-vs-team-name')
            if len(teams) >= 2:
                match_data['team1'] = self.safe_get_text(teams[0])
                match_data['team2'] = self.safe_get_text(teams[1])
            
            # Extract scores
            scores = card_element.find_all('div', class_='match-item-vs-team-score')
            if len(scores) >= 2:
                match_data['team1_score'] = self.extract_number(self.safe_get_text(scores[0]))
                match_data['team2_score'] = self.extract_number(self.safe_get_text(scores[1]))
            
            # Extract tournament
            tournament_elem = card_element.find('div', class_='match-item-event')
            if tournament_elem:
                match_data['tournament'] = self.safe_get_text(tournament_elem)
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error extracting basic match info: {e}")
            return None

    def calculate_betting_relevance(self, match_data):
        """
        Calculate a betting relevance score for a match
        
        Args:
            match_data (dict): Match information
            
        Returns:
            float: Relevance score (0-10)
        """
        score = 5.0  # Base score
        
        # Higher tier tournaments get higher scores
        tournament = match_data.get('tournament', '').lower()
        if 'champions' in tournament:
            score += 3.0
        elif 'masters' in tournament:
            score += 2.0
        elif 'vct' in tournament:
            score += 1.5
        
        # Best-of format affects betting interest
        format_text = match_data.get('format', '').lower()
        if 'bo5' in format_text:
            score += 1.0
        elif 'bo3' in format_text:
            score += 0.5
        
        # Well-known teams increase betting interest
        team1 = match_data.get('team1', '').lower()
        team2 = match_data.get('team2', '').lower()
        
        popular_teams = ['sentinels', 'fnatic', 'loud', 'paper rex', 'nrg', 'drx', 'team liquid']
        if any(team in team1 or team in team2 for team in popular_teams):
            score += 1.0
        
        return min(score, 10.0)  # Cap at 10

    def detect_upset(self, match_data):
        """
        Detect if a match result was likely an upset
        (This is a simplified heuristic)
        """
        # This would need more sophisticated logic in a real implementation
        # For now, we'll use a simple heuristic based on team names
        team1 = match_data.get('team1', '').lower()
        team2 = match_data.get('team2', '').lower()
        winner = match_data.get('winner', '').lower()
        
        tier1_teams = ['sentinels', 'fnatic', 'loud', 'paper rex', 'nrg']
        tier2_teams = ['drx', 'team liquid', 'g2 esports', 'team heretics']
        
        # If a tier 2 team beat a tier 1 team, might be an upset
        if (team1 in tier1_teams and team2 in tier2_teams and winner == team2) or \
           (team2 in tier1_teams and team1 in tier2_teams and winner == team1):
            return True
        
        return False

    def get_team_performance_metrics(self, team_name, matches_data, time_window_days=30):
        """
        Calculate performance metrics for a specific team
        
        Args:
            team_name (str): Name of the team
            matches_data (list): List of match data
            time_window_days (int): Time window for recent performance
            
        Returns:
            dict: Team performance metrics
        """
        team_matches = []
        
        for match in matches_data:
            if match.get('team1') == team_name or match.get('team2') == team_name:
                team_matches.append(match)
        
        if not team_matches:
            return None
        
        # Calculate basic metrics
        wins = 0
        total_matches = len(team_matches)
        total_maps_won = 0
        total_maps_played = 0
        upsets_caused = 0
        
        for match in team_matches:
            team1_score = match.get('team1_score', 0)
            team2_score = match.get('team2_score', 0)
            
            if match.get('team1') == team_name:
                if team1_score > team2_score:
                    wins += 1
                total_maps_won += team1_score
            else:
                if team2_score > team1_score:
                    wins += 1
                total_maps_won += team2_score
            
            total_maps_played += team1_score + team2_score
            
            if match.get('was_upset') and match.get('winner') == team_name:
                upsets_caused += 1
        
        # Calculate rates
        win_rate = wins / total_matches if total_matches > 0 else 0
        map_win_rate = total_maps_won / total_maps_played if total_maps_played > 0 else 0
        
        return {
            'team_name': team_name,
            'matches_played': total_matches,
            'wins': wins,
            'losses': total_matches - wins,
            'win_rate': round(win_rate, 3),
            'maps_won': total_maps_won,
            'maps_played': total_maps_played,
            'map_win_rate': round(map_win_rate, 3),
            'upsets_caused': upsets_caused,
            'recent_matches': team_matches[:5]  # Last 5 matches
        }

    def save_to_csv(self, data, filename):
        """
        Save data to CSV file with proper formatting
        
        Args:
            data (list): List of dictionaries to save
            filename (str): Output filename
        """
        if not data:
            logger.warning("No data to save")
            return
        
        # Convert complex nested data to JSON strings for CSV compatibility
        processed_data = []
        for item in data:
            processed_item = {}
            for key, value in item.items():
                if isinstance(value, (list, dict)):
                    processed_item[key] = json.dumps(value)
                else:
                    processed_item[key] = value
            processed_data.append(processed_item)
        
        df = pd.DataFrame(processed_data)
        df.to_csv(filename, index=False)
        logger.info(f"Saved {len(data)} records to {filename}")

    def run_comprehensive_scrape(self, 
                                completed_pages=2, 
                                upcoming_limit=15, 
                                detailed_stats=True,
                                save_files=True):
        """
        Run a comprehensive scraping session
        
        Args:
            completed_pages (int): Number of pages of completed matches
            upcoming_limit (int): Number of upcoming matches
            detailed_stats (bool): Whether to get detailed statistics
            save_files (bool): Whether to save results to files
            
        Returns:
            dict: All scraped data
        """
        logger.info("Starting comprehensive VLR.gg scraping session")
        
        results = {}
        
        # Scrape completed matches
        logger.info("Phase 1: Scraping completed matches...")
        completed_matches = self.scrape_completed_matches(
            num_pages=completed_pages, 
            detailed_stats=detailed_stats
        )
        results['completed_matches'] = completed_matches
        
        if save_files and completed_matches:
            self.save_to_csv(completed_matches, f'valorant_completed_matches_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
        
        # Scrape upcoming matches
        logger.info("Phase 2: Scraping upcoming matches...")
        upcoming_matches = self.scrape_upcoming_matches(limit=upcoming_limit)
        results['upcoming_matches'] = upcoming_matches
        
        if save_files and upcoming_matches:
            self.save_to_csv(upcoming_matches, f'valorant_upcoming_matches_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
        
        # Calculate team performance metrics
        if completed_matches:
            logger.info("Phase 3: Calculating team performance metrics...")
            teams = set()
            for match in completed_matches:
                if match.get('team1'):
                    teams.add(match['team1'])
                if match.get('team2'):
                    teams.add(match['team2'])
            
            team_metrics = []
            for team in list(teams)[:20]:  # Limit to top 20 teams
                metrics = self.get_team_performance_metrics(team, completed_matches)
                if metrics:
                    team_metrics.append(metrics)
            
            results['team_metrics'] = team_metrics
            
            if save_files and team_metrics:
                # Remove complex nested data for CSV
                csv_metrics = []
                for metric in team_metrics:
                    csv_metric = {k: v for k, v in metric.items() if k != 'recent_matches'}
                    csv_metrics.append(csv_metric)
                
                self.save_to_csv(csv_metrics, f'valorant_team_metrics_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
        
        logger.info(f"Comprehensive scraping completed. Results: {len(results)} datasets")
        return results


# Example usage and demonstration
def main():
    """
    Main function demonstrating the scraper usage
    """
    print("VLR.gg Valorant Professional Match Data Scraper")
    print("=" * 60)
    print("Features:")
    print("- Completed matches with detailed statistics")
    print("- Upcoming matches for betting analysis")
    print("- Team performance metrics")
    print("- Rate limiting and respectful scraping")
    print("- Export to CSV format")
    print("=" * 60)
    
    # Initialize scraper
    scraper = ValorantProScraper(delay=1.5, max_workers=3)
    
    # Run comprehensive scraping
    try:
        results = scraper.run_comprehensive_scrape(
            completed_pages=2,
            upcoming_limit=15,
            detailed_stats=True,
            save_files=True
        )
        
        # Display summary
        print("\n" + "=" * 40)
        print("SCRAPING RESULTS SUMMARY")
        print("=" * 40)
        
        if results.get('completed_matches'):
            print(f"✓ Completed matches: {len(results['completed_matches'])}")
            
        if results.get('upcoming_matches'):
            print(f"✓ Upcoming matches: {len(results['upcoming_matches'])}")
            
        if results.get('team_metrics'):
            print(f"✓ Team performance metrics: {len(results['team_metrics'])}")
            
            # Show top 5 teams by win rate
            top_teams = sorted(results['team_metrics'], 
                             key=lambda x: x.get('win_rate', 0), 
                             reverse=True)[:5]
            
            print("\nTop 5 Teams by Win Rate:")
            for i, team in enumerate(top_teams, 1):
                print(f"{i}. {team['team_name']}: {team['win_rate']:.1%} "
                      f"({team['wins']}-{team['losses']})")
        
        # Show some upcoming high-relevance matches
        if results.get('upcoming_matches'):
            high_relevance = [m for m in results['upcoming_matches'] 
                            if m.get('betting_relevance', 0) >= 7.0]
            
            if high_relevance:
                print(f"\nHigh betting relevance upcoming matches ({len(high_relevance)}):")
                for match in high_relevance[:3]:
                    print(f"- {match.get('team1')} vs {match.get('team2')} "
                          f"({match.get('tournament', 'Unknown tournament')})")
        
        print("\n✓ All data saved to CSV files with timestamps")
        print("✓ Check the generated files for detailed analysis")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        print(f"Error occurred: {e}")
        print("Check the log file for detailed error information")


if __name__ == "__main__":
    main()