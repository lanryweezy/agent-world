"""
AST-based code analysis system for autonomous AI agents.

This module implements safe code analysis using Python's Abstract Syntax Tree (AST)
to understand code structure, detect capabilities, and enable safe code modifications.
"""

import ast
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class CodeRiskLevel(Enum):
    """Risk levels for code modifications."""
    SAFE = "safe"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    DANGEROUS = "dangerous"


class CodeCapability(Enum):
    """Types of code capabilities that can be detected."""
    FILE_IO = "file_io"
    NETWORK_ACCESS = "network_access"
    SYSTEM_CALLS = "system_calls"
    SUBPROCESS = "subprocess"
    IMPORT_MODULES = "import_modules"
    DYNAMIC_EXECUTION = "dynamic_execution"
    REFLECTION = "reflection"
    MEMORY_MANIPULATION = "memory_manipulation"
    THREADING = "threading"
    ASYNC_OPERATIONS = "async_operations"
    DATABASE_ACCESS = "database_access"
    CRYPTOGRAPHY = "cryptography"


@dataclass
class CodeElement:
    """Represents a code element found during analysis."""
    element_type: str  # function, class, variable, import, etc.
    name: str
    line_number: int
    column_offset: int
    source_code: str
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    arguments: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    complexity_score: float = 0.0
    risk_level: CodeRiskLevel = CodeRiskLevel.SAFE
    capabilities: Set[CodeCapability] = field(default_factory=set)


@dataclass
class CodeAnalysisResult:
    """Result of code analysis."""
    file_path: str
    total_lines: int
    total_functions: int
    total_classes: int
    imports: List[str]
    elements: List[CodeElement]
    capabilities: Set[CodeCapability]
    overall_risk_level: CodeRiskLevel
    complexity_score: float
    security_issues: List[str]
    recommendations: List[str]
    ast_tree: Optional[ast.AST] = None


@dataclass
class ModificationProposal:
    """Represents a proposed code modification."""
    proposal_id: str
    target_file: str
    modification_type: str  # add, modify, delete, replace
    target_element: str  # function name, class name, etc.
    original_code: str
    proposed_code: str
    justification: str
    risk_assessment: CodeRiskLevel
    estimated_impact: Dict[str, float]
    dependencies: List[str] = field(default_factory=list)
    test_requirements: List[str] = field(default_factory=list)


