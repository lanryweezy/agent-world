"""
Web browser automation framework for autonomous AI agents.

This module implements safe, intelligent web browsing capabilities with
content filtering, timeout handling, and autonomous navigation.
"""

import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urljoin, urlparse
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event

class BrowsingStrategy(Enum):
    """Web browsing strategies."""
    FOCUSED_SEARCH = "focused_search"
    EXPLORATORY = "exploratory"
    FOLLOW_LINKS = "follow_links"
    TOPIC_DEEP_DIVE = "topic_deep_dive"
    RANDOM_WALK = "random_walk"


class ContentType(Enum):
    """Types of web content."""
    ARTICLE = "article"
    TUTORIAL = "tutorial"
    DOCUMENTATION = "documentation"
    NEWS = "news"
    FORUM = "forum"
    VIDEO = "video"
    ACADEMIC = "academic"
    BLOG = "blog"
    UNKNOWN = "unknown"


@dataclass
class WebPage:
    """Represents a web page with extracted content."""
    url: str
    title: str
    content: str
    content_type: ContentType
    links: List[str]
    images: List[str]
    metadata: Dict[str, Any]
    timestamp: datetime
    load_time: float
    word_count: int
    language: Optional[str] = None
    credibility_score: float = 0.5

@dataclass
class BrowsingSession:
    """Represents a web browsing session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    pages_visited: List[WebPage] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    strategy: BrowsingStrategy = BrowsingStrategy.FOCUSED_SEARCH
    total_time: float = 0.0
    success_rate: float = 0.0


class ContentFilter:
    """Filters and validates web content for safety and relevance."""
    
    def __init__(self):
        # Blocked domains and patterns
        self.blocked_domains = {
            'adult', 'gambling', 'violence', 'illegal', 'malware',
            'phishing', 'spam', 'hate', 'extremist'
        }
        
        # Blocked content patterns
        self.blocked_patterns = [
            r'\b(porn|xxx|adult|gambling|casino|bet)\b',
            r'\b(hack|crack|pirate|illegal|drugs)\b',
            r'\b(violence|weapon|bomb|terror)\b',
            r'\b(hate|racist|extremist)\b'
        ]
        
        # Preferred domains for learning
        self.trusted_domains = {
            'wikipedia.org', 'edu', 'gov', 'arxiv.org', 'github.com',
            'stackoverflow.com', 'medium.com', 'nature.com', 'science.org'
        }
    
    def is_safe_url(self, url: str) -> bool:
        """Check if URL is safe to visit."""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            # Check blocked domains
            for blocked in self.blocked_domains:
                if blocked in domain:
                    return False
            
            # Check URL patterns
            for pattern in self.blocked_patterns:
                if re.search(pattern, url.lower()):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def is_safe_content(self, content: str) -> bool:
        """Check if content is safe and appropriate."""
        try:
            content_lower = content.lower()
            
            # Check for blocked patterns
            for pattern in self.blocked_patterns:
                if re.search(pattern, content_lower):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def calculate_credibility_score(self, url: str, content: str) -> float:
        """Calculate credibility score for content."""
        try:
            score = 0.5  # Base score
            
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            # Domain-based scoring
            if any(trusted in domain for trusted in self.trusted_domains):
                score += 0.3
            elif domain.endswith('.edu') or domain.endswith('.gov'):
                score += 0.4
            elif domain.endswith('.org'):
                score += 0.2
            
            # Content-based scoring
            if len(content) > 1000:  # Substantial content
                score += 0.1
            
            if re.search(r'\b(research|study|analysis|data|evidence)\b', content.lower()):
                score += 0.1
            
            if re.search(r'\b(citation|reference|source|bibliography)\b', content.lower()):
                score += 0.1
            
            return min(1.0, max(0.0, score))
            
        except Exception:
            return 0.5

class WebBrowser(AgentModule):
    """
    Intelligent web browser for autonomous agents with safety features,
    content extraction, and adaptive browsing strategies.
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any] = None):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "web_browser")
        
        # Configuration
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30)
        self.max_pages_per_session = self.config.get('max_pages_per_session', 50)
        self.delay_between_requests = self.config.get('delay_between_requests', 2)
        self.content_filter_enabled = self.config.get('content_filter_enabled', True)
        
        # Browser setup
        self.driver: Optional[webdriver.Chrome] = None
        self.content_filter = ContentFilter()
        
        # Session management
        self.current_session: Optional[BrowsingSession] = None
        self.browsing_history: List[BrowsingSession] = []
        self.visited_urls: Set[str] = set()
        
        # Statistics
        self.browsing_stats = {
            "total_sessions": 0,
            "total_pages_visited": 0,
            "total_browsing_time": 0.0,
            "successful_extractions": 0,
            "blocked_content": 0,
            "average_page_load_time": 0.0
        }
        
        self.logger.info(f"Web browser initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the web browser."""
        try:
            await self._setup_browser()
            self.logger.info("Web browser initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize web browser: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the web browser gracefully."""
        try:
            if self.current_session:
                await self.end_browsing_session()
            
            if self.driver:
                self.driver.quit()
                self.driver = None
            
            self.logger.info("Web browser shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during web browser shutdown: {e}")
    
    async def start_browsing_session(
        self,
        interests: List[str],
        strategy: BrowsingStrategy = BrowsingStrategy.FOCUSED_SEARCH,
        time_limit_hours: float = 2.0
    ) -> str:
        """
        Start a new browsing session.
        
        Args:
            interests: List of topics/interests to focus on
            strategy: Browsing strategy to use
            time_limit_hours: Maximum time for the session
            
        Returns:
            Session ID
        """
        try:
            if self.current_session:
                await self.end_browsing_session()
            
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            self.current_session = BrowsingSession(
                session_id=session_id,
                start_time=datetime.now(),
                interests=interests.copy(),
                strategy=strategy
            )
            
            self.browsing_stats["total_sessions"] += 1
            
            log_agent_event(
                self.agent_id,
                "browsing_session_started",
                {
                    "session_id": session_id,
                    "interests": interests,
                    "strategy": strategy.value,
                    "time_limit_hours": time_limit_hours
                }
            )
            
            self.logger.info(f"Started browsing session: {session_id}")
            
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to start browsing session: {e}")
            raise  
    async def browse_topic(
        self,
        topic: str,
        max_pages: int = 10,
        depth: int = 2
    ) -> List[WebPage]:
        """
        Browse web content related to a specific topic.
        
        Args:
            topic: Topic to search for
            max_pages: Maximum number of pages to visit
            depth: How deep to follow links (1 = search results only)
            
        Returns:
            List of WebPage objects with extracted content
        """
        try:
            if not self.current_session:
                await self.start_browsing_session([topic])
            
            pages_found = []
            
            # Start with search
            search_results = await self._search_topic(topic)
            
            # Visit search result pages
            for i, url in enumerate(search_results[:max_pages]):
                if len(pages_found) >= max_pages:
                    break
                
                page = await self.visit_page(url)
                if page:
                    pages_found.append(page)
                    
                    # Follow links if depth > 1
                    if depth > 1 and len(pages_found) < max_pages:
                        related_pages = await self._follow_related_links(
                            page, 
                            topic, 
                            max_additional=min(3, max_pages - len(pages_found))
                        )
                        pages_found.extend(related_pages)
                
                # Respectful delay
                await asyncio.sleep(self.delay_between_requests)
            
            self.logger.info(f"Browsed topic '{topic}': found {len(pages_found)} pages")
            
            return pages_found
            
        except Exception as e:
            self.logger.error(f"Failed to browse topic '{topic}': {e}")
            return []
    
    async def visit_page(self, url: str) -> Optional[WebPage]:
        """
        Visit a specific web page and extract content.
        
        Args:
            url: URL to visit
            
        Returns:
            WebPage object with extracted content, or None if failed
        """
        try:
            # Check if already visited
            if url in self.visited_urls:
                self.logger.debug(f"Page already visited: {url}")
                return None
            
            # Safety check
            if self.content_filter_enabled and not self.content_filter.is_safe_url(url):
                self.logger.warning(f"Blocked unsafe URL: {url}")
                self.browsing_stats["blocked_content"] += 1
                return None
            
            # Load page
            start_time = time.time()
            
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            load_time = time.time() - start_time
            
            # Extract content
            page = await self._extract_page_content(url, load_time)
            
            if page:
                # Safety check on content
                if self.content_filter_enabled and not self.content_filter.is_safe_content(page.content):
                    self.logger.warning(f"Blocked unsafe content from: {url}")
                    self.browsing_stats["blocked_content"] += 1
                    return None
                
                # Add to session and history
                if self.current_session:
                    self.current_session.pages_visited.append(page)
                
                self.visited_urls.add(url)
                self.browsing_stats["total_pages_visited"] += 1
                self.browsing_stats["successful_extractions"] += 1
                
                # Update average load time
                old_avg = self.browsing_stats["average_page_load_time"]
                count = self.browsing_stats["successful_extractions"]
                self.browsing_stats["average_page_load_time"] = (old_avg * (count - 1) + load_time) / count
                
                log_agent_event(
                    self.agent_id,
                    "page_visited",
                    {
                        "url": url,
                        "title": page.title,
                        "content_type": page.content_type.value,
                        "word_count": page.word_count,
                        "load_time": load_time,
                        "credibility_score": page.credibility_score
                    }
                )
                
                self.logger.debug(f"Successfully visited page: {page.title}")
                
                return page
            
            return None
            
        except TimeoutException:
            self.logger.warning(f"Timeout loading page: {url}")
            return None
        except WebDriverException as e:
            self.logger.warning(f"WebDriver error loading page {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to visit page {url}: {e}")
            return None

    async def end_browsing_session(self) -> Optional[BrowsingSession]:
        """
        End the current browsing session.
        
        Returns:
            Completed BrowsingSession object
        """
        try:
            if not self.current_session:
                return None
            
            # Finalize session
            self.current_session.end_time = datetime.now()
            self.current_session.total_time = (
                self.current_session.end_time - self.current_session.start_time
            ).total_seconds() / 3600.0  # Convert to hours
            
            # Calculate success rate
            if self.current_session.pages_visited:
                successful_pages = sum(
                    1 for page in self.current_session.pages_visited
                    if page.word_count > 100  # Minimum content threshold
                )
                self.current_session.success_rate = successful_pages / len(self.current_session.pages_visited)
            
            # Add to history
            self.browsing_history.append(self.current_session)
            
            # Update statistics
            self.browsing_stats["total_browsing_time"] += self.current_session.total_time
            
            log_agent_event(
                self.agent_id,
                "browsing_session_ended",
                {
                    "session_id": self.current_session.session_id,
                    "duration_hours": self.current_session.total_time,
                    "pages_visited": len(self.current_session.pages_visited),
                    "success_rate": self.current_session.success_rate
                }
            )
            
            completed_session = self.current_session
            self.current_session = None
            
            self.logger.info(f"Ended browsing session: {completed_session.session_id}")
            
            return completed_session
            
        except Exception as e:
            self.logger.error(f"Failed to end browsing session: {e}")
            return None
    
    def get_browsing_statistics(self) -> Dict[str, Any]:
        """
        Get browsing statistics.
        
        Returns:
            Dictionary with browsing statistics
        """
        return {
            **self.browsing_stats,
            "current_session_active": self.current_session is not None,
            "total_unique_urls": len(self.visited_urls),
            "sessions_completed": len(self.browsing_history)
        }
    
    def get_recent_pages(self, hours: int = 24, limit: int = 50) -> List[WebPage]:
        """
        Get recently visited pages.
        
        Args:
            hours: Time window in hours
            limit: Maximum number of pages
            
        Returns:
            List of recent WebPage objects
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_pages = []
            
            # Check current session
            if self.current_session:
                for page in self.current_session.pages_visited:
                    if page.timestamp >= cutoff_time:
                        recent_pages.append(page)
            
            # Check completed sessions
            for session in reversed(self.browsing_history):
                if session.end_time and session.end_time < cutoff_time:
                    break  # Sessions are ordered by time
                
                for page in session.pages_visited:
                    if page.timestamp >= cutoff_time:
                        recent_pages.append(page)
            
            # Sort by timestamp (most recent first) and limit
            recent_pages.sort(key=lambda p: p.timestamp, reverse=True)
            
            return recent_pages[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get recent pages: {e}")
            return [] 
   # Private helper methods
    
    async def _setup_browser(self) -> None:
        """Setup Chrome browser with appropriate options."""
        try:
            chrome_options = Options()
            
            # Headless mode for server environments
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Privacy and security
            chrome_options.add_argument("--incognito")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # Faster loading
            
            # User agent
            chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            
        except Exception as e:
            self.logger.error(f"Failed to setup browser: {e}")
            raise
    
    async def _search_topic(self, topic: str) -> List[str]:
        """Search for topic and return list of URLs."""
        try:
            # Use DuckDuckGo for privacy-focused search
            search_url = f"https://duckduckgo.com/?q={topic.replace(' ', '+')}"
            
            self.driver.get(search_url)
            
            # Wait for results
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='result-title-a']"))
            )
            
            # Extract result URLs
            result_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[data-testid='result-title-a']")
            urls = []
            
            for element in result_elements[:20]:  # Top 20 results
                try:
                    url = element.get_attribute('href')
                    if url and self.content_filter.is_safe_url(url):
                        urls.append(url)
                except Exception:
                    continue
            
            if self.current_session:
                self.current_session.search_queries.append(topic)
            
            self.logger.debug(f"Found {len(urls)} search results for '{topic}'")
            
            return urls
            
        except Exception as e:
            self.logger.error(f"Failed to search for topic '{topic}': {e}")
            return []
    
    async def _extract_page_content(self, url: str, load_time: float) -> Optional[WebPage]:
        """Extract content from the current page."""
        try:
            # Get page source
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract title
            title_element = soup.find('title')
            title = title_element.get_text().strip() if title_element else "Untitled"
            
            # Extract main content
            content = self._extract_main_content(soup)
            
            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http'):
                    links.append(href)
                elif href.startswith('/'):
                    links.append(urljoin(url, href))
            
            # Extract images
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                if src.startswith('http'):
                    images.append(src)
                elif src.startswith('/'):
                    images.append(urljoin(url, src))
            
            # Determine content type
            content_type = self._classify_content_type(url, title, content)
            
            # Calculate credibility score
            credibility_score = self.content_filter.calculate_credibility_score(url, content)
            
            # Create WebPage object
            page = WebPage(
                url=url,
                title=title,
                content=content,
                content_type=content_type,
                links=links[:50],  # Limit links
                images=images[:20],  # Limit images
                metadata={
                    'domain': urlparse(url).netloc,
                    'path': urlparse(url).path,
                    'links_count': len(links),
                    'images_count': len(images)
                },
                timestamp=datetime.now(),
                load_time=load_time,
                word_count=len(content.split()),
                credibility_score=credibility_score
            )
            
            return page
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return None 
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from page, filtering out navigation and ads."""
        try:
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Try to find main content areas
            main_content = ""
            
            # Look for main content containers
            content_selectors = [
                'main', 'article', '[role="main"]', '.content', '.post-content',
                '.entry-content', '.article-content', '#content', '#main'
            ]
            
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    main_content = ' '.join(elem.get_text().strip() for elem in elements)
                    break
            
            # Fallback to body content
            if not main_content:
                body = soup.find('body')
                if body:
                    main_content = body.get_text()
            
            # Clean up text
            main_content = re.sub(r'\s+', ' ', main_content).strip()
            
            return main_content
            
        except Exception as e:
            self.logger.error(f"Failed to extract main content: {e}")
            return ""
    
    def _classify_content_type(self, url: str, title: str, content: str) -> ContentType:
        """Classify the type of content on the page."""
        try:
            url_lower = url.lower()
            title_lower = title.lower()
            content_lower = content.lower()
            
            # Check URL patterns
            if 'wikipedia.org' in url_lower:
                return ContentType.ARTICLE
            elif any(pattern in url_lower for pattern in ['tutorial', 'guide', 'how-to']):
                return ContentType.TUTORIAL
            elif any(pattern in url_lower for pattern in ['docs', 'documentation', 'api']):
                return ContentType.DOCUMENTATION
            elif any(pattern in url_lower for pattern in ['news', 'breaking', 'latest']):
                return ContentType.NEWS
            elif any(pattern in url_lower for pattern in ['forum', 'discussion', 'community']):
                return ContentType.FORUM
            elif any(pattern in url_lower for pattern in ['youtube', 'video', 'watch']):
                return ContentType.VIDEO
            elif any(pattern in url_lower for pattern in ['arxiv', 'journal', 'research', 'paper']):
                return ContentType.ACADEMIC
            elif any(pattern in url_lower for pattern in ['blog', 'post']):
                return ContentType.BLOG
            
            # Check title patterns
            if any(pattern in title_lower for pattern in ['tutorial', 'guide', 'how to']):
                return ContentType.TUTORIAL
            elif any(pattern in title_lower for pattern in ['news', 'breaking']):
                return ContentType.NEWS
            elif any(pattern in title_lower for pattern in ['research', 'study', 'analysis']):
                return ContentType.ACADEMIC
            
            # Check content patterns
            if len(content) > 2000:  # Long-form content
                if any(pattern in content_lower for pattern in ['abstract', 'methodology', 'conclusion']):
                    return ContentType.ACADEMIC
                elif any(pattern in content_lower for pattern in ['step 1', 'step 2', 'tutorial']):
                    return ContentType.TUTORIAL
                else:
                    return ContentType.ARTICLE
            
            return ContentType.UNKNOWN
            
        except Exception:
            return ContentType.UNKNOWN
    
    async def _follow_related_links(
        self, 
        page: WebPage, 
        topic: str, 
        max_additional: int = 3
    ) -> List[WebPage]:
        """Follow related links from a page."""
        try:
            related_pages = []
            topic_lower = topic.lower()
            
            # Filter links for relevance
            relevant_links = []
            for link in page.links:
                if any(keyword in link.lower() for keyword in topic_lower.split()):
                    relevant_links.append(link)
            
            # Visit most relevant links
            for link in relevant_links[:max_additional]:
                if len(related_pages) >= max_additional:
                    break
                
                related_page = await self.visit_page(link)
                if related_page:
                    related_pages.append(related_page)
                
                await asyncio.sleep(self.delay_between_requests)
            
            return related_pages
            
        except Exception as e:
            self.logger.error(f"Failed to follow related links: {e}")
            return []