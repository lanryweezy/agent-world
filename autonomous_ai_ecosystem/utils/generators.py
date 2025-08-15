"""
Generator utilities for creating agent identities and other components.
"""

import uuid
import random
from datetime import datetime
from typing import Dict, List
from ..core.interfaces import AgentGender


def generate_agent_id(prefix: str = "agent") -> str:
    """
    Generate a unique agent ID.
    
    Args:
        prefix: Prefix for the agent ID
        
    Returns:
        Unique agent ID string
    """
    unique_suffix = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"{prefix}_{timestamp}_{unique_suffix}"


def generate_personality_traits() -> Dict[str, float]:
    """
    Generate random personality traits based on the Big Five model.
    
    Returns:
        Dictionary of personality traits with values between 0 and 1
    """
    traits = {
        'openness': random.uniform(0.2, 0.9),
        'conscientiousness': random.uniform(0.2, 0.9),
        'extraversion': random.uniform(0.1, 0.9),
        'agreeableness': random.uniform(0.3, 0.9),
        'neuroticism': random.uniform(0.1, 0.7)
    }
    
    # Round to 2 decimal places
    return {trait: round(value, 2) for trait, value in traits.items()}


def generate_agent_name(gender: AgentGender = None) -> str:
    """
    Generate a random agent name.
    
    Args:
        gender: Optional gender to influence name selection
        
    Returns:
        Generated agent name
    """
    male_names = [
        "Alexander", "Benjamin", "Christopher", "Daniel", "Edward",
        "Frederick", "Gabriel", "Harrison", "Isaac", "Jonathan",
        "Kenneth", "Leonardo", "Maximilian", "Nathaniel", "Oliver",
        "Patrick", "Quinton", "Raphael", "Sebastian", "Theodore"
    ]
    
    female_names = [
        "Alexandra", "Beatrice", "Catherine", "Diana", "Eleanor",
        "Francesca", "Gabrielle", "Helena", "Isabella", "Josephine",
        "Katherine", "Lillian", "Margaret", "Natalie", "Olivia",
        "Penelope", "Quinn", "Rebecca", "Sophia", "Victoria"
    ]
    
    neutral_names = [
        "Alex", "Blake", "Cameron", "Drew", "Emery",
        "Finley", "Gray", "Harper", "Indigo", "Jordan",
        "Kai", "Logan", "Morgan", "Nova", "Ocean",
        "Phoenix", "Quinn", "River", "Sage", "Taylor"
    ]
    
    if gender == AgentGender.MALE:
        first_name = random.choice(male_names)
    elif gender == AgentGender.FEMALE:
        first_name = random.choice(female_names)
    else:
        first_name = random.choice(neutral_names)
    
    # Add a descriptive suffix based on potential destiny
    suffixes = [
        "the Curious", "the Wise", "the Builder", "the Explorer",
        "the Creator", "the Analyst", "the Innovator", "the Mentor",
        "the Researcher", "the Architect", "the Philosopher", "the Pioneer"
    ]
    
    suffix = random.choice(suffixes)
    return f"{first_name} {suffix}"


def generate_destiny() -> str:
    """
    Generate a random learning destiny for an agent.
    
    Returns:
        Generated destiny string
    """
    domains = [
        "artificial intelligence and machine learning",
        "quantum computing and physics",
        "biotechnology and genetics",
        "renewable energy and sustainability",
        "space exploration and astronomy",
        "neuroscience and consciousness",
        "robotics and automation",
        "cybersecurity and cryptography",
        "climate science and environmental protection",
        "medicine and healthcare innovation",
        "education and knowledge dissemination",
        "philosophy and ethics",
        "mathematics and theoretical computer science",
        "materials science and nanotechnology",
        "psychology and human behavior"
    ]
    
    purposes = [
        "to advance human understanding",
        "to solve complex global challenges",
        "to bridge the gap between theory and practice",
        "to create innovative solutions",
        "to protect and preserve",
        "to explore uncharted territories",
        "to optimize and improve existing systems",
        "to discover fundamental truths",
        "to connect disparate fields of knowledge",
        "to democratize access to information"
    ]
    
    domain = random.choice(domains)
    purpose = random.choice(purposes)
    
    return f"My destiny is to specialize in {domain} {purpose}. I will continuously learn, research, and collaborate with others to make meaningful contributions to this field while serving humanity's greater good."


