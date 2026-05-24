"""
Autonomous Deployment agent for the ASI-EVOLVE framework.

Handles the productionization of successfully evolved code, packaging it
into production-ready formats like Dockerfiles or API endpoints.
"""

from typing import Dict, Any, List
from .brain import AIBrain, ThoughtType
from ..core.logger import get_agent_logger, log_agent_event

class AutonomousDeployer:
    """
    Expert DevOps and Reliability Engineer. Transforms experimental code into
    stable, production-ready assets.
    """

    def __init__(self, agent_id: str, brain: AIBrain):
        self.agent_id = agent_id
        self.brain = brain
        self.logger = get_agent_logger(agent_id, "autonomous_deployer")

    async def generate_production_package(self, evolved_code: str, service_name: str) -> Dict[str, str]:
        """
        Generate a production deployment package for the evolved code.
        """
        self.logger.info(f"Generating production package for {service_name}...")

        input_data = {
            "code": evolved_code,
            "service_name": service_name
        }

        template_id = "deployment_generation"
        if template_id not in self.brain.prompt_templates:
            from .brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name="Autonomous Deployment Generation",
                template="""
You are a Senior Cloud Infrastructure Architect. Create a production-ready deployment package for this evolved code:

Service Name: {service_name}
Evolved Code:
{code}

Please provide:
1. "dockerfile": A complete Dockerfile to containerize this code.
2. "api_wrapper": A FastAPI or Flask wrapper to expose the code as an endpoint.
3. "scaling_config": A Kubernetes manifest or scaling recommendation.

Format your response as JSON.
""",
                variables=["service_name", "code"],
                thought_type=ThoughtType.PLANNING,
                max_tokens=3000,
                temperature=0.3
            )

        thought = await self.brain.think(
            thought_type=ThoughtType.PLANNING,
            input_data=input_data,
            template_id=template_id
        )

        package = thought.output
        self.logger.info(f"Production package for {service_name} created successfully.")

        log_agent_event(self.agent_id, "production_package_generated", {"service": service_name})

        return {
            "dockerfile": package.get("dockerfile", ""),
            "api_wrapper": package.get("api_wrapper", ""),
            "scaling_config": package.get("scaling_config", "")
        }
