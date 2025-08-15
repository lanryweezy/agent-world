"""Learning and knowledge acquisition components."""

from .web_browser import WebBrowser
from .knowledge_extractor import KnowledgeExtractor
from .learning_strategy import LearningStrategy

__all__ = [
    "WebBrowser",
    "KnowledgeExtractor", 
    "LearningStrategy"
]