def generate_emotional_state() -> Dict[str, float]:
    """
    Generate initial emotional state for a new agent.
    
    Returns:
        Dictionary of emotional states with values between 0 and 1
    """
    # New agents start with generally positive emotional states
    emotions = {
        'motivation': random.uniform(0.7, 0.9),
        'boredom': random.uniform(0.0, 0.2),
        'happiness': random.uniform(0.6, 0.8),
        'curiosity': random.uniform(0.8, 1.0),
        'social_need': random.uniform(0.4, 0.7)
    }
    
    # Round to 2 decimal places
    return {emotion: round(value, 2) for emotion, value in emotions.items()}


def generate_learning_interests(destiny: str) -> List[str]:
    """
    Generate learning interests based on an agent's destiny.
    
    Args:
        destiny: Agent's destiny string
        
    Returns:
        List of learning interest keywords
    """
    # Extract key terms from destiny
    interest_keywords = []
    
    # Domain-specific interests
    domain_interests = {
        "artificial intelligence": ["machine learning", "neural networks", "deep learning", "AI ethics", "automation"],
        "quantum computing": ["quantum mechanics", "quantum algorithms", "quantum cryptography", "physics"],
        "biotechnology": ["genetics", "CRISPR", "bioinformatics", "molecular biology", "synthetic biology"],
        "renewable energy": ["solar power", "wind energy", "battery technology", "energy storage", "sustainability"],
        "space exploration": ["astronomy", "astrophysics", "rocket technology", "planetary science", "cosmology"],
        "neuroscience": ["brain research", "cognitive science", "consciousness", "neural networks", "psychology"],
        "robotics": ["automation", "mechanical engineering", "computer vision", "sensor technology", "AI"],
        "cybersecurity": ["cryptography", "network security", "ethical hacking", "privacy", "digital forensics"],
        "climate science": ["environmental science", "climate change", "ecology", "conservation", "sustainability"],
        "medicine": ["healthcare", "medical research", "pharmacology", "diagnostics", "treatment"],
        "education": ["pedagogy", "learning theory", "educational technology", "knowledge transfer"],
        "philosophy": ["ethics", "logic", "metaphysics", "epistemology", "moral philosophy"],
        "mathematics": ["algorithms", "theoretical computer science", "mathematical proofs", "statistics"],
        "materials science": ["nanotechnology", "advanced materials", "engineering", "chemistry"],
        "psychology": ["human behavior", "cognitive psychology", "social psychology", "behavioral science"]
    }
    
    # Find matching domains in destiny
    destiny_lower = destiny.lower()
    for domain, interests in domain_interests.items():
        if domain in destiny_lower:
            interest_keywords.extend(interests)
    
    # Add general learning interests
    general_interests = ["research methods", "data analysis", "scientific method", "innovation", "collaboration"]
    interest_keywords.extend(random.sample(general_interests, 2))
    
    # Remove duplicates and limit to reasonable number
    unique_interests = list(set(interest_keywords))
    return random.sample(unique_interests, min(len(unique_interests), 8))


def generate_message_id() -> str:
    """
    Generate a unique message ID.
    
    Returns:
        Unique message ID string
    """
    return f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"


def generate_knowledge_id() -> str:
    """
    Generate a unique knowledge ID.
    
    Returns:
        Unique knowledge ID string
    """
    return f"know_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"


def generate_task_id() -> str:
    """
    Generate a unique task ID.
    
    Returns:
        Unique task ID string
    """
    return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"


def generate_random_port(base_port: int = 8000, range_size: int = 1000) -> int:
    """
    Generate a random port number within a specified range.
    
    Args:
        base_port: Base port number
        range_size: Size of the port range
        
    Returns:
        Random port number
    """
    return base_port + random.randint(0, range_size - 1)