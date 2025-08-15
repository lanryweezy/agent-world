"""
Knowledge extraction and evaluation system for autonomous AI agents.

This module implements sophisticated algorithms for extracting valuable knowledge
from web content, evaluating its quality and relevance, and structuring it for storage.
"""

import re
import math
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter

from ..core.interfaces import Knowledge, AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .web_browser import WebPage, ContentTypeclass Kn
owledgeType(Enum):
    """Types of knowledge that can be extracted."""
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    CONCEPTUAL = "conceptual"
    DEFINITIONAL = "definitional"
    CAUSAL = "causal"
    COMPARATIVE = "comparative"
    TEMPORAL = "temporal"
    QUANTITATIVE = "quantitative"


class ExtractionMethod(Enum):
    """Methods for extracting knowledge."""
    KEYWORD_EXTRACTION = "keyword_extraction"
    ENTITY_RECOGNITION = "entity_recognition"
    PATTERN_MATCHING = "pattern_matching"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    SEMANTIC_ANALYSIS = "semantic_analysis"


@dataclass
class ExtractedKnowledge:
    """Represents extracted knowledge with metadata."""
    content: str
    knowledge_type: KnowledgeType
    confidence_score: float
    relevance_score: float
    source_url: str
    extraction_method: ExtractionMethod
    supporting_evidence: List[str]
    related_concepts: List[str]
    timestamp: datetime
    context: Optional[str] = None


@dataclass
class KnowledgeEvaluation:
    """Evaluation metrics for extracted knowledge."""
    accuracy_score: float
    novelty_score: float
    utility_score: float
    credibility_score: float
    completeness_score: float
    overall_score: float
    evaluation_notes: List[str] = field(default_factory=list)class K