class CodeAnalyzer(AgentModule):
    """
    AST-based code analyzer that can parse, analyze, and understand
    Python code structure for safe modification capabilities.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "code_analyzer")
        
        # Analysis cache
        self.analysis_cache: Dict[str, CodeAnalysisResult] = {}
        self.cache_max_size = 100
        
        # Risk assessment rules
        self.risk_patterns = self._initialize_risk_patterns()
        self.capability_patterns = self._initialize_capability_patterns()
        
        # Allowed and forbidden operations
        self.allowed_modules = {
            'math', 'random', 'datetime', 'json', 'typing', 'dataclasses',
            'enum', 'collections', 'itertools', 'functools', 'operator',
            'copy', 'uuid', 'hashlib', 'base64', 'urllib.parse'
        }
        
        self.forbidden_modules = {
            'os', 'sys', 'subprocess', 'shutil', 'glob', 'tempfile',
            'socket', 'urllib.request', 'http', 'ftplib', 'smtplib',
            'eval', 'exec', 'compile', '__import__', 'importlib',
            'ctypes', 'multiprocessing', 'threading'
        }
        
        # Analysis statistics
        self.analysis_stats = {
            "total_analyses": 0,
            "files_analyzed": 0,
            "security_issues_found": 0,
            "high_risk_modifications_blocked": 0,
            "safe_modifications_approved": 0
        }
        
        self.logger.info(f"Code analyzer initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the code analyzer."""
        try:
            # Load any existing analysis cache
            await self._load_analysis_cache()
            
            self.logger.info("Code analyzer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize code analyzer: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the code analyzer gracefully."""
        try:
            # Save analysis cache
            await self._save_analysis_cache()
            
            self.logger.info("Code analyzer shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during code analyzer shutdown: {e}")
    
    async def analyze_file(self, file_path: str, use_cache: bool = True) -> CodeAnalysisResult:
        """
        Analyze a Python file using AST.
        
        Args:
            file_path: Path to the Python file to analyze
            use_cache: Whether to use cached results if available
            
        Returns:
            CodeAnalysisResult with detailed analysis
        """
        try:
            # Check cache first
            if use_cache and file_path in self.analysis_cache:
                self.logger.debug(f"Using cached analysis for {file_path}")
                return self.analysis_cache[file_path]
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Parse AST
            try:
                ast_tree = ast.parse(source_code, filename=file_path)
            except SyntaxError as e:
                self.logger.error(f"Syntax error in {file_path}: {e}")
                raise ValueError(f"Invalid Python syntax in {file_path}: {e}")
            
            # Analyze the AST
            result = await self._analyze_ast(file_path, source_code, ast_tree)
            
            # Cache the result
            self._cache_analysis_result(file_path, result)
            
            # Update statistics
            self.analysis_stats["total_analyses"] += 1
            self.analysis_stats["files_analyzed"] += 1
            self.analysis_stats["security_issues_found"] += len(result.security_issues)
            
            log_agent_event(
                self.agent_id,
                "code_analyzed",
                {
                    "file_path": file_path,
                    "total_lines": result.total_lines,
                    "risk_level": result.overall_risk_level.value,
                    "capabilities": [cap.value for cap in result.capabilities],
                    "security_issues": len(result.security_issues)
                }
            )
            
            self.logger.info(f"Analyzed {file_path}: {result.total_lines} lines, risk: {result.overall_risk_level.value}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze file {file_path}: {e}")
            raise
    
    async def analyze_code_string(self, code: str, filename: str = "<string>") -> CodeAnalysisResult:
        """
        Analyze a code string using AST.
        
        Args:
            code: Python code string to analyze
            filename: Optional filename for error reporting
            
        Returns:
            CodeAnalysisResult with detailed analysis
        """
        try:
            # Parse AST
            try:
                ast_tree = ast.parse(code, filename=filename)
            except SyntaxError as e:
                self.logger.error(f"Syntax error in code string: {e}")
                raise ValueError(f"Invalid Python syntax: {e}")
            
            # Analyze the AST
            result = await self._analyze_ast(filename, code, ast_tree)
            
            # Update statistics
            self.analysis_stats["total_analyses"] += 1
            
            self.logger.debug(f"Analyzed code string: {result.total_lines} lines, risk: {result.overall_risk_level.value}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze code string: {e}")
            raise
    
    async def assess_modification_risk(self, proposal: ModificationProposal) -> Dict[str, Any]:
        """
        Assess the risk of a proposed code modification.
        
        Args:
            proposal: ModificationProposal to assess
            
        Returns:
            Risk assessment with recommendations
        """
        try:
            # Analyze the proposed code
            proposed_analysis = await self.analyze_code_string(
                proposal.proposed_code, 
                f"<proposal:{proposal.proposal_id}>"
            )
            
            # Analyze the original code if available
            original_analysis = None
            if proposal.original_code:
                original_analysis = await self.analyze_code_string(
                    proposal.original_code,
                    f"<original:{proposal.proposal_id}>"
                )
            
            # Calculate risk factors
            risk_factors = self._calculate_risk_factors(
                proposed_analysis, original_analysis, proposal
            )
            
            # Generate recommendations
            recommendations = self._generate_modification_recommendations(
                proposed_analysis, risk_factors
            )
            
            # Determine if modification should be allowed
            should_allow = self._should_allow_modification(risk_factors, proposed_analysis)
            
            assessment = {
                "proposal_id": proposal.proposal_id,
                "risk_level": proposed_analysis.overall_risk_level.value,
                "should_allow": should_allow,
                "risk_factors": risk_factors,
                "security_issues": proposed_analysis.security_issues,
                "capabilities_added": list(proposed_analysis.capabilities),
                "recommendations": recommendations,
                "complexity_change": self._calculate_complexity_change(
                    original_analysis, proposed_analysis
                )
            }
            
            # Update statistics
            if should_allow:
                self.analysis_stats["safe_modifications_approved"] += 1
            else:
                self.analysis_stats["high_risk_modifications_blocked"] += 1
            
            log_agent_event(
                self.agent_id,
                "modification_assessed",
                {
                    "proposal_id": proposal.proposal_id,
                    "risk_level": proposed_analysis.overall_risk_level.value,
                    "allowed": should_allow,
                    "security_issues": len(proposed_analysis.security_issues)
                }
            )
            
            self.logger.info(f"Assessed modification {proposal.proposal_id}: risk={proposed_analysis.overall_risk_level.value}, allowed={should_allow}")
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Failed to assess modification risk: {e}")
            raise
    
    async def extract_functions(self, file_path: str) -> List[CodeElement]:
        """Extract all functions from a Python file."""
        try:
            analysis = await self.analyze_file(file_path)
            return [elem for elem in analysis.elements if elem.element_type == "function"]
        except Exception as e:
            self.logger.error(f"Failed to extract functions from {file_path}: {e}")
            return []
    
    async def extract_classes(self, file_path: str) -> List[CodeElement]:
        """Extract all classes from a Python file."""
        try:
            analysis = await self.analyze_file(file_path)
            return [elem for elem in analysis.elements if elem.element_type == "class"]
        except Exception as e:
            self.logger.error(f"Failed to extract classes from {file_path}: {e}")
            return []
    
    async def find_security_vulnerabilities(self, file_path: str) -> List[str]:
        """Find potential security vulnerabilities in a file."""
        try:
            analysis = await self.analyze_file(file_path)
            return analysis.security_issues
        except Exception as e:
            self.logger.error(f"Failed to find vulnerabilities in {file_path}: {e}")
            return []
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get code analysis statistics."""
        return {
            **self.analysis_stats,
            "cache_size": len(self.analysis_cache),
            "allowed_modules": len(self.allowed_modules),
            "forbidden_modules": len(self.forbidden_modules)
        }
    
    # Private helper methods
    
    async def _analyze_ast(self, file_path: str, source_code: str, ast_tree: ast.AST) -> CodeAnalysisResult:
        """Analyze an AST tree and extract information."""
        try:
            # Initialize analysis visitor
            visitor = CodeAnalysisVisitor(self.risk_patterns, self.capability_patterns)
            visitor.visit(ast_tree)
            
            # Calculate metrics
            total_lines = len(source_code.splitlines())
            complexity_score = self._calculate_complexity_score(visitor.elements)
            overall_risk = self._determine_overall_risk(visitor.elements, visitor.security_issues)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(visitor.elements, visitor.security_issues)
            
            return CodeAnalysisResult(
                file_path=file_path,
                total_lines=total_lines,
                total_functions=len([e for e in visitor.elements if e.element_type == "function"]),
                total_classes=len([e for e in visitor.elements if e.element_type == "class"]),
                imports=visitor.imports,
                elements=visitor.elements,
                capabilities=visitor.capabilities,
                overall_risk_level=overall_risk,
                complexity_score=complexity_score,
                security_issues=visitor.security_issues,
                recommendations=recommendations,
                ast_tree=ast_tree
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze AST: {e}")
            raise
    
    def _initialize_risk_patterns(self) -> Dict[str, CodeRiskLevel]:
        """Initialize patterns for risk assessment."""
        return {
            # High-risk patterns
            'eval': CodeRiskLevel.DANGEROUS,
            'exec': CodeRiskLevel.DANGEROUS,
            'compile': CodeRiskLevel.DANGEROUS,
            '__import__': CodeRiskLevel.DANGEROUS,
            'getattr': CodeRiskLevel.HIGH_RISK,
            'setattr': CodeRiskLevel.HIGH_RISK,
            'delattr': CodeRiskLevel.HIGH_RISK,
            'globals': CodeRiskLevel.HIGH_RISK,
            'locals': CodeRiskLevel.HIGH_RISK,
            'vars': CodeRiskLevel.HIGH_RISK,
            
            # Medium-risk patterns
            'open': CodeRiskLevel.MEDIUM_RISK,
            'file': CodeRiskLevel.MEDIUM_RISK,
            'input': CodeRiskLevel.MEDIUM_RISK,
            'raw_input': CodeRiskLevel.MEDIUM_RISK,
            
            # Low-risk patterns
            'print': CodeRiskLevel.LOW_RISK,
            'len': CodeRiskLevel.SAFE,
            'str': CodeRiskLevel.SAFE,
            'int': CodeRiskLevel.SAFE,
            'float': CodeRiskLevel.SAFE,
        }
    
    def _initialize_capability_patterns(self) -> Dict[str, Set[CodeCapability]]:
        """Initialize patterns for capability detection."""
        return {
            'open': {CodeCapability.FILE_IO},
            'file': {CodeCapability.FILE_IO},
            'socket': {CodeCapability.NETWORK_ACCESS},
            'urllib': {CodeCapability.NETWORK_ACCESS},
            'http': {CodeCapability.NETWORK_ACCESS},
            'requests': {CodeCapability.NETWORK_ACCESS},
            'os': {CodeCapability.SYSTEM_CALLS},
            'sys': {CodeCapability.SYSTEM_CALLS},
            'subprocess': {CodeCapability.SUBPROCESS},
            'eval': {CodeCapability.DYNAMIC_EXECUTION},
            'exec': {CodeCapability.DYNAMIC_EXECUTION},
            'compile': {CodeCapability.DYNAMIC_EXECUTION},
            'getattr': {CodeCapability.REFLECTION},
            'setattr': {CodeCapability.REFLECTION},
            'hasattr': {CodeCapability.REFLECTION},
            'threading': {CodeCapability.THREADING},
            'multiprocessing': {CodeCapability.THREADING},
            'asyncio': {CodeCapability.ASYNC_OPERATIONS},
            'sqlite3': {CodeCapability.DATABASE_ACCESS},
            'mysql': {CodeCapability.DATABASE_ACCESS},
            'postgresql': {CodeCapability.DATABASE_ACCESS},
            'cryptography': {CodeCapability.CRYPTOGRAPHY},
            'hashlib': {CodeCapability.CRYPTOGRAPHY},
        }
    
    def _calculate_complexity_score(self, elements: List[CodeElement]) -> float:
        """Calculate overall complexity score."""
        if not elements:
            return 0.0
        
        total_complexity = sum(elem.complexity_score for elem in elements)
        return total_complexity / len(elements)
    
    def _determine_overall_risk(self, elements: List[CodeElement], security_issues: List[str]) -> CodeRiskLevel:
        """Determine overall risk level."""
        if security_issues:
            return CodeRiskLevel.HIGH_RISK
        
        if not elements:
            return CodeRiskLevel.SAFE
        
        max_risk = max(elem.risk_level for elem in elements)
        return max_risk
    
    def _generate_recommendations(self, elements: List[CodeElement], security_issues: List[str]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if security_issues:
            recommendations.append("Address security issues before deployment")
        
        high_risk_elements = [e for e in elements if e.risk_level in [CodeRiskLevel.HIGH_RISK, CodeRiskLevel.DANGEROUS]]
        if high_risk_elements:
            recommendations.append("Review high-risk code elements for safety")
        
        complex_elements = [e for e in elements if e.complexity_score > 10]
        if complex_elements:
            recommendations.append("Consider refactoring complex functions")
        
        return recommendations
    
    def _calculate_risk_factors(
        self, 
        proposed_analysis: CodeAnalysisResult, 
        original_analysis: Optional[CodeAnalysisResult],
        proposal: ModificationProposal
    ) -> Dict[str, float]:
        """Calculate various risk factors for a modification."""
        risk_factors = {
            "complexity_increase": 0.0,
            "capability_expansion": 0.0,
            "security_degradation": 0.0,
            "dependency_risk": 0.0,
            "modification_scope": 0.0
        }
        
        # Complexity risk
        if original_analysis:
            complexity_change = proposed_analysis.complexity_score - original_analysis.complexity_score
            risk_factors["complexity_increase"] = max(0.0, complexity_change / 10.0)
        
        # Capability expansion risk
        new_capabilities = len(proposed_analysis.capabilities)
        if original_analysis:
            new_capabilities = len(proposed_analysis.capabilities - original_analysis.capabilities)
        risk_factors["capability_expansion"] = min(1.0, new_capabilities / 5.0)
        
        # Security risk
        risk_factors["security_degradation"] = min(1.0, len(proposed_analysis.security_issues) / 3.0)
        
        # Dependency risk
        risk_factors["dependency_risk"] = min(1.0, len(proposal.dependencies) / 10.0)
        
        # Modification scope risk
        scope_multiplier = {
            "add": 0.3,
            "modify": 0.5,
            "delete": 0.7,
            "replace": 0.8
        }
        risk_factors["modification_scope"] = scope_multiplier.get(proposal.modification_type, 0.5)
        
        return risk_factors
    
    def _generate_modification_recommendations(
        self, 
        analysis: CodeAnalysisResult, 
        risk_factors: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations for a modification."""
        recommendations = []
        
        if analysis.overall_risk_level in [CodeRiskLevel.HIGH_RISK, CodeRiskLevel.DANGEROUS]:
            recommendations.append("High-risk modification - requires careful review")
        
        if risk_factors["complexity_increase"] > 0.5:
            recommendations.append("Significant complexity increase - consider simplification")
        
        if risk_factors["capability_expansion"] > 0.3:
            recommendations.append("New capabilities added - verify necessity and safety")
        
        if analysis.security_issues:
            recommendations.append("Security issues detected - must be resolved before approval")
        
        return recommendations
    
    def _should_allow_modification(
        self, 
        risk_factors: Dict[str, float], 
        analysis: CodeAnalysisResult
    ) -> bool:
        """Determine if a modification should be allowed."""
        # Block dangerous modifications
        if analysis.overall_risk_level == CodeRiskLevel.DANGEROUS:
            return False
        
        # Block if security issues exist
        if analysis.security_issues:
            return False
        
        # Calculate overall risk score
        overall_risk = sum(risk_factors.values()) / len(risk_factors)
        
        # Allow if overall risk is acceptable
        return overall_risk < 0.7
    
    def _calculate_complexity_change(
        self, 
        original: Optional[CodeAnalysisResult], 
        proposed: CodeAnalysisResult
    ) -> float:
        """Calculate complexity change between original and proposed code."""
        if not original:
            return proposed.complexity_score
        
        return proposed.complexity_score - original.complexity_score
    
    def _cache_analysis_result(self, file_path: str, result: CodeAnalysisResult) -> None:
        """Cache an analysis result."""
        if len(self.analysis_cache) >= self.cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.analysis_cache))
            del self.analysis_cache[oldest_key]
        
        self.analysis_cache[file_path] = result
    
    async def _load_analysis_cache(self) -> None:
        """Load analysis cache from storage."""
        # Placeholder for loading cache from persistent storage
        pass
    
    async def _save_analysis_cache(self) -> None:
        """Save analysis cache to storage."""
        # Placeholder for saving cache to persistent storage
        pass


