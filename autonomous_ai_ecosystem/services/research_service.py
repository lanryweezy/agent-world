"""
Research service with web scraping and analysis capabilities.

This module implements comprehensive research capabilities including
web scraping, content analysis, source validation, and report generation.
"""

import asyncio
import aiohttp
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
from urllib.parse import urljoin, urlparse
import hashlib

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class ResearchType(Enum):
    """Types of research that can be conducted."""
    GENERAL_TOPIC = "general_topic"
    COMPETITIVE_ANALYSIS = "competitive_analysis"
    MARKET_RESEARCH = "market_research"
    TECHNICAL_RESEARCH = "technical_research"
    ACADEMIC_RESEARCH = "academic_research"
    NEWS_MONITORING = "news_monitoring"
    TREND_ANALYSIS = "trend_analysis"
    FACT_CHECKING = "fact_checking"


class SourceType(Enum):
    """Types of information sources."""
    WEBSITE = "website"
    NEWS_ARTICLE = "news_article"
    ACADEMIC_PAPER = "academic_paper"
    BLOG_POST = "blog_post"
    FORUM_POST = "forum_post"
    SOCIAL_MEDIA = "social_media"
    DOCUMENTATION = "documentation"
    REPORT = "report"


class CredibilityLevel(Enum):
    """Credibility levels for sources."""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"
    UNKNOWN = "unknown"


@dataclass
class ResearchSource:
    """Information about a research source."""
    source_id: str
    url: str
    title: str
    source_type: SourceType
    
    # Content information
    content: str = ""
    summary: str = ""
    key_points: List[str] = field(default_factory=list)
    
    # Metadata
    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    domain: str = ""
    
    # Quality metrics
    credibility_level: CredibilityLevel = CredibilityLevel.UNKNOWN
    credibility_score: float = 0.5
    relevance_score: float = 0.0
    
    # Analysis results
    sentiment: float = 0.0  # -1.0 to 1.0
    readability_score: float = 0.0
    word_count: int = 0
    
    # Extraction metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    processing_time: float = 0.0
    
    def get_domain(self) -> str:
        """Extract domain from URL."""
        if not self.domain:
            parsed = urlparse(self.url)
            self.domain = parsed.netloc.lower()
        return self.domain


@dataclass
class ResearchQuery:
    """Research query configuration."""
    query_id: str
    topic: str
    research_type: ResearchType
    
    # Query parameters
    keywords: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    target_sources: List[str] = field(default_factory=list)  # Specific domains/URLs
    
    # Search constraints
    max_sources: int = 20
    max_depth: int = 2  # How many levels deep to follow links
    time_range_days: Optional[int] = None
    language: str = "en"
    
    # Quality filters
    min_credibility: CredibilityLevel = CredibilityLevel.LOW
    min_relevance: float = 0.3
    
    # Analysis requirements
    include_sentiment: bool = True
    include_summary: bool = True
    include_key_points: bool = True
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    requested_by: str = ""
    priority: int = 5


@dataclass
class ResearchReport:
    """Comprehensive research report."""
    report_id: str
    query_id: str
    topic: str
    
    # Report content
    executive_summary: str = ""
    detailed_findings: str = ""
    key_insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Sources and evidence
    sources: List[ResearchSource] = field(default_factory=list)
    source_count: int = 0
    credible_source_count: int = 0
    
    # Analysis results
    overall_sentiment: float = 0.0
    confidence_score: float = 0.0
    completeness_score: float = 0.0
    
    # Categorized findings
    facts: List[str] = field(default_factory=list)
    opinions: List[str] = field(default_factory=list)
    statistics: List[Dict[str, Any]] = field(default_factory=list)
    quotes: List[Dict[str, str]] = field(default_factory=list)
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    research_duration: float = 0.0
    total_words_analyzed: int = 0
    
    def get_credibility_breakdown(self) -> Dict[str, int]:
        """Get breakdown of sources by credibility level."""
        breakdown = {level.value: 0 for level in CredibilityLevel}
        for source in self.sources:
            breakdown[source.credibility_level.value] += 1
        return breakdown