nowledgeExtractor(AgentModule):
    """
    Advanced knowledge extraction system that identifies, extracts, and evaluates
    valuable knowledge from web content and other sources.
    """
    
    def __init__(self, agent_id: str, interests: List[str] = None):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "knowledge_extractor")
        
        # Agent's learning interests
        self.interests = interests or []
        self.interest_weights = {interest: 1.0 for interest in self.interests}
        
        # Knowledge patterns and rules
        self.extraction_patterns = self._initialize_extraction_patterns()
        self.evaluation_criteria = self._initialize_evaluation_criteria()
        
        # Knowledge base for comparison
        self.known_concepts: Set[str] = set()
        self.knowledge_history: List[ExtractedKnowledge] = []
        
        # Statistics
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "high_quality_extractions": 0,
            "knowledge_types": {},
            "average_confidence": 0.0,
            "average_relevance": 0.0
        }
        
        self.logger.info(f"Knowledge extractor initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the knowledge extraction system."""
        try:
            # Load any existing knowledge base
            await self._load_knowledge_base()
            
            self.logger.info("Knowledge extractor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize knowledge extractor: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the knowledge extraction system gracefully."""
        try:
            # Save knowledge base
            await self._save_knowledge_base()
            
            self.logger.info("Knowledge extractor shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during knowledge extractor shutdown: {e}")
    
    async def extract_knowledge_from_page(self, page: WebPage) -> List[ExtractedKnowledge]:
        """
        Extract knowledge from a web page.
        
        Args:
            page: WebPage object to extract knowledge from
            
        Returns:
            List of ExtractedKnowledge objects
        """
        try:
            extracted_knowledge = []
            
            # Apply different extraction methods
            methods = [
                self._extract_by_keywords,
                self._extract_by_patterns,
                self._extract_by_entities,
                self._extract_by_definitions,
                self._extract_by_procedures
            ]
            
            for method in methods:
                try:
                    knowledge_items = await method(page)
                    extracted_knowledge.extend(knowledge_items)
                except Exception as e:
                    self.logger.warning(f"Extraction method failed: {e}")
            
            # Remove duplicates and low-quality extractions
            filtered_knowledge = self._filter_and_deduplicate(extracted_knowledge)
            
            # Evaluate extracted knowledge
            evaluated_knowledge = []
            for knowledge in filtered_knowledge:
                evaluation = await self._evaluate_knowledge(knowledge, page)
                if evaluation.overall_score >= 0.5:  # Quality threshold
                    evaluated_knowledge.append(knowledge)
            
            # Update statistics
            self.extraction_stats["total_extractions"] += len(extracted_knowledge)
            self.extraction_stats["successful_extractions"] += len(evaluated_knowledge)
            
            if evaluated_knowledge:
                high_quality = sum(1 for k in evaluated_knowledge if k.confidence_score > 0.7)
                self.extraction_stats["high_quality_extractions"] += high_quality
                
                avg_confidence = sum(k.confidence_score for k in evaluated_knowledge) / len(evaluated_knowledge)
                avg_relevance = sum(k.relevance_score for k in evaluated_knowledge) / len(evaluated_knowledge)
                
                # Update running averages
                total_successful = self.extraction_stats["successful_extractions"]
                old_conf = self.extraction_stats["average_confidence"]
                old_rel = self.extraction_stats["average_relevance"]
                
                self.extraction_stats["average_confidence"] = (
                    (old_conf * (total_successful - len(evaluated_knowledge)) + 
                     avg_confidence * len(evaluated_knowledge)) / total_successful
                )
                self.extraction_stats["average_relevance"] = (
                    (old_rel * (total_successful - len(evaluated_knowledge)) + 
                     avg_relevance * len(evaluated_knowledge)) / total_successful
                )
            
            # Add to knowledge history
            self.knowledge_history.extend(evaluated_knowledge)
            
            # Update known concepts
            for knowledge in evaluated_knowledge:
                self.known_concepts.update(knowledge.related_concepts)
            
            log_agent_event(
                self.agent_id,
                "knowledge_extracted",
                {
                    "source_url": page.url,
                    "total_extracted": len(extracted_knowledge),
                    "high_quality": len(evaluated_knowledge),
                    "knowledge_types": [k.knowledge_type.value for k in evaluated_knowledge]
                }
            )
            
            self.logger.info(f"Extracted {len(evaluated_knowledge)} knowledge items from {page.url}")
            
            return evaluated_knowledge
            
        except Exception as e:
            self.logger.error(f"Failed to extract knowledge from page: {e}")
            return [] 
   async def evaluate_knowledge_quality(self, knowledge: ExtractedKnowledge) -> KnowledgeEvaluation:
        """
        Evaluate the quality of extracted knowledge.
        
        Args:
            knowledge: ExtractedKnowledge to evaluate
            
        Returns:
            KnowledgeEvaluation with quality metrics
        """
        try:
            evaluation = KnowledgeEvaluation(
                accuracy_score=0.0,
                novelty_score=0.0,
                utility_score=0.0,
                credibility_score=0.0,
                completeness_score=0.0,
                overall_score=0.0
            )
            
            # Accuracy score (based on confidence and supporting evidence)
            evaluation.accuracy_score = knowledge.confidence_score
            if knowledge.supporting_evidence:
                evaluation.accuracy_score += min(0.2, len(knowledge.supporting_evidence) * 0.05)
            evaluation.accuracy_score = min(1.0, evaluation.accuracy_score)
            
            # Novelty score (how new is this knowledge)
            evaluation.novelty_score = self._calculate_novelty_score(knowledge)
            
            # Utility score (how useful is this knowledge)
            evaluation.utility_score = self._calculate_utility_score(knowledge)
            
            # Credibility score (from source and content analysis)
            evaluation.credibility_score = self._calculate_credibility_score(knowledge)
            
            # Completeness score (how complete is the information)
            evaluation.completeness_score = self._calculate_completeness_score(knowledge)
            
            # Overall score (weighted combination)
            weights = {
                'accuracy': 0.3,
                'novelty': 0.2,
                'utility': 0.25,
                'credibility': 0.15,
                'completeness': 0.1
            }
            
            evaluation.overall_score = (
                evaluation.accuracy_score * weights['accuracy'] +
                evaluation.novelty_score * weights['novelty'] +
                evaluation.utility_score * weights['utility'] +
                evaluation.credibility_score * weights['credibility'] +
                evaluation.completeness_score * weights['completeness']
            )
            
            # Add evaluation notes
            if evaluation.accuracy_score < 0.5:
                evaluation.evaluation_notes.append("Low accuracy - needs verification")
            if evaluation.novelty_score > 0.8:
                evaluation.evaluation_notes.append("High novelty - new concept discovered")
            if evaluation.utility_score > 0.7:
                evaluation.evaluation_notes.append("High utility - directly relevant to interests")
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate knowledge quality: {e}")
            return KnowledgeEvaluation(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    def update_interests(self, new_interests: List[str], weights: Optional[Dict[str, float]] = None) -> None:
        """
        Update agent's learning interests.
        
        Args:
            new_interests: List of new interests to add
            weights: Optional weights for interests
        """
        try:
            for interest in new_interests:
                if interest not in self.interests:
                    self.interests.append(interest)
                    self.interest_weights[interest] = weights.get(interest, 1.0) if weights else 1.0
            
            self.logger.info(f"Updated interests: {self.interests}")
            
        except Exception as e:
            self.logger.error(f"Failed to update interests: {e}")
    
    def get_knowledge_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of recently extracted knowledge.
        
        Args:
            hours: Time window in hours
            
        Returns:
            Dictionary with knowledge summary
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_knowledge = [
                k for k in self.knowledge_history 
                if k.timestamp >= cutoff_time
            ]
            
            if not recent_knowledge:
                return {"total_knowledge": 0, "knowledge_types": {}, "top_concepts": []}
            
            # Knowledge type distribution
            type_counts = Counter(k.knowledge_type.value for k in recent_knowledge)
            
            # Top concepts
            all_concepts = []
            for k in recent_knowledge:
                all_concepts.extend(k.related_concepts)
            top_concepts = Counter(all_concepts).most_common(10)
            
            # Quality metrics
            avg_confidence = sum(k.confidence_score for k in recent_knowledge) / len(recent_knowledge)
            avg_relevance = sum(k.relevance_score for k in recent_knowledge) / len(recent_knowledge)
            
            return {
                "total_knowledge": len(recent_knowledge),
                "knowledge_types": dict(type_counts),
                "top_concepts": [concept for concept, count in top_concepts],
                "average_confidence": avg_confidence,
                "average_relevance": avg_relevance,
                "high_quality_count": sum(1 for k in recent_knowledge if k.confidence_score > 0.7)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge summary: {e}")
            return {}
    
    def get_extraction_statistics(self) -> Dict[str, Any]:
        """
        Get knowledge extraction statistics.
        
        Returns:
            Dictionary with extraction statistics
        """
        return {
            **self.extraction_stats,
            "total_interests": len(self.interests),
            "known_concepts_count": len(self.known_concepts),
            "knowledge_history_size": len(self.knowledge_history)
        }   
 # Private extraction methods
    
    async def _extract_by_keywords(self, page: WebPage) -> List[ExtractedKnowledge]:
        """Extract knowledge based on keyword patterns."""
        try:
            extracted = []
            content = page.content.lower()
            
            # Look for interest-related keywords
            for interest in self.interests:
                interest_lower = interest.lower()
                if interest_lower in content:
                    # Find sentences containing the interest
                    sentences = self._split_into_sentences(page.content)
                    relevant_sentences = [
                        s for s in sentences 
                        if interest_lower in s.lower() and len(s.split()) > 5
                    ]
                    
                    for sentence in relevant_sentences[:3]:  # Limit to top 3
                        knowledge = ExtractedKnowledge(
                            content=sentence.strip(),
                            knowledge_type=KnowledgeType.FACTUAL,
                            confidence_score=0.6,
                            relevance_score=self.interest_weights.get(interest, 1.0),
                            source_url=page.url,
                            extraction_method=ExtractionMethod.KEYWORD_EXTRACTION,
                            supporting_evidence=[],
                            related_concepts=[interest],
                            timestamp=datetime.now(),
                            context=f"Found in context of {interest}"
                        )
                        extracted.append(knowledge)
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"Keyword extraction failed: {e}")
            return []
    
    async def _extract_by_patterns(self, page: WebPage) -> List[ExtractedKnowledge]:
        """Extract knowledge using predefined patterns."""
        try:
            extracted = []
            
            for pattern_name, pattern_info in self.extraction_patterns.items():
                matches = re.finditer(pattern_info['pattern'], page.content, re.IGNORECASE)
                
                for match in matches:
                    if len(extracted) >= 10:  # Limit extractions per method
                        break
                    
                    matched_text = match.group(0)
                    
                    # Extract context around the match
                    start = max(0, match.start() - 100)
                    end = min(len(page.content), match.end() + 100)
                    context = page.content[start:end]
                    
                    knowledge = ExtractedKnowledge(
                        content=matched_text,
                        knowledge_type=pattern_info['knowledge_type'],
                        confidence_score=pattern_info['confidence'],
                        relevance_score=self._calculate_pattern_relevance(matched_text),
                        source_url=page.url,
                        extraction_method=ExtractionMethod.PATTERN_MATCHING,
                        supporting_evidence=[context],
                        related_concepts=self._extract_concepts_from_text(matched_text),
                        timestamp=datetime.now(),
                        context=context
                    )
                    extracted.append(knowledge)
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"Pattern extraction failed: {e}")
            return []
    
    async def _extract_by_entities(self, page: WebPage) -> List[ExtractedKnowledge]:
        """Extract knowledge by identifying entities and relationships."""
        try:
            extracted = []
            
            # Simple entity patterns (in a full implementation, would use NLP libraries)
            entity_patterns = {
                'person': r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
                'organization': r'\b[A-Z][a-z]+ (?:Inc|Corp|Ltd|Company|Organization)\b',
                'location': r'\b[A-Z][a-z]+ (?:City|State|Country|University)\b',
                'technology': r'\b[A-Z][a-z]*(?:AI|ML|API|SDK|Framework|Library)\b'
            }
            
            for entity_type, pattern in entity_patterns.items():
                matches = re.finditer(pattern, page.content)
                
                for match in matches:
                    if len(extracted) >= 5:  # Limit per entity type
                        break
                    
                    entity = match.group(0)
                    
                    # Find sentences mentioning this entity
                    sentences = self._split_into_sentences(page.content)
                    entity_sentences = [
                        s for s in sentences 
                        if entity in s and len(s.split()) > 5
                    ]
                    
                    if entity_sentences:
                        knowledge = ExtractedKnowledge(
                            content=entity_sentences[0],
                            knowledge_type=KnowledgeType.FACTUAL,
                            confidence_score=0.7,
                            relevance_score=self._calculate_entity_relevance(entity),
                            source_url=page.url,
                            extraction_method=ExtractionMethod.ENTITY_RECOGNITION,
                            supporting_evidence=entity_sentences[:2],
                            related_concepts=[entity, entity_type],
                            timestamp=datetime.now(),
                            context=f"Entity: {entity} ({entity_type})"
                        )
                        extracted.append(knowledge)
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"Entity extraction failed: {e}")
            return []    
async def _extract_by_definitions(self, page: WebPage) -> List[ExtractedKnowledge]:
        """Extract definitional knowledge."""
        try:
            extracted = []
            
            # Definition patterns
            definition_patterns = [
                r'(.+?)\s+is\s+(?:a|an)\s+(.+?)(?:\.|,|;)',
                r'(.+?)\s+refers to\s+(.+?)(?:\.|,|;)',
                r'(.+?)\s+means\s+(.+?)(?:\.|,|;)',
                r'(.+?)\s+can be defined as\s+(.+?)(?:\.|,|;)',
                r'(?:The term|The word)\s+(.+?)\s+(?:means|refers to)\s+(.+?)(?:\.|,|;)'
            ]
            
            for pattern in definition_patterns:
                matches = re.finditer(pattern, page.content, re.IGNORECASE)
                
                for match in matches:
                    if len(extracted) >= 5:  # Limit definitions
                        break
                    
                    term = match.group(1).strip()
                    definition = match.group(2).strip()
                    
                    # Filter out very short or very long definitions
                    if 10 <= len(definition) <= 200 and len(term.split()) <= 5:
                        full_definition = f"{term} is {definition}"
                        
                        knowledge = ExtractedKnowledge(
                            content=full_definition,
                            knowledge_type=KnowledgeType.DEFINITIONAL,
                            confidence_score=0.8,
                            relevance_score=self._calculate_definition_relevance(term),
                            source_url=page.url,
                            extraction_method=ExtractionMethod.PATTERN_MATCHING,
                            supporting_evidence=[match.group(0)],
                            related_concepts=[term] + self._extract_concepts_from_text(definition),
                            timestamp=datetime.now(),
                            context=f"Definition of {term}"
                        )
                        extracted.append(knowledge)
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"Definition extraction failed: {e}")
            return []
    
    async def _extract_by_procedures(self, page: WebPage) -> List[ExtractedKnowledge]:
        """Extract procedural knowledge (how-to information)."""
        try:
            extracted = []
            
            # Look for step-by-step procedures
            step_patterns = [
                r'(?:Step\s+\d+|First|Second|Third|Next|Then|Finally)[:\-\s]+(.+?)(?:\n|\.)',
                r'\d+\.\s+(.+?)(?:\n|\.|$)',
                r'(?:To\s+\w+|In order to)[,\s]+(.+?)(?:\n|\.|,)'
            ]
            
            for pattern in step_patterns:
                matches = re.finditer(pattern, page.content, re.IGNORECASE | re.MULTILINE)
                
                steps = []
                for match in matches:
                    step = match.group(1).strip()
                    if 10 <= len(step) <= 150:  # Reasonable step length
                        steps.append(step)
                
                if len(steps) >= 2:  # At least 2 steps for a procedure
                    procedure_text = "Procedure: " + " → ".join(steps[:5])  # Limit to 5 steps
                    
                    knowledge = ExtractedKnowledge(
                        content=procedure_text,
                        knowledge_type=KnowledgeType.PROCEDURAL,
                        confidence_score=0.7,
                        relevance_score=self._calculate_procedure_relevance(procedure_text),
                        source_url=page.url,
                        extraction_method=ExtractionMethod.PATTERN_MATCHING,
                        supporting_evidence=steps,
                        related_concepts=self._extract_concepts_from_text(procedure_text),
                        timestamp=datetime.now(),
                        context="Step-by-step procedure"
                    )
                    extracted.append(knowledge)
                    break  # Only extract one procedure per page
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"Procedure extraction failed: {e}")
            return []
    
    # Private helper methods
    
    def _initialize_extraction_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize patterns for knowledge extraction."""
        return {
            'causal_relationship': {
                'pattern': r'(.+?)\s+(?:causes|leads to|results in|triggers)\s+(.+?)(?:\.|,|;)',
                'knowledge_type': KnowledgeType.CAUSAL,
                'confidence': 0.7
            },
            'comparison': {
                'pattern': r'(.+?)\s+(?:is better than|is worse than|compared to|versus)\s+(.+?)(?:\.|,|;)',
                'knowledge_type': KnowledgeType.COMPARATIVE,
                'confidence': 0.6
            },
            'quantitative': {
                'pattern': r'(.+?)\s+(?:is|are|measures|equals)\s+(\d+(?:\.\d+)?(?:\s*%|\s*percent|\s*\w+)?)(?:\.|,|;)',
                'knowledge_type': KnowledgeType.QUANTITATIVE,
                'confidence': 0.8
            },
            'temporal': {
                'pattern': r'(?:In|During|After|Before)\s+(\d{4}|\w+\s+\d{4})[,\s]+(.+?)(?:\.|,|;)',
                'knowledge_type': KnowledgeType.TEMPORAL,
                'confidence': 0.7
            }
        }
    
    def _initialize_evaluation_criteria(self) -> Dict[str, float]:
        """Initialize criteria for knowledge evaluation."""
        return {
            'min_content_length': 10,
            'max_content_length': 500,
            'min_confidence_threshold': 0.3,
            'novelty_weight': 0.2,
            'relevance_weight': 0.3,
            'credibility_weight': 0.25,
            'completeness_weight': 0.25
        }    def
 _filter_and_deduplicate(self, knowledge_list: List[ExtractedKnowledge]) -> List[ExtractedKnowledge]:
        """Filter and remove duplicate knowledge items."""
        try:
            # Filter by quality criteria
            filtered = []
            for knowledge in knowledge_list:
                # Length check
                if not (self.evaluation_criteria['min_content_length'] <= 
                       len(knowledge.content) <= 
                       self.evaluation_criteria['max_content_length']):
                    continue
                
                # Confidence check
                if knowledge.confidence_score < self.evaluation_criteria['min_confidence_threshold']:
                    continue
                
                filtered.append(knowledge)
            
            # Remove duplicates based on content similarity
            deduplicated = []
            for knowledge in filtered:
                is_duplicate = False
                for existing in deduplicated:
                    if self._calculate_content_similarity(knowledge.content, existing.content) > 0.8:
                        # Keep the one with higher confidence
                        if knowledge.confidence_score > existing.confidence_score:
                            deduplicated.remove(existing)
                        else:
                            is_duplicate = True
                        break
                
                if not is_duplicate:
                    deduplicated.append(knowledge)
            
            return deduplicated
            
        except Exception as e:
            self.logger.error(f"Failed to filter and deduplicate knowledge: {e}")
            return knowledge_list
    
    async def _evaluate_knowledge(self, knowledge: ExtractedKnowledge, page: WebPage) -> KnowledgeEvaluation:
        """Evaluate a single knowledge item."""
        try:
            return await self.evaluate_knowledge_quality(knowledge)
        except Exception as e:
            self.logger.error(f"Failed to evaluate knowledge: {e}")
            return KnowledgeEvaluation(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    def _calculate_novelty_score(self, knowledge: ExtractedKnowledge) -> float:
        """Calculate how novel the knowledge is."""
        try:
            # Check against known concepts
            content_concepts = set(knowledge.related_concepts)
            known_overlap = len(content_concepts.intersection(self.known_concepts))
            
            if not content_concepts:
                return 0.5  # Neutral if no concepts identified
            
            novelty = 1.0 - (known_overlap / len(content_concepts))
            
            # Boost novelty for certain knowledge types
            if knowledge.knowledge_type in [KnowledgeType.DEFINITIONAL, KnowledgeType.PROCEDURAL]:
                novelty += 0.1
            
            return min(1.0, max(0.0, novelty))
            
        except Exception:
            return 0.5
    
    def _calculate_utility_score(self, knowledge: ExtractedKnowledge) -> float:
        """Calculate how useful the knowledge is based on interests."""
        try:
            utility = 0.0
            
            # Check relevance to interests
            for concept in knowledge.related_concepts:
                for interest in self.interests:
                    if interest.lower() in concept.lower() or concept.lower() in interest.lower():
                        utility += self.interest_weights.get(interest, 1.0) * 0.2
            
            # Boost utility for certain knowledge types
            type_utilities = {
                KnowledgeType.PROCEDURAL: 0.3,
                KnowledgeType.DEFINITIONAL: 0.2,
                KnowledgeType.CAUSAL: 0.25,
                KnowledgeType.QUANTITATIVE: 0.2
            }
            
            utility += type_utilities.get(knowledge.knowledge_type, 0.1)
            
            return min(1.0, max(0.0, utility))
            
        except Exception:
            return 0.5
    
    def _calculate_credibility_score(self, knowledge: ExtractedKnowledge) -> float:
        """Calculate credibility based on source and content."""
        try:
            # Base credibility from source URL (would be enhanced with actual credibility data)
            credibility = 0.5
            
            url_lower = knowledge.source_url.lower()
            
            # Trusted domains
            if any(domain in url_lower for domain in ['edu', 'gov', 'wikipedia', 'arxiv']):
                credibility += 0.3
            elif any(domain in url_lower for domain in ['nature.com', 'science.org', 'ieee.org']):
                credibility += 0.4
            
            # Supporting evidence boost
            if knowledge.supporting_evidence:
                credibility += min(0.2, len(knowledge.supporting_evidence) * 0.05)
            
            return min(1.0, max(0.0, credibility))
            
        except Exception:
            return 0.5
    
    def _calculate_completeness_score(self, knowledge: ExtractedKnowledge) -> float:
        """Calculate how complete the knowledge is."""
        try:
            completeness = 0.5  # Base score
            
            # Content length factor
            content_length = len(knowledge.content)
            if 50 <= content_length <= 200:
                completeness += 0.2
            elif content_length > 200:
                completeness += 0.1
            
            # Context availability
            if knowledge.context:
                completeness += 0.1
            
            # Supporting evidence
            if knowledge.supporting_evidence:
                completeness += min(0.2, len(knowledge.supporting_evidence) * 0.1)
            
            # Related concepts
            if knowledge.related_concepts:
                completeness += min(0.1, len(knowledge.related_concepts) * 0.02)
            
            return min(1.0, max(0.0, completeness))
            
        except Exception:
            return 0.5 
   def _calculate_pattern_relevance(self, text: str) -> float:
        """Calculate relevance of pattern-matched text."""
        try:
            relevance = 0.5
            
            # Check for interest keywords
            text_lower = text.lower()
            for interest in self.interests:
                if interest.lower() in text_lower:
                    relevance += self.interest_weights.get(interest, 1.0) * 0.1
            
            return min(1.0, max(0.0, relevance))
            
        except Exception:
            return 0.5
    
    def _calculate_entity_relevance(self, entity: str) -> float:
        """Calculate relevance of an extracted entity."""
        try:
            relevance = 0.3  # Base relevance for entities
            
            # Check against interests
            entity_lower = entity.lower()
            for interest in self.interests:
                if interest.lower() in entity_lower or entity_lower in interest.lower():
                    relevance += self.interest_weights.get(interest, 1.0) * 0.2
            
            return min(1.0, max(0.0, relevance))
            
        except Exception:
            return 0.3
    
    def _calculate_definition_relevance(self, term: str) -> float:
        """Calculate relevance of a definition."""
        try:
            relevance = 0.4  # Base relevance for definitions
            
            # Check if term relates to interests
            term_lower = term.lower()
            for interest in self.interests:
                if interest.lower() in term_lower or term_lower in interest.lower():
                    relevance += self.interest_weights.get(interest, 1.0) * 0.3
            
            return min(1.0, max(0.0, relevance))
            
        except Exception:
            return 0.4
    
    def _calculate_procedure_relevance(self, procedure: str) -> float:
        """Calculate relevance of a procedure."""
        try:
            relevance = 0.6  # Higher base relevance for procedures
            
            # Check for interest keywords in procedure
            procedure_lower = procedure.lower()
            for interest in self.interests:
                if interest.lower() in procedure_lower:
                    relevance += self.interest_weights.get(interest, 1.0) * 0.2
            
            return min(1.0, max(0.0, relevance))
            
        except Exception:
            return 0.6
    
    def _extract_concepts_from_text(self, text: str) -> List[str]:
        """Extract key concepts from text."""
        try:
            # Simple concept extraction (would be enhanced with NLP in full implementation)
            concepts = []
            
            # Extract capitalized words (potential proper nouns)
            capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', text)
            concepts.extend(capitalized_words)
            
            # Extract technical terms (words with specific patterns)
            technical_terms = re.findall(r'\b\w*(?:AI|ML|API|SDK|tion|ing|ism|ity)\b', text, re.IGNORECASE)
            concepts.extend(technical_terms)
            
            # Remove duplicates and filter
            unique_concepts = list(set(concepts))
            filtered_concepts = [
                concept for concept in unique_concepts 
                if len(concept) > 2 and concept.lower() not in ['the', 'and', 'for', 'with']
            ]
            
            return filtered_concepts[:10]  # Limit to top 10 concepts
            
        except Exception:
            return []
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        try:
            # Simple sentence splitting
            sentences = re.split(r'[.!?]+', text)
            return [s.strip() for s in sentences if len(s.strip()) > 10]
        except Exception:
            return []
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        try:
            # Simple word-based similarity
            words1 = set(content1.lower().split())
            words2 = set(content2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception:
            return 0.0
    
    async def _load_knowledge_base(self) -> None:
        """Load existing knowledge base."""
        # Placeholder for loading from persistent storage
        pass
    
    async def _save_knowledge_base(self) -> None:
        """Save knowledge base to persistent storage."""
        # Placeholder for saving to persistent storage
        pass