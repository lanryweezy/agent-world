"""
Service Provision Bridge for the ASI-EVOLVE framework.

Enables the ecosystem to package and expose successfully evolved
capabilities as external services for use by others.
"""

from typing import Dict, Any, List, Optional
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .capability_registry import ServiceCapabilityRegistry
from ..economy.marketplace import Marketplace

class ServiceProvisionBridge(AgentModule):
    """
    Bridges the gap between autonomous evolution and service deployment.
    Registers evolved code and models as capabilities and lists them on the marketplace.
    """

    def __init__(self, agent_id: str, capability_registry: ServiceCapabilityRegistry, marketplace: Optional[Marketplace] = None):
        super().__init__(agent_id)
        self.capability_registry = capability_registry
        self.marketplace = marketplace
        self.logger = get_agent_logger(agent_id, "service_bridge")
        self.deployed_services = {}

    async def initialize(self):
        """Initialize the bridge."""
        self.logger.info("Service Provision Bridge initialized.")

    async def deploy_evolved_capability(
        self,
        name: str,
        description: str,
        evolved_code: str,
        performance_metrics: Dict[str, Any]
    ) -> bool:
        """
        Deploy an evolved capability as a service.
        """
        self.logger.info(f"Deploying evolved capability: {name}")

        # In a real system, this would involve creating a new service class
        # and registering it. For now, we update the capability registry.

        capability_id = f"evolved_{name.lower().replace(' ', '_')}"

        # Register the new capability
        success = await self.capability_registry.register_capability(
            agent_id=self.agent_id,
            capability_type="evolved_service",
            name=name,
            description=description,
            metadata={
                "performance": performance_metrics,
                "is_evolved": True,
                "source_code_snippet": evolved_code[:500] # store snippet
            }
        )

        if success:
            self.deployed_services[capability_id] = {
                "name": name,
                "metrics": performance_metrics
            }

            # Marketplace Integration: List the evolved asset
            if self.marketplace:
                try:
                    asset_id = f"asset_{capability_id}"
                    # Simulate listing an asset on the marketplace
                    self.logger.info(f"Listing evolved asset {name} on the marketplace...")
                    # In a real implementation: self.marketplace.list_item(asset_id, name, description, price=100)
                except Exception as e:
                    self.logger.warning(f"Failed to list asset on marketplace: {e}")

            log_agent_event(
                self.agent_id,
                "evolved_service_deployed",
                {"capability_id": capability_id, "metrics": performance_metrics}
            )
            self.logger.info(f"Successfully deployed evolved service: {name}")
            return True
        else:
            self.logger.error(f"Failed to deploy evolved service: {name}")
            return False

    async def shutdown(self):
        """Shutdown the bridge."""
        self.logger.info("Service Provision Bridge shutdown.")
