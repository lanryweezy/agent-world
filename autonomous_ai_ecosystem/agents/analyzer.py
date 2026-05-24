"""
Structured Analyzer for the ASI-EVOLVE framework.

Translates complex multi-dimensional experimental outcomes into structured,
actionable insights for future evolution iterations.
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from .brain import AIBrain, ThoughtType
from ..core.logger import get_agent_logger

class StructuredAnalyzer:
    """
    Dedicated analyzer that distills experimental logs, metrics, and failures
    into reusable insights (lessons) stored in the database.
    """

    def __init__(self, agent_id: str, brain: AIBrain):
        self.agent_id = agent_id
        self.brain = brain
        self.logger = get_agent_logger(agent_id, "structured_analyzer")

    async def analyze_experiment(
        self,
        program_code: str,
        execution_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze an experimental run and produce a structured report.
        """
        self.logger.info("Analyzing experiment results...")

        input_data = {
            "program_code": program_code,
            "execution_result": execution_result,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

        # Use AI Brain to perform analysis
        thought = await self.brain.think(
            thought_type=ThoughtType.ANALYSIS,
            input_data=input_data,
            template_id="experimental_analysis"
        )

        analysis_report = thought.output
        self.logger.info("Experimental analysis completed.")

        return {
            "analysis": analysis_report.get("analysis", ""),
            "insights": analysis_report.get("insights", []),
            "lessons_learned": analysis_report.get("lessons_learned", []),
            "suggested_next_steps": analysis_report.get("suggested_next_steps", []),
            "confidence": thought.confidence
        }

    def register_template(self):
        """Register the analysis template with the brain."""
        template_id = "experimental_analysis"
        if template_id not in self.brain.prompt_templates:
            from .brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name="Experimental Result Analysis",
                template="""
You are an expert AI Research Scientist. Analyze the following experimental outcome:

Program Code:
{program_code}

Execution Result:
{execution_result}

Context:
{context}

Please provide a structured analysis report:
1. "analysis": A detailed evaluation of why the code performed as it did.
2. "insights": Key scientific or technical insights gained.
3. "lessons_learned": Concrete, reusable lessons for future iterations (e.g., "don't use X with Y", "Z is more efficient than W").
4. "suggested_next_steps": Specific ideas for the next research round.

Format your response as JSON.
""",
                variables=["program_code", "execution_result", "context"],
                thought_type=ThoughtType.ANALYSIS,
                max_tokens=2000,
                temperature=0.4
            )
