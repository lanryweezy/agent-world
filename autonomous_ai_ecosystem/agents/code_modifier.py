"""
Safe code modification system for autonomous AI agents.

This module implements safe code modification capabilities using AST manipulation,
allowing agents to modify their own code while maintaining safety and security.
"""

import ast
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .code_analyzer import CodeAnalyzer, ModificationProposal, CodeRiskLevel


class ModificationType(Enum):
    """Types of code modifications."""
    ADD_FUNCTION = "add_function"
    MODIFY_FUNCTION = "modify_function"
    DELETE_FUNCTION = "delete_function"
    ADD_CLASS = "add_class"
    MODIFY_CLASS = "modify_class"
    DELETE_CLASS = "delete_class"
    ADD_IMPORT = "add_import"
    REMOVE_IMPORT = "remove_import"
    MODIFY_VARIABLE = "modify_variable"
    ADD_METHOD = "add_method"
    MODIFY_METHOD = "modify_method"


class ModificationStatus(Enum):
    """Status of code modifications."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ModificationRecord:
    """Record of a code modification."""
    modification_id: str
    proposal: ModificationProposal
    status: ModificationStatus
    created_at: datetime
    applied_at: Optional[datetime] = None
    rollback_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    backup_path: Optional[str] = None


@dataclass
class CodeTemplate:
    """Template for generating code."""
    template_id: str
    name: str
    description: str
    template_code: str
    parameters: List[str]
    risk_level: CodeRiskLevel
    category: str


class CodeModifier(AgentModule):
    """
    Safe code modification system that can analyze, validate, and apply
    code changes while maintaining safety and providing rollback capabilities.
    """
    
    def __init__(self, agent_id: str, code_analyzer: CodeAnalyzer):
        super().__init__(agent_id)
        self.code_analyzer = code_analyzer
        self.logger = get_agent_logger(agent_id, "code_modifier")
        
        # Modification tracking
        self.modification_history: List[ModificationRecord] = []
        self.pending_modifications: Dict[str, ModificationRecord] = {}
        self.max_history_size = 1000
        
        # Backup management
        self.backup_directory = f"data/agents/{agent_id}/code_backups"
        self.max_backups = 50
        
        # Code templates
        self.code_templates = self._initialize_code_templates()
        
        # Safety settings
        self.safety_settings = {
            "require_approval_for_high_risk": True,
            "auto_approve_safe_modifications": True,
            "create_backups": True,
            "max_modifications_per_session": 10,
            "rollback_on_failure": True
        }
        
        # Modification statistics
        self.modification_stats = {
            "total_proposals": 0,
            "approved_modifications": 0,
            "rejected_modifications": 0,
            "successful_applications": 0,
            "failed_applications": 0,
            "rollbacks_performed": 0
        }
        
        self.logger.info(f"Code modifier initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the code modifier."""
        try:
            # Create backup directory
            Path(self.backup_directory).mkdir(parents=True, exist_ok=True)
            
            # Load modification history
            await self._load_modification_history()
            
            self.logger.info("Code modifier initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize code modifier: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the code modifier gracefully."""
        try:
            # Save modification history
            await self._save_modification_history()
            
            # Clean up old backups
            await self._cleanup_old_backups()
            
            self.logger.info("Code modifier shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during code modifier shutdown: {e}")
    
    async def propose_modification(
        self,
        target_file: str,
        modification_type: ModificationType,
        target_element: str,
        new_code: str,
        justification: str,
        original_code: str = ""
    ) -> str:
        """
        Propose a code modification.
        
        Args:
            target_file: File to modify
            modification_type: Type of modification
            target_element: Element to modify (function name, class name, etc.)
            new_code: New code to add/replace
            justification: Reason for the modification
            original_code: Original code being replaced (if applicable)
            
        Returns:
            Modification ID for tracking
        """
        try:
            modification_id = f"mod_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.modification_history)}"
            
            # Create modification proposal
            proposal = ModificationProposal(
                proposal_id=modification_id,
                target_file=target_file,
                modification_type=modification_type.value,
                target_element=target_element,
                original_code=original_code,
                proposed_code=new_code,
                justification=justification,
                risk_assessment=CodeRiskLevel.SAFE,  # Will be updated by analysis
                estimated_impact={}
            )
            
            # Assess risk
            risk_assessment = await self.code_analyzer.assess_modification_risk(proposal)
            proposal.risk_assessment = CodeRiskLevel(risk_assessment["risk_level"])
            
            # Create modification record
            record = ModificationRecord(
                modification_id=modification_id,
                proposal=proposal,
                status=ModificationStatus.PENDING,
                created_at=datetime.now()
            )
            
            # Store pending modification
            self.pending_modifications[modification_id] = record
            self.modification_history.append(record)
            
            # Update statistics
            self.modification_stats["total_proposals"] += 1
            
            # Auto-approve safe modifications if enabled
            if (self.safety_settings["auto_approve_safe_modifications"] and 
                risk_assessment["should_allow"]):
                await self.approve_modification(modification_id)
            
            log_agent_event(
                self.agent_id,
                "modification_proposed",
                {
                    "modification_id": modification_id,
                    "target_file": target_file,
                    "modification_type": modification_type.value,
                    "risk_level": proposal.risk_assessment.value,
                    "auto_approved": risk_assessment["should_allow"]
                }
            )
            
            self.logger.info(f"Proposed modification {modification_id}: {modification_type.value} in {target_file}")
            
            return modification_id
            
        except Exception as e:
            self.logger.error(f"Failed to propose modification: {e}")
            raise
    
    async def approve_modification(self, modification_id: str) -> bool:
        """
        Approve a pending modification.
        
        Args:
            modification_id: ID of the modification to approve
            
        Returns:
            True if approved successfully
        """
        try:
            if modification_id not in self.pending_modifications:
                raise ValueError(f"Modification {modification_id} not found or not pending")
            
            record = self.pending_modifications[modification_id]
            
            # Update status
            record.status = ModificationStatus.APPROVED
            
            # Remove from pending
            del self.pending_modifications[modification_id]
            
            # Update statistics
            self.modification_stats["approved_modifications"] += 1
            
            log_agent_event(
                self.agent_id,
                "modification_approved",
                {"modification_id": modification_id}
            )
            
            self.logger.info(f"Approved modification {modification_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to approve modification {modification_id}: {e}")
            return False
    
    async def reject_modification(self, modification_id: str, reason: str = "") -> bool:
        """
        Reject a pending modification.
        
        Args:
            modification_id: ID of the modification to reject
            reason: Reason for rejection
            
        Returns:
            True if rejected successfully
        """
        try:
            if modification_id not in self.pending_modifications:
                raise ValueError(f"Modification {modification_id} not found or not pending")
            
            record = self.pending_modifications[modification_id]
            
            # Update status
            record.status = ModificationStatus.REJECTED
            record.error_message = reason
            
            # Remove from pending
            del self.pending_modifications[modification_id]
            
            # Update statistics
            self.modification_stats["rejected_modifications"] += 1
            
            log_agent_event(
                self.agent_id,
                "modification_rejected",
                {"modification_id": modification_id, "reason": reason}
            )
            
            self.logger.info(f"Rejected modification {modification_id}: {reason}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reject modification {modification_id}: {e}")
            return False
    
    async def apply_modification(self, modification_id: str) -> bool:
        """
        Apply an approved modification.
        
        Args:
            modification_id: ID of the modification to apply
            
        Returns:
            True if applied successfully
        """
        try:
            # Find the modification record
            record = None
            for mod_record in self.modification_history:
                if mod_record.modification_id == modification_id:
                    record = mod_record
                    break
            
            if not record:
                raise ValueError(f"Modification {modification_id} not found")
            
            if record.status != ModificationStatus.APPROVED:
                raise ValueError(f"Modification {modification_id} is not approved")
            
            # Create backup if enabled
            backup_path = None
            if self.safety_settings["create_backups"]:
                backup_path = await self._create_backup(record.proposal.target_file)
                record.backup_path = backup_path
            
            # Apply the modification
            success = await self._apply_modification_to_file(record.proposal)
            
            if success:
                record.status = ModificationStatus.APPLIED
                record.applied_at = datetime.now()
                self.modification_stats["successful_applications"] += 1
                
                log_agent_event(
                    self.agent_id,
                    "modification_applied",
                    {
                        "modification_id": modification_id,
                        "target_file": record.proposal.target_file,
                        "backup_created": backup_path is not None
                    }
                )
                
                self.logger.info(f"Applied modification {modification_id} successfully")
            else:
                record.status = ModificationStatus.FAILED
                record.error_message = "Failed to apply modification"
                self.modification_stats["failed_applications"] += 1
                
                # Rollback if enabled
                if self.safety_settings["rollback_on_failure"] and backup_path:
                    await self._rollback_modification(modification_id)
                
                self.logger.error(f"Failed to apply modification {modification_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to apply modification {modification_id}: {e}")
            return False
    
    async def rollback_modification(self, modification_id: str) -> bool:
        """
        Rollback a previously applied modification.
        
        Args:
            modification_id: ID of the modification to rollback
            
        Returns:
            True if rolled back successfully
        """
        try:
            return await self._rollback_modification(modification_id)
        except Exception as e:
            self.logger.error(f"Failed to rollback modification {modification_id}: {e}")
            return False
    
    async def generate_code_from_template(
        self,
        template_id: str,
        parameters: Dict[str, str]
    ) -> str:
        """
        Generate code from a template.
        
        Args:
            template_id: ID of the template to use
            parameters: Parameters to fill in the template
            
        Returns:
            Generated code string
        """
        try:
            if template_id not in self.code_templates:
                raise ValueError(f"Template {template_id} not found")
            
            template = self.code_templates[template_id]
            
            # Validate parameters
            missing_params = set(template.parameters) - set(parameters.keys())
            if missing_params:
                raise ValueError(f"Missing parameters: {missing_params}")
            
            # Generate code
            code = template.template_code
            for param, value in parameters.items():
                code = code.replace(f"{{{param}}}", value)
            
            self.logger.debug(f"Generated code from template {template_id}")
            
            return code
            
        except Exception as e:
            self.logger.error(f"Failed to generate code from template {template_id}: {e}")
            raise
    
    def get_pending_modifications(self) -> List[ModificationRecord]:
        """Get all pending modifications."""
        return list(self.pending_modifications.values())
    
    def get_modification_history(self, limit: int = 50) -> List[ModificationRecord]:
        """Get modification history."""
        return self.modification_history[-limit:]
    
    def get_modification_statistics(self) -> Dict[str, Any]:
        """Get modification statistics."""
        return {
            **self.modification_stats,
            "pending_count": len(self.pending_modifications),
            "history_size": len(self.modification_history),
            "backup_directory": self.backup_directory
        }
    
    # Private helper methods
    
    async def _apply_modification_to_file(self, proposal: ModificationProposal) -> bool:
        """Apply a modification to a file."""
        try:
            target_file = proposal.target_file
            
            # Read current file content
            if os.path.exists(target_file):
                with open(target_file, 'r', encoding='utf-8') as f:
                    current_content = f.read()
            else:
                current_content = ""
            
            # Parse current AST
            if current_content:
                try:
                    current_ast = ast.parse(current_content)
                except SyntaxError as e:
                    self.logger.error(f"Syntax error in current file {target_file}: {e}")
                    return False
            else:
                current_ast = ast.Module(body=[], type_ignores=[])
            
            # Apply modification based on type
            modification_type = ModificationType(proposal.modification_type)
            
            if modification_type == ModificationType.ADD_FUNCTION:
                success = await self._add_function_to_ast(current_ast, proposal)
            elif modification_type == ModificationType.MODIFY_FUNCTION:
                success = await self._modify_function_in_ast(current_ast, proposal)
            elif modification_type == ModificationType.DELETE_FUNCTION:
                success = await self._delete_function_from_ast(current_ast, proposal)
            elif modification_type == ModificationType.ADD_CLASS:
                success = await self._add_class_to_ast(current_ast, proposal)
            elif modification_type == ModificationType.ADD_IMPORT:
                success = await self._add_import_to_ast(current_ast, proposal)
            else:
                self.logger.warning(f"Unsupported modification type: {modification_type}")
                return False
            
            if not success:
                return False
            
            # Convert AST back to code
            try:
                if hasattr(ast, 'unparse'):
                    new_content = ast.unparse(current_ast)
                else:
                    # Fallback for older Python versions
                    new_content = self._ast_to_code(current_ast)
            except Exception as e:
                self.logger.error(f"Failed to convert AST to code: {e}")
                return False
            
            # Write modified content
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply modification to file: {e}")
            return False
    
    async def _add_function_to_ast(self, ast_tree: ast.Module, proposal: ModificationProposal) -> bool:
        """Add a function to the AST."""
        try:
            # Parse the new function
            new_function_ast = ast.parse(proposal.proposed_code)
            
            if not new_function_ast.body or not isinstance(new_function_ast.body[0], ast.FunctionDef):
                self.logger.error("Proposed code is not a valid function")
                return False
            
            new_function = new_function_ast.body[0]
            
            # Add to the module
            ast_tree.body.append(new_function)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add function to AST: {e}")
            return False
    
    async def _modify_function_in_ast(self, ast_tree: ast.Module, proposal: ModificationProposal) -> bool:
        """Modify a function in the AST."""
        try:
            # Find the target function
            target_function = None
            for i, node in enumerate(ast_tree.body):
                if isinstance(node, ast.FunctionDef) and node.name == proposal.target_element:
                    target_function = node
                    target_index = i
                    break
            
            if not target_function:
                self.logger.error(f"Function {proposal.target_element} not found")
                return False
            
            # Parse the new function
            new_function_ast = ast.parse(proposal.proposed_code)
            
            if not new_function_ast.body or not isinstance(new_function_ast.body[0], ast.FunctionDef):
                self.logger.error("Proposed code is not a valid function")
                return False
            
            new_function = new_function_ast.body[0]
            
            # Replace the function
            ast_tree.body[target_index] = new_function
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to modify function in AST: {e}")
            return False
    
    async def _delete_function_from_ast(self, ast_tree: ast.Module, proposal: ModificationProposal) -> bool:
        """Delete a function from the AST."""
        try:
            # Find and remove the target function
            for i, node in enumerate(ast_tree.body):
                if isinstance(node, ast.FunctionDef) and node.name == proposal.target_element:
                    del ast_tree.body[i]
                    return True
            
            self.logger.error(f"Function {proposal.target_element} not found")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete function from AST: {e}")
            return False
    
    async def _add_class_to_ast(self, ast_tree: ast.Module, proposal: ModificationProposal) -> bool:
        """Add a class to the AST."""
        try:
            # Parse the new class
            new_class_ast = ast.parse(proposal.proposed_code)
            
            if not new_class_ast.body or not isinstance(new_class_ast.body[0], ast.ClassDef):
                self.logger.error("Proposed code is not a valid class")
                return False
            
            new_class = new_class_ast.body[0]
            
            # Add to the module
            ast_tree.body.append(new_class)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add class to AST: {e}")
            return False
    
    async def _add_import_to_ast(self, ast_tree: ast.Module, proposal: ModificationProposal) -> bool:
        """Add an import to the AST."""
        try:
            # Parse the import statement
            import_ast = ast.parse(proposal.proposed_code)
            
            if not import_ast.body or not isinstance(import_ast.body[0], (ast.Import, ast.ImportFrom)):
                self.logger.error("Proposed code is not a valid import")
                return False
            
            import_node = import_ast.body[0]
            
            # Add to the beginning of the module (after docstring if present)
            insert_index = 0
            if (ast_tree.body and isinstance(ast_tree.body[0], ast.Expr) and 
                isinstance(ast_tree.body[0].value, ast.Constant) and 
                isinstance(ast_tree.body[0].value.value, str)):
                insert_index = 1  # After docstring
            
            ast_tree.body.insert(insert_index, import_node)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add import to AST: {e}")
            return False
    
    def _ast_to_code(self, ast_tree: ast.AST) -> str:
        """Convert AST to code (fallback for older Python versions)."""
        # This is a simplified implementation
        # In practice, you might want to use a library like astor
        import inspect
        try:
            return inspect.getsource(ast_tree)
        except:
            return "# Failed to convert AST to code"
    
    async def _create_backup(self, file_path: str) -> str:
        """Create a backup of a file."""
        try:
            if not os.path.exists(file_path):
                return ""
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.basename(file_path)
            backup_filename = f"{filename}.backup.{timestamp}"
            backup_path = os.path.join(self.backup_directory, backup_filename)
            
            shutil.copy2(file_path, backup_path)
            
            self.logger.debug(f"Created backup: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create backup for {file_path}: {e}")
            return ""
    
    async def _rollback_modification(self, modification_id: str) -> bool:
        """Rollback a modification using backup."""
        try:
            # Find the modification record
            record = None
            for mod_record in self.modification_history:
                if mod_record.modification_id == modification_id:
                    record = mod_record
                    break
            
            if not record or not record.backup_path:
                self.logger.error(f"No backup found for modification {modification_id}")
                return False
            
            if not os.path.exists(record.backup_path):
                self.logger.error(f"Backup file not found: {record.backup_path}")
                return False
            
            # Restore from backup
            shutil.copy2(record.backup_path, record.proposal.target_file)
            
            # Update record
            record.status = ModificationStatus.ROLLED_BACK
            record.rollback_info = {
                "rollback_time": datetime.now().isoformat(),
                "backup_used": record.backup_path
            }
            
            # Update statistics
            self.modification_stats["rollbacks_performed"] += 1
            
            log_agent_event(
                self.agent_id,
                "modification_rolled_back",
                {"modification_id": modification_id, "backup_path": record.backup_path}
            )
            
            self.logger.info(f"Rolled back modification {modification_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback modification {modification_id}: {e}")
            return False
    
    def _initialize_code_templates(self) -> Dict[str, CodeTemplate]:
        """Initialize code templates."""
        templates = {}
        
        # Simple function template
        templates["simple_function"] = CodeTemplate(
            template_id="simple_function",
            name="Simple Function",
            description="A simple function template",
            template_code='''def {function_name}({parameters}):
    """
    {docstring}
    """
    {body}
    return {return_value}''',
            parameters=["function_name", "parameters", "docstring", "body", "return_value"],
            risk_level=CodeRiskLevel.SAFE,
            category="function"
        )
        
        # Simple class template
        templates["simple_class"] = CodeTemplate(
            template_id="simple_class",
            name="Simple Class",
            description="A simple class template",
            template_code='''class {class_name}:
    """
    {docstring}
    """
    
    def __init__(self{init_parameters}):
        {init_body}
    
    {methods}''',
            parameters=["class_name", "docstring", "init_parameters", "init_body", "methods"],
            risk_level=CodeRiskLevel.SAFE,
            category="class"
        )
        
        return templates
    
    async def _load_modification_history(self) -> None:
        """Load modification history from storage."""
        # Placeholder for loading from persistent storage
        pass
    
    async def _save_modification_history(self) -> None:
        """Save modification history to storage."""
        # Placeholder for saving to persistent storage
        pass
    
    async def _cleanup_old_backups(self) -> None:
        """Clean up old backup files."""
        try:
            if not os.path.exists(self.backup_directory):
                return
            
            # Get all backup files
            backup_files = []
            for filename in os.listdir(self.backup_directory):
                if filename.endswith('.backup'):
                    file_path = os.path.join(self.backup_directory, filename)
                    backup_files.append((file_path, os.path.getmtime(file_path)))
            
            # Sort by modification time (oldest first)
            backup_files.sort(key=lambda x: x[1])
            
            # Remove excess backups
            while len(backup_files) > self.max_backups:
                file_path, _ = backup_files.pop(0)
                os.remove(file_path)
                self.logger.debug(f"Removed old backup: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")