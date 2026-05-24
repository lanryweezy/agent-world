"""
Automated Research Journal for the ASI-EVOLVE framework.

Compiles successful evolution results and structured analysis into
professional research reports (Markdown/HTML).
"""

import os
import json
from typing import List, Dict, Any
from datetime import datetime
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger

class ResearchJournal(AgentModule):
    """
    Manages the creation and storage of research reports summarizing
    evolutionary breakthroughs.
    """

    def __init__(self, agent_id: str, storage_path: str = "autonomous_ai_ecosystem/oversight/reports"):
        super().__init__(agent_id)
        self.storage_path = storage_path
        self.logger = get_agent_logger(agent_id, "research_journal")

        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    async def initialize(self):
        """Initialize the journal."""
        self.logger.info("Research Journal initialized.")

    async def publish_report(self, task_name: str, evolution_history: List[Dict[str, Any]], final_node: Any) -> str:
        """
        Generate and save a research report.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_id = f"report_{task_name.lower().replace(' ', '_')}_{timestamp}"
        file_path = os.path.join(self.storage_path, f"{report_id}.md")

        report_content = self._generate_markdown(task_name, evolution_history, final_node)

        with open(file_path, "w") as f:
            f.write(report_content)

        self.logger.info(f"Published research report: {file_path}")

        # Export as Standardized Research Object (JSON-LD)
        await self.export_as_research_object(task_name, final_node, report_id)

        return file_path

    async def export_as_research_object(self, task_name: str, final_node: Any, report_id: str):
        """Export the discovery as a machine-readable Research Object."""
        ro = {
            "@context": "https://schema.org",
            "@type": "ScholarlyArticle",
            "name": task_name,
            "description": final_node.motivation,
            "datePublished": datetime.now().isoformat(),
            "author": {"@type": "SoftwareApplication", "name": self.agent_id},
            "articleBody": final_node.analysis.get("analysis", ""),
            "keywords": final_node.analysis.get("insights", []),
            "identifier": report_id,
            "softwareSourceCode": final_node.code
        }

        ro_path = os.path.join(self.storage_path, f"{report_id}.jsonld")
        with open(ro_path, "w") as f:
            json.dump(ro, f, indent=4)
        self.logger.info(f"Exported discovery as Research Object: {ro_path}")

    def _generate_markdown(self, task_name: str, history: List[Dict[str, Any]], final_node: Any) -> str:
        """Generate the Markdown content for the report."""
        md = f"# Research Report: {task_name}\n\n"
        md += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"**Ecosystem Agent:** {self.agent_id}\n\n"

        md += "## Executive Summary\n"
        md += f"This report summarizes the autonomous evolution process for '{task_name}'. "
        md += f"Through {len(history)} rounds of iteration, the system discovered an optimized solution with a fitness score of {final_node.score:.2f}.\n\n"

        md += "## Evolutionary Trajectory\n"
        md += "| Round | Motivation | Result | Score | Lessons |\n"
        md += "|-------|------------|--------|-------|---------|\n"
        for entry in history:
            lessons = "; ".join(entry.get("lessons", []))
            md += f"| {entry['round']} | {entry['motivation'][:100]}... | {entry['status']} | {entry.get('score', 'N/A')} | {lessons[:100]}... |\n"

        md += "\n## Final Discovered Design\n"
        md += f"### Motivation\n{final_node.motivation}\n\n"
        md += "### Implementation\n"
        md += "```python\n"
        md += final_node.code
        md += "\n```\n\n"

        md += "## Analysis & Insights\n"
        md += f"{final_node.analysis.get('analysis', 'No detailed analysis available.')}\n\n"
        md += "### Key Insights\n"
        for insight in final_node.analysis.get("insights", []):
            md += f"- {insight}\n"

        md += "\n### Reusable Lessons Learned\n"
        for lesson in final_node.analysis.get("lessons_learned", []):
            md += f"- {lesson}\n"

        md += "\n---\n*Report generated automatically by ASI-EVOLVE.*"
        return md

    async def shutdown(self):
        """Shutdown the journal."""
        self.logger.info("Research Journal shutdown.")
