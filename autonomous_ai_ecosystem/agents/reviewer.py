"""
Reviewer agent for the ASI-EVOLVE framework.

Inspired by "The AI Scientist," this agent provides critical review of
proposed code modifications before they are executed in the sandbox.
"""

from typing import Dict, Any, List
from .brain import AIBrain, ThoughtType
from ..core.logger import get_agent_logger

class CritiqueReviewer:
    """
    Expert reviewer that identifies potential flaws, security issues,
    or optimization opportunities in proposed code designs. Supports Peer Discussion.
    """

    def __init__(self, agent_id: str, brain: AIBrain):
        self.agent_id = agent_id
        self.brain = brain
        self.logger = get_agent_logger(agent_id, "critique_reviewer")

    async def review_design(
        self,
        proposed_code: str,
        motivation: str,
        task_description: str,
        enable_discussion: bool = True
    ) -> Dict[str, Any]:
        """
        Review a proposed code design and provide a score and feedback.
        """
        self.logger.info("Reviewing proposed design...")

        input_data = {
            "proposed_code": proposed_code,
            "motivation": motivation,
            "task_description": task_description
        }

        template_id = "code_review"
        if template_id not in self.brain.prompt_templates:
            from .brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name="Autonomous Code Review",
                template="""
You are a Senior AI Security and Software Architect. Review the following code proposal:

Task: {task_description}
Motivation: {motivation}

Proposed Code:
{proposed_code}

Please provide a critical review:
1. "score": A rating from 0.0 to 1.0 (1.0 = perfect, 0.0 = dangerous or broken).
2. "critique": Detailed technical criticism.
3. "risks": Potential security or runtime risks identified.
4. "improvement_suggestions": Concrete ways to fix identified issues.
5. "should_proceed": Boolean, whether this code is safe enough to test in a sandbox.

Format your response as JSON.
""",
                variables=["task_description", "motivation", "proposed_code"],
                thought_type=ThoughtType.ANALYSIS,
                max_tokens=2000,
                temperature=0.3
            )

        thought = await self.brain.think(
            thought_type=ThoughtType.ANALYSIS,
            input_data=input_data,
            template_id=template_id
        )

        review = thought.output

        if enable_discussion and review.get("score", 0.0) < 0.9:
            # Perform "Peer Discussion" (Self-Correction loop)
            self.logger.info("Initiating peer discussion for closer inspection...")
            discussion_input = {
                "initial_review": review,
                "proposed_code": proposed_code,
                "task_description": task_description
            }

            discussion_template = "peer_discussion"
            if discussion_template not in self.brain.prompt_templates:
                from .brain import PromptTemplate
                self.brain.prompt_templates[discussion_template] = PromptTemplate(
                    template_id=discussion_template,
                    name="Research Peer Discussion",
                    template="""
You are participating in a peer discussion about a code proposal.

Initial Review:
{initial_review}

Proposed Code:
{proposed_code}

Task: {task_description}

Please debate the initial review points. Are they too harsh? Did they miss a subtle bug?
Produce a FINAL consensus review with the same JSON keys: score, critique, risks, improvement_suggestions, should_proceed.
""",
                    variables=["initial_review", "proposed_code", "task_description"],
                    thought_type=ThoughtType.ANALYSIS,
                    max_tokens=2000,
                    temperature=0.5
                )

            consensus_thought = await self.brain.think(
                thought_type=ThoughtType.ANALYSIS,
                input_data=discussion_input,
                template_id=discussion_template
            )
            review = consensus_thought.output
            self.logger.info("Peer discussion reached consensus.")

        self.logger.info(f"Final Review completed. Safe to proceed: {review.get('should_proceed', False)}")

        return {
            "score": review.get("score", 0.0),
            "critique": review.get("critique", ""),
            "risks": review.get("risks", []),
            "suggestions": review.get("improvement_suggestions", []),
            "should_proceed": review.get("should_proceed", False),
            "confidence": thought.confidence
        }
