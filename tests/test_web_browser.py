"""
Unit tests for web browser automation framework.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from autonomous_ai_ecosystem.learning.web_browser import (
    WebBrowser, WebPage, BrowsingSession, ContentFilter,
    BrowsingStrategy, ContentType
)


class TestContentFilter:
    """Test cases for ContentFilter."""
    
    def setup_method(self):
        """Set up test environment."""
        self.content_filter = ContentFilter()
    
    def test_safe_url_detection(self):
        """Test safe URL detection."""
        # Safe URLs
        safe_urls = [
            "https://wikipedia.org/wiki/Python",
            "https://github.com/python/cpython",
            "https://stackoverflow.com/questions/python",
            "https://docs.python.org/3/",
            "https://arxiv.org/abs/1234.5678"
        ]
        
        for url in safe_urls:
            assert self.content_filter.is_safe_url(url) == True
        
        # Unsafe URLs
        unsafe_urls = [
            "https://adult-content.com",
            "https://gambling-site.com",
            "https://hack-tools.net",
            "https://violence-content.org"
        ]
        
        for url in unsafe_urls:
            assert self.content_filter.is_safe_url(url) == False
    
    def test_safe_content_detection(self):
        """Test safe content detection."""
        # Safe content
        safe_content = [
            "This is an educational article about machine learning algorithms.",
            "Python is a programming language used for data science and web development.",
            "Research shows that artificial intelligence can help solve complex problems."
        ]
        
        for content in safe_content:
            assert self.content_filter.is_safe_content(content) == True
        
        # Unsafe content
        unsafe_content = [
            "This content contains adult material and explicit content.",
            "Learn how to hack into systems and crack passwords.",
            "Violence and weapons are discussed in detail here."
        ]
        
        for content in unsafe_content:
            assert self.content_filter.is_safe_content(content) == False
    
    def test_credibility_score_calculation(self):
        """Test credibility score calculation."""
        # High credibility
        high_cred_url = "https://nature.com/articles/research-paper"
        high_cred_content = "This research study presents evidence-based analysis with citations and references."
        
        score = self.content_filter.calculate_credibility_score(high_cred_url, high_cred_content)
        assert score > 0.7
        
        # Low credibility
        low_cred_url = "https://random-blog.com/opinion"
        low_cred_content = "This is just my opinion without any sources."
        
        score = self.content_filter.calculate_credibility_score(low_cred_url, low_cred_content)
        assert score < 0.7


class TestWebBrowser:
    """Test cases for WebBrowser."""
    
    def setup_method(self):
        """Set up test environment."""
        self.agent_id = "test_agent_browser"
        self.config = {
            'timeout': 10,
            'max_pages_per_session': 5,
            'delay_between_requests': 0.1,  # Faster for testing
            'content_filter_enabled': True
        }
        self.web_browser = WebBrowser(self.agent_id, self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        import asyncio
        if hasattr(self, 'web_browser'):
            asyncio.create_task(self.web_browser.shutdown())
    
    @pytest.mark.asyncio
    async def test_web_browser_initialization(self):
        """Test web browser initialization."""
        # Mock browser setup to avoid actual browser launch
        with patch.object(self.web_browser, '_setup_browser'):
            await self.web_browser.initialize()
        
        assert self.web_browser.agent_id == self.agent_id
        assert self.web_browser.config == self.config
        assert self.web_browser.timeout == 10
        assert self.web_browser.max_pages_per_session == 5
        assert self.web_browser.content_filter_enabled == True
    
    @pytest.mark.asyncio
    async def test_browsing_session_management(self):
        """Test browsing session start and end."""
        interests = ["machine learning", "python programming"]
        strategy = BrowsingStrategy.FOCUSED_SEARCH
        
        # Start session
        session_id = await self.web_browser.start_browsing_session(interests, strategy)
        
        assert session_id is not None
        assert self.web_browser.current_session is not None
        assert self.web_browser.current_session.session_id == session_id
        assert self.web_browser.current_session.interests == interests
        assert self.web_browser.current_session.strategy == strategy
        
        # End session
        completed_session = await self.web_browser.end_browsing_session()
        
        assert completed_session is not None
        assert completed_session.session_id == session_id
        assert completed_session.end_time is not None
        assert completed_session.total_time > 0
        assert self.web_browser.current_session is None
        assert len(self.web_browser.browsing_history) == 1
    
    def test_webpage_creation(self):
        """Test WebPage object creation."""
        page = WebPage(
            url="https://example.com/article",
            title="Test Article",
            content="This is test content for the article.",
            content_type=ContentType.ARTICLE,
            links=["https://example.com/link1", "https://example.com/link2"],
            images=["https://example.com/image1.jpg"],
            metadata={"domain": "example.com"},
            timestamp=datetime.now(),
            load_time=1.5,
            word_count=8,
            credibility_score=0.8
        )
        
        assert page.url == "https://example.com/article"
        assert page.title == "Test Article"
        assert page.content_type == ContentType.ARTICLE
        assert page.word_count == 8
        assert page.credibility_score == 0.8
        assert len(page.links) == 2
        assert len(page.images) == 1
    
    @pytest.mark.asyncio
    async def test_visit_page_with_mocked_driver(self):
        """Test visiting a page with mocked WebDriver."""
        # Mock the WebDriver and its methods
        mock_driver = MagicMock()
        mock_driver.get = MagicMock()
        mock_driver.page_source = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <main>
                    <h1>Test Article</h1>
                    <p>This is test content for the article.</p>
                    <a href="https://example.com/link1">Link 1</a>
                    <img src="https://example.com/image1.jpg" alt="Image 1">
                </main>
            </body>
        </html>
        """
        
        self.web_browser.driver = mock_driver
        
        # Mock WebDriverWait
        with patch('autonomous_ai_ecosystem.learning.web_browser.WebDriverWait'):
            page = await self.web_browser.visit_page("https://example.com/test")
        
        assert page is not None
        assert page.title == "Test Page"
        assert "Test Article" in page.content
        assert page.url == "https://example.com/test"
        assert page.word_count > 0
    
    def test_content_type_classification(self):
        """Test content type classification."""
        # Test different URL patterns
        test_cases = [
            ("https://wikipedia.org/wiki/Python", "Python Programming", "", ContentType.ARTICLE),
            ("https://docs.python.org/3/tutorial/", "Python Tutorial", "", ContentType.DOCUMENTATION),
            ("https://stackoverflow.com/questions/python", "Python Question", "", ContentType.FORUM),
            ("https://youtube.com/watch?v=123", "Python Video", "", ContentType.VIDEO),
            ("https://arxiv.org/abs/1234.5678", "Research Paper", "abstract methodology", ContentType.ACADEMIC),
            ("https://blog.example.com/post", "Blog Post", "", ContentType.BLOG),
            ("https://news.example.com/breaking", "Breaking News", "", ContentType.NEWS)
        ]
        
        for url, title, content, expected_type in test_cases:
            result = self.web_browser._classify_content_type(url, title, content)
            assert result == expected_type
    
    def test_browsing_statistics(self):
        """Test browsing statistics tracking."""
        initial_stats = self.web_browser.get_browsing_statistics()
        
        assert "total_sessions" in initial_stats
        assert "total_pages_visited" in initial_stats
        assert "total_browsing_time" in initial_stats
        assert "successful_extractions" in initial_stats
        assert "blocked_content" in initial_stats
        assert "current_session_active" in initial_stats
        
        # All should be zero initially
        assert initial_stats["total_sessions"] == 0
        assert initial_stats["total_pages_visited"] == 0
        assert initial_stats["current_session_active"] == False
    
    @pytest.mark.asyncio
    async def test_recent_pages_retrieval(self):
        """Test recent pages retrieval."""
        # Start a session and add some mock pages
        await self.web_browser.start_browsing_session(["test"])
        
        # Create mock pages
        mock_pages = []
        for i in range(3):
            page = WebPage(
                url=f"https://example.com/page{i}",
                title=f"Test Page {i}",
                content=f"Content for page {i}",
                content_type=ContentType.ARTICLE,
                links=[],
                images=[],
                metadata={},
                timestamp=datetime.now() - timedelta(hours=i),
                load_time=1.0,
                word_count=10
            )
            mock_pages.append(page)
            self.web_browser.current_session.pages_visited.append(page)
        
        # Get recent pages
        recent_pages = self.web_browser.get_recent_pages(hours=24, limit=10)
        
        assert len(recent_pages) == 3
        # Should be sorted by timestamp (most recent first)
        assert recent_pages[0].title == "Test Page 0"
        assert recent_pages[1].title == "Test Page 1"
        assert recent_pages[2].title == "Test Page 2"
    
    def test_main_content_extraction(self):
        """Test main content extraction from HTML."""
        from bs4 import BeautifulSoup
        
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <nav>Navigation menu</nav>
                <header>Header content</header>
                <main>
                    <h1>Main Article Title</h1>
                    <p>This is the main content of the article.</p>
                    <p>Another paragraph with important information.</p>
                </main>
                <aside>Sidebar content</aside>
                <footer>Footer content</footer>
                <script>console.log('script');</script>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        main_content = self.web_browser._extract_main_content(soup)
        
        assert "Main Article Title" in main_content
        assert "main content of the article" in main_content
        assert "important information" in main_content
        
        # Should not contain navigation, header, footer, or script content
        assert "Navigation menu" not in main_content
        assert "Header content" not in main_content
        assert "Footer content" not in main_content
        assert "Sidebar content" not in main_content
        assert "console.log" not in main_content