class CodeAnalysisVisitor(ast.NodeVisitor):
    """AST visitor for code analysis."""
    
    def __init__(self, risk_patterns: Dict[str, CodeRiskLevel], capability_patterns: Dict[str, Set[CodeCapability]]):
        self.risk_patterns = risk_patterns
        self.capability_patterns = capability_patterns
        
        # Analysis results
        self.elements: List[CodeElement] = []
        self.imports: List[str] = []
        self.capabilities: Set[CodeCapability] = set()
        self.security_issues: List[str] = []
        
        # Tracking state
        self.current_class = None
        self.current_function = None
        self.nesting_level = 0
    
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        for alias in node.names:
            module_name = alias.name
            self.imports.append(module_name)
            
            # Check for capabilities
            if module_name in self.capability_patterns:
                self.capabilities.update(self.capability_patterns[module_name])
            
            # Check for security issues
            if any(forbidden in module_name for forbidden in ['os', 'sys', 'subprocess']):
                self.security_issues.append(f"Potentially dangerous import: {module_name}")
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-import statements."""
        if node.module:
            self.imports.append(node.module)
            
            # Check for capabilities
            if node.module in self.capability_patterns:
                self.capabilities.update(self.capability_patterns[node.module])
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        self.current_function = node.name
        self.nesting_level += 1
        
        # Extract function information
        element = CodeElement(
            element_type="function",
            name=node.name,
            line_number=node.lineno,
            column_offset=node.col_offset,
            source_code=ast.unparse(node) if hasattr(ast, 'unparse') else "",
            docstring=ast.get_docstring(node),
            decorators=[ast.unparse(dec) if hasattr(ast, 'unparse') else str(dec) for dec in node.decorator_list],
            arguments=[arg.arg for arg in node.args.args],
            complexity_score=self._calculate_function_complexity(node)
        )
        
        # Assess risk level
        element.risk_level = self._assess_element_risk(node)
        
        self.elements.append(element)
        
        # Continue visiting
        self.generic_visit(node)
        
        self.nesting_level -= 1
        self.current_function = None
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        self.current_class = node.name
        self.nesting_level += 1
        
        # Extract class information
        element = CodeElement(
            element_type="class",
            name=node.name,
            line_number=node.lineno,
            column_offset=node.col_offset,
            source_code=ast.unparse(node) if hasattr(ast, 'unparse') else "",
            docstring=ast.get_docstring(node),
            decorators=[ast.unparse(dec) if hasattr(ast, 'unparse') else str(dec) for dec in node.decorator_list],
            complexity_score=self._calculate_class_complexity(node)
        )
        
        # Assess risk level
        element.risk_level = self._assess_element_risk(node)
        
        self.elements.append(element)
        
        # Continue visiting
        self.generic_visit(node)
        
        self.nesting_level -= 1
        self.current_class = None
    
    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls."""
        # Extract function name
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        
        if func_name:
            # Check for risky function calls
            if func_name in self.risk_patterns:
                risk_level = self.risk_patterns[func_name]
                if risk_level in [CodeRiskLevel.HIGH_RISK, CodeRiskLevel.DANGEROUS]:
                    self.security_issues.append(f"Risky function call: {func_name}")
            
            # Check for capabilities
            if func_name in self.capability_patterns:
                self.capabilities.update(self.capability_patterns[func_name])
        
        self.generic_visit(node)
    
    def _calculate_function_complexity(self, node: ast.FunctionDef) -> float:
        """Calculate complexity score for a function."""
        complexity = 1  # Base complexity
        
        # Count control flow statements
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        # Add penalty for nesting
        complexity += self.nesting_level * 0.5
        
        # Add penalty for number of arguments
        complexity += len(node.args.args) * 0.1
        
        return complexity
    
    def _calculate_class_complexity(self, node: ast.ClassDef) -> float:
        """Calculate complexity score for a class."""
        complexity = 1  # Base complexity
        
        # Count methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        complexity += len(methods) * 0.5
        
        # Count inheritance
        complexity += len(node.bases) * 0.3
        
        return complexity
    
    def _assess_element_risk(self, node: ast.AST) -> CodeRiskLevel:
        """Assess risk level for a code element."""
        risk_level = CodeRiskLevel.SAFE
        
        # Check for risky patterns in the element
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                func_name = child.func.id
                if func_name in self.risk_patterns:
                    element_risk = self.risk_patterns[func_name]
                    if element_risk.value > risk_level.value:
                        risk_level = element_risk
        
        return risk_level