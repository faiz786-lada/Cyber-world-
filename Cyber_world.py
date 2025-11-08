#!/usr/bin/env python3
"""
🌐 Cyber World Search Engine
A powerful, self-hosted search engine built with Python
GitHub: https://github.com/yourusername/cyber-world-search
"""

import requests
import sqlite3
import time
import os
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import json
from datetime import datetime

class CyberWorldSearchEngine:
    def __init__(self, db_name='cyber_world.db'):
        self.engine_name = "Cyber World Search"
        self.version = "2.0"
        self.db_path = db_name
        self.setup_database()
        print(f"🚀 {self.engine_name} v{self.version} Initialized!")
    
    def setup_database(self):
        """Database setup with error handling"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # Create tables
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS websites 
                (id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT, 
                 content TEXT, last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_index 
                (id INTEGER PRIMARY KEY, word TEXT, website_id INTEGER,
                 frequency INTEGER DEFAULT 1)
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_history 
                (id INTEGER PRIMARY KEY, query TEXT, results_count INTEGER,
                 search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
            ''')
            
            self.conn.commit()
            
        except Exception as e:
            print(f"❌ Database setup error: {e}")
            sys.exit(1)
    
    def is_valid_url(self, url):
        """URL validate karta hai"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def clean_text(self, text):
        """Text saaf karta hai"""
        if not text:
            return ""
        # Remove special characters, extra spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip().lower()
    
    def extract_meaningful_text(self, soup):
        """Meaningful text extract karta hai"""
        # Remove script and style elements
        for script in soup(["script", "style", "meta", "nav"]):
            script.decompose()
        
        # Get text from important tags
        meaningful_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'article', 'section']
        texts = []
        
        for tag in meaningful_tags:
            elements = soup.find_all(tag)
            for element in elements:
                text = element.get_text().strip()
                if len(text) > 20:  # Only meaningful content
                    texts.append(text)
        
        return ' '.join(texts) if texts else soup.get_text()
    
    def crawl_website(self, start_url, max_pages=20, delay=2):
        """Website crawl karta hai aur data collect karta hai"""
        print(f"\n🕷️ {self.engine_name} Crawler Starting...")
        print(f"🎯 Target: {start_url}")
        print(f"📄 Max Pages: {max_pages}")
        print(f"⏰ Delay: {delay} seconds")
        print("-" * 50)
        
        if not self.is_valid_url(start_url):
            print("❌ Invalid URL format")
            return 0
        
        visited = set()
        to_visit = [start_url]
        crawled_count = 0
        
        try:
            while to_visit and crawled_count < max_pages:
                url = to_visit.pop(0)
                
                if url in visited:
                    continue
                    
                try:
                    print(f"🔍 Crawling [{crawled_count + 1}/{max_pages}]: {url}")
                    
                    # Website se data fetch karo
                    headers = {
                        'User-Agent': 'CyberWorldBot/1.0 (+https://github.com/cyberworld)',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    }
                    
                    response = requests.get(url, timeout=10, headers=headers)
                    response.raise_for_status()
                    
                    # Content type check karo
                    if 'text/html' not in response.headers.get('content-type', '').lower():
                        print(f"⚠️  Skipping non-HTML content: {url}")
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Title aur content extract karo
                    title = soup.title.string if soup.title else "No Title"
                    meaningful_content = self.extract_meaningful_text(soup)
                    clean_content = self.clean_text(meaningful_content)[:8000]  # Limit content
                    
                    if len(clean_content) < 50:  # Too little content
                        print(f"⚠️  Skipping page with little content: {url}")
                        continue
                    
                    # Database mein save karo
                    self.cursor.execute('''
                        INSERT OR REPLACE INTO websites (url, title, content) 
                        VALUES (?, ?, ?)
                    ''', (url, title, clean_content))
                    
                    website_id = self.cursor.lastrowid
                    
                    # Words ko index karo
                    words = clean_content.split()
                    word_count = {}
                    
                    for word in words:
                        if 3 <= len(word) <= 30 and word.isalpha():  # Meaningful words
                            word_count[word] = word_count.get(word, 0) + 1
                    
                    # Search index update karo
                    for word, freq in word_count.items():
                        self.cursor.execute('''
                            INSERT INTO search_index (word, website_id, frequency) 
                            VALUES (?, ?, ?)
                        ''', (word, website_id, freq))
                    
                    self.conn.commit()
                    visited.add(url)
                    crawled_count += 1
                    
                    print(f"✅ Saved: {title[:60]}...")
                    
                    # New links find karo (same domain only)
                    domain = urlparse(url).netloc
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        full_url = urljoin(url, href)
                        
                        if (self.is_valid_url(full_url) and 
                            urlparse(full_url).netloc == domain and
                            full_url not in visited and 
                            full_url not in to_visit and
                            crawled_count < max_pages):
                            to_visit.append(full_url)
                    
                    # Respect robots.txt - delay
                    time.sleep(delay)
                    
                except requests.exceptions.RequestException as e:
                    print(f"❌ Network error with {url}: {e}")
                    continue
                except Exception as e:
                    print(f"❌ Error crawling {url}: {str(e)[:100]}")
                    continue
            
            print(f"\n🎊 Crawling Complete! {crawled_count} pages saved to database.")
            return crawled_count
            
        except KeyboardInterrupt:
            print(f"\n⏹️ Crawling interrupted. {crawled_count} pages saved.")
            return crawled_count
    
    def search(self, query, limit=15):
        """Search query process karta hai"""
        if not query or not query.strip():
            return []
        
        clean_query = query.strip()
        print(f"🔎 Searching for: '{clean_query}'")
        
        query_words = [self.clean_text(word) for word in clean_query.split() if len(word) > 2]
        
        if not query_words:
            return []
        
        results = []
        
        try:
            # Advanced ranking: frequency and multiple word matches
            placeholders = ','.join('?' * len(query_words))
            
            self.cursor.execute(f'''
                SELECT w.url, w.title, w.content, 
                       SUM(si.frequency) as score,
                       COUNT(DISTINCT si.word) as matched_words
                FROM websites w
                JOIN search_index si ON w.id = si.website_id
                WHERE si.word IN ({placeholders})
                GROUP BY w.id
                ORDER BY matched_words DESC, score DESC
                LIMIT ?
            ''', query_words + [limit])
            
            results = self.cursor.fetchall()
            
            # Search history save karo
            self.cursor.execute(
                "INSERT INTO search_history (query, results_count) VALUES (?, ?)", 
                (clean_query, len(results))
            )
            self.conn.commit()
            
        except Exception as e:
            print(f"❌ Search error: {e}")
        
        return results
    
    def display_results(self, results, query):
        """Search results beautiful format mein display karta hai"""
        print(f"\n{'='*70}")
        print(f"🌐 {self.engine_name} - Search Results")
        print(f"📝 Query: '{query}'")
        print(f"📊 Found: {len(results)} results")
        print(f"{'='*70}")
        
        if not results:
            print("❌ No results found. Try different keywords or crawl more websites.")
            print("💡 Tip: Use option 4 to crawl new websites")
            return
        
        for i, (url, title, content, score, matched_words) in enumerate(results, 1):
            print(f"\n#{i} ⭐ Score: {score} | 🔤 Words: {matched_words}")
            print(f"🔗 URL: {url}")
            print(f"📖 Title: {title}")
            
            # Query words highlight karo
            snippet = content[:200] + "..." if len(content) > 200 else content
            print(f"📄 Content: {snippet}")
            print(f"{'-'*70}")
    
    def get_search_history(self, limit=10):
        """Recent search history dikhata hai"""
        self.cursor.execute('''
            SELECT query, results_count, search_time FROM search_history 
            ORDER BY search_time DESC LIMIT ?
        ''', (limit,))
        
        history = self.cursor.fetchall()
        
        print(f"\n📜 Recent Search History (Last {limit}):")
        if not history:
            print("   No search history yet.")
            return
            
        for query, count, time in history:
            time_str = time.split('.')[0]  # Remove microseconds
            print(f"   • '{query}' → {count} results ({time_str})")
    
    def get_stats(self):
        """Search engine statistics dikhata hai"""
        self.cursor.execute("SELECT COUNT(*) FROM websites")
        total_pages = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM search_index")
        total_indexed_words = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(DISTINCT word) FROM search_index")
        unique_words = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM search_history")
        total_searches = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(DISTINCT url) FROM websites")
        unique_domains = self.cursor.fetchone()[0]
        
        print(f"\n📊 {self.engine_name} Statistics:")
        print(f"   🌐 Websites Indexed: {total_pages}")
        print(f"   🏷️ Unique Domains: {unique_domains}")
        print(f"   📝 Total Words in Index: {total_indexed_words}")
        print(f"   🔤 Unique Words: {unique_words}")
        print(f"   🔍 Total Searches: {total_searches}")
        
        if total_pages > 0:
            self.cursor.execute("SELECT url, title FROM websites ORDER BY last_crawled DESC LIMIT 3")
            recent = self.cursor.fetchall()
            print(f"\n   📅 Recently Crawled:")
            for url, title in recent:
                print(f"      • {title[:40]}...")
    
    def export_data(self, filename='cyber_world_export.json'):
        """Data export karta hai JSON format mein"""
        try:
            self.cursor.execute('''
                SELECT url, title, content FROM websites
            ''')
            websites = self.cursor.fetchall()
            
            data = {
                'export_time': datetime.now().isoformat(),
                'engine_name': self.engine_name,
                'version': self.version,
                'websites_count': len(websites),
                'websites': [
                    {
                        'url': url,
                        'title': title,
                        'content_preview': content[:500] + '...' if len(content) > 500 else content
                    } for url, title, content in websites
                ]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Data exported to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Export error: {e}")
            return False
    
    def close(self):
        """Database connection close karta hai"""
        if hasattr(self, 'conn'):
            self.conn.close()
            print("✅ Database connection closed.")

def main():
    """Main application function"""
    print("🚀 Cyber World Search Engine Starting...")
    print("🌐 Developed by Cyber World Team")
    print("📖 GitHub: https://github.com/yourusername/cyber-world-search")
    print("=" * 60)
    
    # Search engine initialize karo
    cyber = CyberWorldSearchEngine()
    
    try:
        # Initial setup with sample websites
        print("\n🎯 Initial Setup:")
        print("   I'll crawl some sample websites to get started...")
        
        sample_sites = [
            "https://httpbin.org",
            "https://example.com",
        ]
        
        for site in sample_sites:
            try:
                cyber.crawl_website(site, max_pages=3, delay=1)
                time.sleep(2)
            except Exception as e:
                print(f"   Could not crawl {site}: {e}")
        
        # Main interface
        while True:
            print(f"\n{'='*50}")
            print(f"🌐 {cyber.engine_name} v{cyber.version}")
            print(f"{'='*50}")
            print("1. 🔍 Search Websites")
            print("2. 📊 View Statistics") 
            print("3. 📜 Search History")
            print("4. 🕷️ Crawl New Website")
            print("5. 💾 Export Data")
            print("6. ❌ Exit")
            print("-" * 50)
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                query = input("Enter search query: ").strip()
                if query:
                    results = cyber.search(query, limit=10)
                    cyber.display_results(results, query)
                else:
                    print("❌ Please enter a valid query.")
            
            elif choice == '2':
                cyber.get_stats()
            
            elif choice == '3':
                limit = input("How many recent searches to show? (default 10): ").strip()
                try:
                    limit = int(limit) if limit.isdigit() else 10
                    cyber.get_search_history(limit)
                except:
                    cyber.get_search_history()
            
            elif choice == '4':
                url = input("Enter website URL to crawl: ").strip()
                if cyber.is_valid_url(url):
                    pages = input("Max pages to crawl (default 10): ").strip()
                    delay = input("Delay between requests in seconds (default 2): ").strip()
                    
                    max_pages = int(pages) if pages.isdigit() else 10
                    crawl_delay = int(delay) if delay.isdigit() else 2
                    
                    cyber.crawl_website(url, max_pages=max_pages, delay=crawl_delay)
                else:
                    print("❌ Invalid URL format. Please include http:// or https://")
            
            elif choice == '5':
                filename = input("Export filename (default: cyber_world_export.json): ").strip()
                filename = filename if filename else 'cyber_world_export.json'
                cyber.export_data(filename)
            
            elif choice == '6':
                print("\n👋 Thank you for using Cyber World Search!")
                print("🌟 Don't forget to star our GitHub repository!")
                break
            
            else:
                print("❌ Invalid choice. Please enter a number between 1-6.")
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Program interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        cyber.close()

if __name__ == "__main__":
    main()