if __name__ == "__main__":
    pytest.main([__file__])@
pytest.mark.asyncio
class TestKnowledgeExtractor:
    """Test cases for KnowledgeExtractor."""
    
    def setup_method(self):
        """Set up test environment."""
        from autonomous_ai_ecosystem.learning.knowledge_extractor import (
            KnowledgeExtractor, ExtractedKnowledge, KnowledgeType, ExtractionMethod
        )
        
        self.agent_id = "test_agent_knowledge"
        self.interests = ["machine learning", "python programming", "artificial intelligence"]
        self.knowledge_extractor = KnowledgeExtractor(self.agent_id, self.interests)
    
    def teardown_method(self):
        """Clean up test environment."""
        import asyncio
        if hasattr(self, 'knowledge_extractor'):
            asyncio.create_task(self.knowledge_extractor.shutdown())
    
    @pytest.mark.asyncio
    async def test_knowledge_extractor_initialization(self):
        """Test knowledge extractor initialization."""
        await self.knowledge_extractor.initialize()
        
        assert self.knowledge_extractor.agent_id == self.agent_id
        assert self.knowledge_extractor.interests == self.interests
        assert len(self.knowledge_extractor.interest_weights) == len(self.interests)
        assert len(self.knowledge_extractor.extraction_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_knowledge_extraction_from_page(self):
        """Test knowledge extraction from a web page."""
        from autonomous_ai_ecosystem.learning.web_browser import WebPage, ContentType
        
        await self.knowledge_extractor.initialize()
        
        # Create mock web page with relevant content
        page = WebPage(
            url="https://example.com/ml-article",
            title="Introduction to Machine Learning",
            content="""
            Machine learning is a subset of artificial intelligence that enables computers to learn 
            without being explicitly programmed. Python is a popular programming language for 
            machine learning because it has many useful libraries. TensorFlow is a machine learning 
            framework developed by Google. To implement a neural network, first you need to prepare 
            your data, then you design the network architecture, and finally you train the model.
            """,
            content_type=ContentType.ARTICLE,
            links=[],
            images=[],
            metadata={},
            timestamp=datetime.now(),
            load_time=1.0,
            word_count=50,
            credibility_score=0.8
        )
        
        # Extract knowledge
        extracted_knowledge = await self.knowledge_extractor.extract_knowledge_from_page(page)
        
        assert len(extracted_knowledge) > 0
        
        # Check that extracted knowledge contains relevant information
        knowledge_contents = [k.content for k in extracted_knowledge]
        knowledge_text = " ".join(knowledge_contents).lower()
        
        # Should contain some of our interests
        assert any(interest.lower() in knowledge_text for interest in self.interests)
        
        # Check knowledge types
        knowledge_types = [k.knowledge_type for k in extracted_knowledge]
        assert len(set(knowledge_types)) > 0  # Should have different types
    
    def test_extracted_knowledge_creation(self):
        """Test ExtractedKnowledge object creation."""
        from autonomous_ai_ecosystem.learning.knowledge_extractor import (
            ExtractedKnowledge, KnowledgeType, ExtractionMethod
        )
        
        knowledge = ExtractedKnowledge(
            content="Machine learning is a subset of artificial intelligence",
            knowledge_type=KnowledgeType.DEFINITIONAL,
            confidence_score=0.8,
            relevance_score=0.9,
            source_url="https://example.com",
            extraction_method=ExtractionMethod.PATTERN_MATCHING,
            supporting_evidence=["Supporting context"],
            related_concepts=["machine learning", "artificial intelligence"],
            timestamp=datetime.now(),
            context="Definition context"
        )
        
        assert knowledge.content == "Machine learning is a subset of artificial intelligence"
        assert knowledge.knowledge_type == KnowledgeType.DEFINITIONAL
        assert knowledge.confidence_score == 0.8
        assert knowledge.relevance_score == 0.9
        assert len(knowledge.related_concepts) == 2
    
    @pytest.mark.asyncio
    async def test_knowledge_quality_evaluation(self):
        """Test knowledge quality evaluation."""
        from autonomous_ai_ecosystem.learning.knowledge_extractor import (
            ExtractedKnowledge, KnowledgeType, ExtractionMethod
        )
        
        await self.knowledge_extractor.initialize()
        
        # High quality knowledge
        high_quality_knowledge = ExtractedKnowledge(
            content="Machine learning is a method of data analysis that automates analytical model building using algorithms that iteratively learn from data",
            knowledge_type=KnowledgeType.DEFINITIONAL,
            confidence_score=0.9,
            relevance_score=0.8,
            source_url="https://nature.com/ml-article",
            extraction_method=ExtractionMethod.PATTERN_MATCHING,
            supporting_evidence=["Context 1", "Context 2"],
            related_concepts=["machine learning", "data analysis", "algorithms"],
            timestamp=datetime.now(),
            context="Academic definition"
        )
        
        evaluation = await self.knowledge_extractor.evaluate_knowledge_quality(high_quality_knowledge)
        
        assert evaluation.overall_score > 0.5
        assert evaluation.accuracy_score > 0.0
        assert evaluation.credibility_score > 0.0
        assert evaluation.completeness_score > 0.0
    
    def test_interest_updates(self):
        """Test updating agent interests."""
        initial_count = len(self.knowledge_extractor.interests)
        
        # Add new interests
        new_interests = ["deep learning", "neural networks"]
        self.knowledge_extractor.update_interests(new_interests)
        
        assert len(self.knowledge_extractor.interests) == initial_count + len(new_interests)
        assert "deep learning" in self.knowledge_extractor.interests
        assert "neural networks" in self.knowledge_extractor.interests
        
        # Check weights were assigned
        assert "deep learning" in self.knowledge_extractor.interest_weights
        assert "neural networks" in self.knowledge_extractor.interest_weights
    
    def test_concept_extraction(self):
        """Test concept extraction from text."""
        text = "Machine Learning algorithms use TensorFlow and PyTorch frameworks for implementation"
        
        concepts = self.knowledge_extractor._extract_concepts_from_text(text)
        
        assert len(concepts) > 0
        # Should extract capitalized words and technical terms
        expected_concepts = ["Machine", "Learning", "TensorFlow", "PyTorch"]
        for concept in expected_concepts:
            assert concept in concepts
    
    def test_content_similarity_calculation(self):
        """Test content similarity calculation."""
        content1 = "Machine learning is a subset of artificial intelligence"
        content2 = "Machine learning is part of artificial intelligence field"
        content3 = "Python is a programming language for web development"
        
        # Similar content should have high similarity
        similarity_high = self.knowledge_extractor._calculate_content_similarity(content1, content2)
        assert similarity_high > 0.5
        
        # Different content should have low similarity
        similarity_low = self.knowledge_extractor._calculate_content_similarity(content1, content3)
        assert similarity_low < 0.5
    
    def test_knowledge_summary(self):
        """Test knowledge summary generation."""
        from autonomous_ai_ecosystem.learning.knowledge_extractor import (
            ExtractedKnowledge, KnowledgeType, ExtractionMethod
        )
        
        # Add some mock knowledge to history
        mock_knowledge = [
            ExtractedKnowledge(
                content="Test knowledge 1",
                knowledge_type=KnowledgeType.FACTUAL,
                confidence_score=0.8,
                relevance_score=0.7,
                source_url="https://example.com",
                extraction_method=ExtractionMethod.KEYWORD_EXTRACTION,
                supporting_evidence=[],
                related_concepts=["concept1", "concept2"],
                timestamp=datetime.now()
            ),
            ExtractedKnowledge(
                content="Test knowledge 2",
                knowledge_type=KnowledgeType.DEFINITIONAL,
                confidence_score=0.9,
                relevance_score=0.8,
                source_url="https://example.com",
                extraction_method=ExtractionMethod.PATTERN_MATCHING,
                supporting_evidence=[],
                related_concepts=["concept2", "concept3"],
                timestamp=datetime.now()
            )
        ]
        
        self.knowledge_extractor.knowledge_history.extend(mock_knowledge)
        
        # Get summary
        summary = self.knowledge_extractor.get_knowledge_summary(hours=24)
        
        assert summary["total_knowledge"] == 2
        assert "knowledge_types" in summary
        assert "top_concepts" in summary
        assert "average_confidence" in summary
        assert summary["average_confidence"] > 0.0
    
    def test_extraction_statistics(self):
        """Test extraction statistics."""
        stats = self.knowledge_extractor.get_extraction_statistics()
        
        expected_fields = [
            "total_extractions",
            "successful_extractions", 
            "high_quality_extractions",
            "knowledge_types",
            "average_confidence",
            "average_relevance",
            "total_interests",
            "known_concepts_count",
            "knowledge_history_size"
        ]
        
        for field in expected_fields:
            assert field in stats
        
        assert stats["total_interests"] == len(self.interests)