class WebResearchService(AgentModule):
    """
    Web research service with scraping and analysis capabilities.
    
    Provides comprehensive research functionality including web scraping,
    content analysis, source validation, and report generation.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "research_service")
        
        # Core data structures
        self.research_queries: Dict[str, ResearchQuery] = {}
        self.research_reports: Dict[str, ResearchReport] = {}
        self.source_cache: Dict[str, ResearchSource] = {}
        
        # Active research tasks
        self.active_research: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self.config = {
            "max_concurrent_research": 3,
            "default_timeout_seconds": 30,
            "max_content_length": 50000,
            "cache_duration_hours": 24,
            "user_agent": "AI-Research-Bot/1.0",
            "respect_robots_txt": True,
            "min_delay_between_requests": 1.0,
            "max_retries": 3,
            "enable_content_analysis": True,
            "enable_fact_checking": True
        }
        
        # HTTP session for web scraping
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Domain-specific credibility scores
        self.domain_credibility = {
            # High credibility domains
            "wikipedia.org": 0.8,
            "scholar.google.com": 0.9,
            "arxiv.org": 0.85,
            "nature.com": 0.9,
            "science.org": 0.9,
            "ieee.org": 0.85,
            "acm.org": 0.85,
            "gov": 0.8,  # Government domains
            "edu": 0.75,  # Educational domains
            
            # Medium credibility domains
            "reuters.com": 0.7,
            "bbc.com": 0.7,
            "cnn.com": 0.6,
            "nytimes.com": 0.7,
            "washingtonpost.com": 0.7,
            "theguardian.com": 0.7,
            
            # Lower credibility (but still useful)
            "medium.com": 0.5,
            "reddit.com": 0.4,
            "stackoverflow.com": 0.6,
            "github.com": 0.6,
        }
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "completed_research": 0,
            "failed_research": 0,
            "total_sources_scraped": 0,
            "total_content_analyzed": 0,
            "average_research_time": 0.0,
            "research_by_type": {research_type.value: 0 for research_type in ResearchType},
            "sources_by_credibility": {level.value: 0 for level in CredibilityLevel}
        }
        
        # Counters
        self.query_counter = 0
        self.report_counter = 0
        self.source_counter = 0
        
        self.logger.info("Web research service initialized")
    
    async def initialize(self) -> None:
        """Initialize the research service."""
        try:
            # Create HTTP session with appropriate settings
            timeout = aiohttp.ClientTimeout(total=self.config["default_timeout_seconds"])
            self.http_session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": self.config["user_agent"]},
                connector=aiohttp.TCPConnector(limit=10)
            )
            
            # Start background tasks
            asyncio.create_task(self._cleanup_old_cache())
            asyncio.create_task(self._update_statistics())
            
            self.logger.info("Research service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize research service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the research service."""
        try:
            # Cancel active research tasks
            for task in self.active_research.values():
                task.cancel()
            
            # Wait for tasks to complete
            if self.active_research:
                await asyncio.gather(*self.active_research.values(), return_exceptions=True)
            
            # Close HTTP session
            if self.http_session:
                await self.http_session.close()
            
            self.logger.info("Research service shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during research service shutdown: {e}")
    
    async def conduct_research(
        self,
        topic: str,
        research_type: ResearchType = ResearchType.GENERAL_TOPIC,
        keywords: Optional[List[str]] = None,
        max_sources: int = 20,
        min_credibility: CredibilityLevel = CredibilityLevel.LOW,
        include_analysis: bool = True
    ) -> Dict[str, Any]:
        """Conduct comprehensive research on a topic."""
        try:
            # Check concurrent research limit
            if len(self.active_research) >= self.config["max_concurrent_research"]:
                return {"success": False, "error": "Maximum concurrent research limit reached"}
            
            # Create research query
            self.query_counter += 1
            query_id = f"query_{self.query_counter}_{datetime.now().timestamp()}"
            
            query = ResearchQuery(
                query_id=query_id,
                topic=topic,
                research_type=research_type,
                keywords=keywords or [],
                max_sources=max_sources,
                min_credibility=min_credibility,
                include_sentiment=include_analysis,
                include_summary=include_analysis,
                include_key_points=include_analysis,
                requested_by=self.agent_id
            )
            
            self.research_queries[query_id] = query
            
            # Start research task
            research_task = asyncio.create_task(self._conduct_research_async(query_id))
            self.active_research[query_id] = research_task
            
            # Update statistics
            self.stats["total_queries"] += 1
            self.stats["research_by_type"][research_type.value] += 1
            
            log_agent_event(
                self.agent_id,
                "research_started",
                {
                    "query_id": query_id,
                    "topic": topic,
                    "research_type": research_type.value,
                    "max_sources": max_sources
                }
            )
            
            result = {
                "success": True,
                "query_id": query_id,
                "topic": topic,
                "research_type": research_type.value,
                "estimated_completion_time": self._estimate_research_time(query),
                "status": "researching"
            }
            
            self.logger.info(f"Research started: {topic} ({research_type.value})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to start research: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_research_report(self, query_id: str) -> Dict[str, Any]:
        """Get research report by query ID."""
        try:
            if query_id not in self.research_queries:
                return {"success": False, "error": "Research query not found"}
            
            # Check if research is still in progress
            if query_id in self.active_research:
                task = self.active_research[query_id]
                if not task.done():
                    return {
                        "success": True,
                        "status": "researching",
                        "query_id": query_id,
                        "progress": "Research in progress..."
                    }
            
            # Look for completed report
            reports = [report for report in self.research_reports.values() 
                      if report.query_id == query_id]
            
            if not reports:
                return {"success": False, "error": "Research report not found or research failed"}
            
            # Return the most recent report
            report = max(reports, key=lambda r: r.generated_at)
            
            result = {
                "success": True,
                "query_id": query_id,
                "report_id": report.report_id,
                "topic": report.topic,
                "executive_summary": report.executive_summary,
                "detailed_findings": report.detailed_findings,
                "key_insights": report.key_insights,
                "recommendations": report.recommendations,
                "statistics": {
                    "source_count": report.source_count,
                    "credible_source_count": report.credible_source_count,
                    "overall_sentiment": report.overall_sentiment,
                    "confidence_score": report.confidence_score,
                    "completeness_score": report.completeness_score,
                    "research_duration": report.research_duration,
                    "total_words_analyzed": report.total_words_analyzed
                },
                "credibility_breakdown": report.get_credibility_breakdown(),
                "sources": [
                    {
                        "title": source.title,
                        "url": source.url,
                        "credibility_level": source.credibility_level.value,
                        "relevance_score": source.relevance_score,
                        "summary": source.summary
                    }
                    for source in report.sources[:10]  # Top 10 sources
                ],
                "generated_at": report.generated_at.isoformat()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get research report: {e}")
            return {"success": False, "error": str(e)}
    
    async def _conduct_research_async(self, query_id: str) -> None:
        """Conduct research asynchronously."""
        query = self.research_queries[query_id]
        start_time = datetime.now()
        
        try:
            # Generate search URLs and terms
            search_terms = self._generate_search_terms(query)
            
            # Collect sources
            sources = []
            for search_term in search_terms[:5]:  # Limit search terms
                term_sources = await self._search_and_scrape(search_term, query)
                sources.extend(term_sources)
                
                # Respect rate limiting
                await asyncio.sleep(self.config["min_delay_between_requests"])
            
            # Remove duplicates and filter by quality
            unique_sources = self._deduplicate_sources(sources)
            filtered_sources = self._filter_sources_by_quality(unique_sources, query)
            
            # Analyze sources
            if query.include_summary or query.include_key_points or query.include_sentiment:
                for source in filtered_sources:
                    await self._analyze_source_content(source, query)
            
            # Generate comprehensive report
            report = await self._generate_research_report(query, filtered_sources, start_time)
            
            # Store report
            self.research_reports[report.report_id] = report
            
            # Update statistics
            self.stats["completed_research"] += 1
            self.stats["total_sources_scraped"] += len(filtered_sources)
            self.stats["total_content_analyzed"] += sum(source.word_count for source in filtered_sources)
            
            for source in filtered_sources:
                self.stats["sources_by_credibility"][source.credibility_level.value] += 1
            
            log_agent_event(
                self.agent_id,
                "research_completed",
                {
                    "query_id": query_id,
                    "report_id": report.report_id,
                    "source_count": len(filtered_sources),
                    "research_duration": report.research_duration,
                    "confidence_score": report.confidence_score
                }
            )
            
            self.logger.info(f"Research completed: {query.topic} ({len(filtered_sources)} sources)")
            
        except Exception as e:
            self.stats["failed_research"] += 1
            self.logger.error(f"Research failed for query {query_id}: {e}")
        
        finally:
            # Clean up active research
            if query_id in self.active_research:
                del self.active_research[query_id]
    
    async def _search_and_scrape(self, search_term: str, query: ResearchQuery) -> List[ResearchSource]:
        """Search for and scrape sources for a search term."""
        sources = []
        
        try:
            # For this implementation, we'll simulate web search results
            # In a real implementation, you would integrate with search APIs
            search_urls = self._generate_search_urls(search_term, query)
            
            for url in search_urls[:query.max_sources]:
                try:
                    source = await self._scrape_url(url, query)
                    if source:
                        sources.append(source)
                    
                    # Respect rate limiting
                    await asyncio.sleep(self.config["min_delay_between_requests"])
                    
                except Exception as e:
                    self.logger.warning(f"Failed to scrape {url}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Search and scrape failed for term '{search_term}': {e}")
        
        return sources
    
    async def _scrape_url(self, url: str, query: ResearchQuery) -> Optional[ResearchSource]:
        """Scrape content from a URL."""
        try:
            # Check cache first
            url_hash = hashlib.md5(url.encode()).hexdigest()
            if url_hash in self.source_cache:
                cached_source = self.source_cache[url_hash]
                # Check if cache is still valid
                if (datetime.now() - cached_source.scraped_at).total_seconds() < self.config["cache_duration_hours"] * 3600:
                    return cached_source
            
            start_time = datetime.now()
            
            async with self.http_session.get(url) as response:
                if response.status != 200:
                    return None
                
                content = await response.text()
                
                # Limit content length
                if len(content) > self.config["max_content_length"]:
                    content = content[:self.config["max_content_length"]]
                
                # Extract basic information
                title = self._extract_title(content)
                clean_content = self._clean_content(content)
                
                # Create source object
                self.source_counter += 1
                source_id = f"source_{self.source_counter}_{datetime.now().timestamp()}"
                
                source = ResearchSource(
                    source_id=source_id,
                    url=url,
                    title=title,
                    source_type=self._determine_source_type(url, content),
                    content=clean_content,
                    word_count=len(clean_content.split()),
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
                
                # Calculate credibility
                source.credibility_score = self._calculate_credibility(source)
                source.credibility_level = self._score_to_credibility_level(source.credibility_score)
                
                # Calculate relevance
                source.relevance_score = self._calculate_relevance(source, query)
                
                # Cache the source
                self.source_cache[url_hash] = source
                
                return source
                
        except Exception as e:
            self.logger.warning(f"Failed to scrape URL {url}: {e}")
            return None
    
    def _generate_search_terms(self, query: ResearchQuery) -> List[str]:
        """Generate search terms from the research query."""
        terms = [query.topic]
        
        # Add keyword combinations
        if query.keywords:
            terms.extend(query.keywords)
            # Create combinations
            for keyword in query.keywords:
                terms.append(f"{query.topic} {keyword}")
        
        # Add research type specific terms
        if query.research_type == ResearchType.COMPETITIVE_ANALYSIS:
            terms.append(f"{query.topic} competitors analysis")
            terms.append(f"{query.topic} market share")
        elif query.research_type == ResearchType.TECHNICAL_RESEARCH:
            terms.append(f"{query.topic} technical documentation")
            terms.append(f"{query.topic} implementation")
        elif query.research_type == ResearchType.ACADEMIC_RESEARCH:
            terms.append(f"{query.topic} research paper")
            terms.append(f"{query.topic} academic study")
        
        return terms[:10]  # Limit to 10 terms
    
    def _generate_search_urls(self, search_term: str, query: ResearchQuery) -> List[str]:
        """Generate URLs to search (simulated for this implementation)."""
        # In a real implementation, this would use search APIs
        # For now, we'll return some example URLs based on the search term
        
        base_urls = [
            "https://en.wikipedia.org/wiki/",
            "https://www.example.com/articles/",
            "https://blog.example.com/posts/",
            "https://docs.example.com/guides/",
            "https://news.example.com/stories/"
        ]
        
        # Generate URLs based on search term
        urls = []
        search_slug = search_term.lower().replace(" ", "_")
        
        for base_url in base_urls:
            urls.append(f"{base_url}{search_slug}")
        
        # Add target sources if specified
        if query.target_sources:
            urls.extend(query.target_sources)
        
        return urls
    
    def _extract_title(self, html_content: str) -> str:
        """Extract title from HTML content."""
        # Simple title extraction
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        
        # Try h1 tag
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html_content, re.IGNORECASE)
        if h1_match:
            return h1_match.group(1).strip()
        
        return "Untitled"
    
    def _clean_content(self, html_content: str) -> str:
        """Clean HTML content to extract text."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', ' ', text)
        
        return text.strip()
    
    def _determine_source_type(self, url: str, content: str) -> SourceType:
        """Determine the type of source based on URL and content."""
        domain = urlparse(url).netloc.lower()
        
        if "wikipedia.org" in domain:
            return SourceType.WEBSITE
        elif any(news_domain in domain for news_domain in ["news", "cnn", "bbc", "reuters"]):
            return SourceType.NEWS_ARTICLE
        elif "arxiv.org" in domain or "scholar.google" in domain:
            return SourceType.ACADEMIC_PAPER
        elif "blog" in domain or "medium.com" in domain:
            return SourceType.BLOG_POST
        elif "reddit.com" in domain or "forum" in domain:
            return SourceType.FORUM_POST
        elif "docs" in domain or "documentation" in url.lower():
            return SourceType.DOCUMENTATION
        else:
            return SourceType.WEBSITE
    
    def _calculate_credibility(self, source: ResearchSource) -> float:
        """Calculate credibility score for a source."""
        score = 0.5  # Base score
        
        domain = source.get_domain()
        
        # Check domain credibility
        for domain_pattern, credibility in self.domain_credibility.items():
            if domain_pattern in domain:
                score = credibility
                break
        
        # Adjust based on source type
        type_adjustments = {
            SourceType.ACADEMIC_PAPER: 0.2,
            SourceType.NEWS_ARTICLE: 0.1,
            SourceType.DOCUMENTATION: 0.15,
            SourceType.WEBSITE: 0.0,
            SourceType.BLOG_POST: -0.1,
            SourceType.FORUM_POST: -0.2,
            SourceType.SOCIAL_MEDIA: -0.3
        }
        
        score += type_adjustments.get(source.source_type, 0.0)
        
        # Adjust based on content quality indicators
        if source.author:
            score += 0.05
        
        if source.publication_date:
            # Newer content gets slight boost
            days_old = (datetime.now() - source.publication_date).days
            if days_old < 30:
                score += 0.05
            elif days_old > 365:
                score -= 0.05
        
        # Content length indicator
        if 500 <= source.word_count <= 5000:
            score += 0.05
        elif source.word_count < 100:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _score_to_credibility_level(self, score: float) -> CredibilityLevel:
        """Convert credibility score to credibility level."""
        if score >= 0.8:
            return CredibilityLevel.VERY_HIGH
        elif score >= 0.6:
            return CredibilityLevel.HIGH
        elif score >= 0.4:
            return CredibilityLevel.MEDIUM
        elif score >= 0.2:
            return CredibilityLevel.LOW
        else:
            return CredibilityLevel.VERY_LOW
    
    def _calculate_relevance(self, source: ResearchSource, query: ResearchQuery) -> float:
        """Calculate relevance score for a source."""
        content_lower = source.content.lower()
        title_lower = source.title.lower()
        topic_lower = query.topic.lower()
        
        relevance = 0.0
        
        # Topic in title gets high score
        if topic_lower in title_lower:
            relevance += 0.4
        
        # Topic in content
        topic_count = content_lower.count(topic_lower)
        relevance += min(0.3, topic_count * 0.05)
        
        # Keywords in content
        if query.keywords:
            keyword_matches = 0
            for keyword in query.keywords:
                if keyword.lower() in content_lower:
                    keyword_matches += 1
            
            relevance += min(0.3, keyword_matches / len(query.keywords) * 0.3)
        
        return min(1.0, relevance)
    
    def _deduplicate_sources(self, sources: List[ResearchSource]) -> List[ResearchSource]:
        """Remove duplicate sources based on URL and content similarity."""
        seen_urls = set()
        unique_sources = []
        
        for source in sources:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)
        
        return unique_sources
    
    def _filter_sources_by_quality(self, sources: List[ResearchSource], query: ResearchQuery) -> List[ResearchSource]:
        """Filter sources based on quality criteria."""
        filtered = []
        
        # Convert credibility level to score for comparison
        min_credibility_score = {
            CredibilityLevel.VERY_LOW: 0.0,
            CredibilityLevel.LOW: 0.2,
            CredibilityLevel.MEDIUM: 0.4,
            CredibilityLevel.HIGH: 0.6,
            CredibilityLevel.VERY_HIGH: 0.8
        }[query.min_credibility]
        
        for source in sources:
            if (source.credibility_score >= min_credibility_score and 
                source.relevance_score >= query.min_relevance):
                filtered.append(source)
        
        # Sort by relevance and credibility
        filtered.sort(key=lambda s: (s.relevance_score + s.credibility_score) / 2, reverse=True)
        
        # Limit to max sources
        return filtered[:query.max_sources]
    
    async def _analyze_source_content(self, source: ResearchSource, query: ResearchQuery) -> None:
        """Analyze source content for insights."""
        try:
            # Generate summary
            if query.include_summary:
                source.summary = self._generate_summary(source.content)
            
            # Extract key points
            if query.include_key_points:
                source.key_points = self._extract_key_points(source.content)
            
            # Analyze sentiment
            if query.include_sentiment:
                source.sentiment = self._analyze_sentiment(source.content)
            
            # Calculate readability
            source.readability_score = self._calculate_readability(source.content)
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze source content: {e}")
    
    def _generate_summary(self, content: str) -> str:
        """Generate a summary of the content."""
        # Simple extractive summarization
        sentences = content.split('. ')
        if len(sentences) <= 3:
            return content
        
        # Take first and last sentences, plus one from middle
        summary_sentences = [
            sentences[0],
            sentences[len(sentences) // 2],
            sentences[-1]
        ]
        
        return '. '.join(summary_sentences)
    
    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content."""
        # Simple key point extraction based on sentence patterns
        sentences = content.split('. ')
        key_points = []
        
        # Look for sentences with key indicators
        key_indicators = ['important', 'key', 'main', 'significant', 'crucial', 'essential']
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in key_indicators):
                key_points.append(sentence.strip())
        
        # If no key indicators found, take sentences with numbers or statistics
        if not key_points:
            for sentence in sentences:
                if re.search(r'\d+%|\d+\.\d+|\$\d+', sentence):
                    key_points.append(sentence.strip())
        
        return key_points[:5]  # Limit to 5 key points
    
    def _analyze_sentiment(self, content: str) -> float:
        """Analyze sentiment of content (simplified implementation)."""
        # Simple sentiment analysis based on word lists
        positive_words = ['good', 'great', 'excellent', 'positive', 'success', 'benefit', 'advantage']
        negative_words = ['bad', 'poor', 'negative', 'problem', 'issue', 'disadvantage', 'failure']
        
        content_lower = content.lower()
        positive_count = sum(content_lower.count(word) for word in positive_words)
        negative_count = sum(content_lower.count(word) for word in negative_words)
        
        total_words = len(content.split())
        if total_words == 0:
            return 0.0
        
        sentiment_score = (positive_count - negative_count) / total_words
        return max(-1.0, min(1.0, sentiment_score * 10))  # Scale and clamp
    
    def _calculate_readability(self, content: str) -> float:
        """Calculate readability score (simplified)."""
        words = content.split()
        sentences = content.split('.')
        
        if len(sentences) == 0 or len(words) == 0:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        
        # Simple readability score (lower is more readable)
        readability = 1.0 - min(1.0, avg_sentence_length / 20.0)
        return readability
    
    async def _generate_research_report(
        self, 
        query: ResearchQuery, 
        sources: List[ResearchSource], 
        start_time: datetime
    ) -> ResearchReport:
        """Generate comprehensive research report."""
        self.report_counter += 1
        report_id = f"report_{self.report_counter}_{datetime.now().timestamp()}"
        
        # Calculate statistics
        credible_sources = [s for s in sources if s.credibility_score >= 0.6]
        total_words = sum(source.word_count for source in sources)
        avg_sentiment = sum(source.sentiment for source in sources) / max(len(sources), 1)
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(query, sources)
        
        # Generate detailed findings
        detailed_findings = self._generate_detailed_findings(query, sources)
        
        # Extract insights and recommendations
        key_insights = self._extract_insights(sources)
        recommendations = self._generate_recommendations(query, sources)
        
        # Calculate confidence and completeness scores
        confidence_score = self._calculate_confidence_score(sources)
        completeness_score = self._calculate_completeness_score(query, sources)
        
        report = ResearchReport(
            report_id=report_id,
            query_id=query.query_id,
            topic=query.topic,
            executive_summary=executive_summary,
            detailed_findings=detailed_findings,
            key_insights=key_insights,
            recommendations=recommendations,
            sources=sources,
            source_count=len(sources),
            credible_source_count=len(credible_sources),
            overall_sentiment=avg_sentiment,
            confidence_score=confidence_score,
            completeness_score=completeness_score,
            research_duration=(datetime.now() - start_time).total_seconds(),
            total_words_analyzed=total_words
        )
        
        return report
    
    def _generate_executive_summary(self, query: ResearchQuery, sources: List[ResearchSource]) -> str:
        """Generate executive summary of research findings."""
        if not sources:
            return f"No reliable sources found for research on '{query.topic}'."
        
        summary_parts = [
            f"Research conducted on '{query.topic}' using {len(sources)} sources.",
            f"Analysis included {sum(s.word_count for s in sources)} words of content.",
        ]
        
        # Add credibility information
        credible_count = len([s for s in sources if s.credibility_score >= 0.6])
        summary_parts.append(f"{credible_count} sources were deemed highly credible.")
        
        # Add sentiment information
        avg_sentiment = sum(s.sentiment for s in sources) / len(sources)
        if avg_sentiment > 0.1:
            summary_parts.append("Overall sentiment towards the topic is positive.")
        elif avg_sentiment < -0.1:
            summary_parts.append("Overall sentiment towards the topic is negative.")
        else:
            summary_parts.append("Overall sentiment towards the topic is neutral.")
        
        return " ".join(summary_parts)
    
    def _generate_detailed_findings(self, query: ResearchQuery, sources: List[ResearchSource]) -> str:
        """Generate detailed findings from research."""
        findings = []
        
        # Group sources by credibility level
        by_credibility = {}
        for source in sources:
            level = source.credibility_level.value
            if level not in by_credibility:
                by_credibility[level] = []
            by_credibility[level].append(source)
        
        # Summarize findings by credibility
        for level, level_sources in by_credibility.items():
            if level_sources:
                findings.append(f"\n{level.replace('_', ' ').title()} Credibility Sources ({len(level_sources)}):")
                for source in level_sources[:3]:  # Top 3 per level
                    findings.append(f"- {source.title}: {source.summary}")
        
        return "\n".join(findings)
    
    def _extract_insights(self, sources: List[ResearchSource]) -> List[str]:
        """Extract key insights from sources."""
        insights = []
        
        # Collect all key points
        all_key_points = []
        for source in sources:
            all_key_points.extend(source.key_points)
        
        # Simple insight extraction (in practice, would use more sophisticated NLP)
        insights.extend(all_key_points[:10])  # Top 10 key points as insights
        
        return insights
    
    def _generate_recommendations(self, query: ResearchQuery, sources: List[ResearchSource]) -> List[str]:
        """Generate recommendations based on research findings."""
        recommendations = []
        
        # Basic recommendations based on research type
        if query.research_type == ResearchType.COMPETITIVE_ANALYSIS:
            recommendations.append("Analyze competitor strengths and weaknesses identified in research")
            recommendations.append("Consider market positioning based on competitive landscape")
        elif query.research_type == ResearchType.TECHNICAL_RESEARCH:
            recommendations.append("Review technical implementation details from credible sources")
            recommendations.append("Consider best practices identified in documentation")
        else:
            recommendations.append("Further investigate high-credibility sources for detailed information")
            recommendations.append("Cross-reference findings with additional authoritative sources")
        
        # Add source-specific recommendations
        high_credibility_sources = [s for s in sources if s.credibility_score >= 0.8]
        if high_credibility_sources:
            recommendations.append(f"Focus on insights from {len(high_credibility_sources)} high-credibility sources")
        
        return recommendations
    
    def _calculate_confidence_score(self, sources: List[ResearchSource]) -> float:
        """Calculate confidence score for research findings."""
        if not sources:
            return 0.0
        
        # Base confidence on source credibility and quantity
        avg_credibility = sum(s.credibility_score for s in sources) / len(sources)
        source_count_factor = min(1.0, len(sources) / 10.0)  # More sources = higher confidence
        
        confidence = (avg_credibility * 0.7) + (source_count_factor * 0.3)
        return confidence
    
    def _calculate_completeness_score(self, query: ResearchQuery, sources: List[ResearchSource]) -> float:
        """Calculate completeness score for research."""
        if not sources:
            return 0.0
        
        # Base completeness on source diversity and coverage
        source_types = set(s.source_type for s in sources)
        type_diversity = len(source_types) / len(SourceType)
        
        # Coverage based on relevance scores
        avg_relevance = sum(s.relevance_score for s in sources) / len(sources)
        
        completeness = (type_diversity * 0.4) + (avg_relevance * 0.6)
        return completeness
    
    def _estimate_research_time(self, query: ResearchQuery) -> float:
        """Estimate research completion time in seconds."""
        base_time = 60  # 1 minute base
        source_time = query.max_sources * 5  # 5 seconds per source
        analysis_time = 30 if query.include_summary else 0
        
        return base_time + source_time + analysis_time
    
    async def _cleanup_old_cache(self) -> None:
        """Clean up old cached sources."""
        while True:
            try:
                current_time = datetime.now()
                expired_keys = []
                
                for key, source in self.source_cache.items():
                    age_hours = (current_time - source.scraped_at).total_seconds() / 3600
                    if age_hours > self.config["cache_duration_hours"]:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.source_cache[key]
                
                if expired_keys:
                    self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                
                # Sleep for 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def _update_statistics(self) -> None:
        """Update service statistics."""
        while True:
            try:
                # Update average research time
                if self.stats["completed_research"] > 0:
                    total_time = sum(
                        report.research_duration 
                        for report in self.research_reports.values()
                    )
                    self.stats["average_research_time"] = total_time / self.stats["completed_research"]
                
                # Sleep for 5 minutes before next update
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(300)