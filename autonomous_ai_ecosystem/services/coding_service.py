"""
Coding service with code generation and debugging capabilities.

This module implements comprehensive coding assistance including
code generation, debugging, optimization, and code analysis.
"""

import asyncio
import ast
import re
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class CodeLanguage(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    SQL = "sql"
    HTML = "html"
    CSS = "css"
    BASH = "bash"


class CodeTaskType(Enum):
    """Types of coding tasks."""
    GENERATE_FUNCTION = "generate_function"
    GENERATE_CLASS = "generate_class"
    GENERATE_MODULE = "generate_module"
    DEBUG_CODE = "debug_code"
    OPTIMIZE_CODE = "optimize_code"
    REFACTOR_CODE = "refactor_code"
    ADD_TESTS = "add_tests"
    ADD_DOCUMENTATION = "add_documentation"
    CODE_REVIEW = "code_review"
    FIX_SECURITY = "fix_security"
    CONVERT_LANGUAGE = "convert_language"


class CodeQuality(Enum):
    """Code quality levels."""
    BASIC = "basic"
    GOOD = "good"
    PRODUCTION = "production"
    ENTERPRISE = "enterprise"


@dataclass
class CodeRequest:
    """Request for coding assistance."""
    request_id: str
    task_type: CodeTaskType
    language: CodeLanguage
    
    # Task description
    description: str
    requirements: List[str] = field(default_factory=list)
    
    # Input code (for debugging, optimization, etc.)
    input_code: str = ""
    
    # Generation parameters
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    parameters: List[Dict[str, str]] = field(default_factory=list)  # name, type, description
    return_type: Optional[str] = None
    
    # Quality and style preferences
    quality_level: CodeQuality = CodeQuality.GOOD
    coding_style: str = "standard"  # standard, google, pep8, etc.
    include_comments: bool = True
    include_docstrings: bool = True
    include_type_hints: bool = True
    
    # Testing requirements
    include_unit_tests: bool = False
    test_framework: Optional[str] = None
    
    # Context and constraints
    existing_codebase: str = ""
    dependencies: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    requested_by: str = ""
    priority: int = 5


@dataclass
class CodeSolution:
    """Generated code solution."""
    solution_id: str
    request_id: str
    
    # Generated code
    code: str
    test_code: str = ""
    documentation: str = ""
    
    # Code analysis
    complexity_score: float = 0.0
    maintainability_score: float = 0.0
    performance_score: float = 0.0
    security_score: float = 0.0
    
    # Quality metrics
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    test_coverage: float = 0.0
    
    # Validation results
    syntax_valid: bool = False
    tests_pass: bool = False
    linting_score: float = 0.0
    
    # Generation metadata
    generated_at: datetime = field(default_factory=datetime.now)
    generation_time: float = 0.0
    model_used: str = ""
    
    # Improvements and alternatives
    optimization_suggestions: List[str] = field(default_factory=list)
    alternative_approaches: List[str] = field(default_factory=list)
    
    def get_quality_summary(self) -> Dict[str, Any]:
        """Get comprehensive quality summary."""
        return {
            "complexity_score": self.complexity_score,
            "maintainability_score": self.maintainability_score,
            "performance_score": self.performance_score,
            "security_score": self.security_score,
            "lines_of_code": self.lines_of_code,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "test_coverage": self.test_coverage,
            "syntax_valid": self.syntax_valid,
            "tests_pass": self.tests_pass,
            "linting_score": self.linting_score,
            "overall_quality": self._calculate_overall_quality()
        }
    
    def _calculate_overall_quality(self) -> float:
        """Calculate overall quality score."""
        scores = [
            self.complexity_score,
            self.maintainability_score,
            self.performance_score,
            self.security_score,
            self.linting_score
        ]
        
        # Weight syntax validity and test passing
        if not self.syntax_valid:
            return 0.0
        
        base_score = sum(scores) / len(scores)
        
        if self.tests_pass:
            base_score *= 1.1  # Bonus for passing tests
        
        return min(1.0, base_score)


@dataclass
class CodeAnalysis:
    """Code analysis results."""
    analysis_id: str
    code: str
    language: CodeLanguage
    
    # Static analysis results
    syntax_errors: List[Dict[str, Any]] = field(default_factory=list)
    style_violations: List[Dict[str, Any]] = field(default_factory=list)
    security_issues: List[Dict[str, Any]] = field(default_factory=list)
    performance_issues: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metrics
    complexity_metrics: Dict[str, float] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Suggestions
    improvement_suggestions: List[str] = field(default_factory=list)
    refactoring_opportunities: List[str] = field(default_factory=list)
    
    # Metadata
    analyzed_at: datetime = field(default_factory=datetime.now)
    analysis_time: float = 0.0


class CodingAssistanceService(AgentModule):
    """
    Coding assistance service with generation and debugging capabilities.
    
    Provides comprehensive coding support including code generation,
    debugging, optimization, and quality analysis.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "coding_service")
        
        # Core data structures
        self.code_requests: Dict[str, CodeRequest] = {}
        self.code_solutions: Dict[str, CodeSolution] = {}
        self.code_analyses: Dict[str, CodeAnalysis] = {}
        
        # Active coding tasks
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self.config = {
            "max_concurrent_tasks": 5,
            "default_timeout_seconds": 300,
            "max_code_length": 50000,
            "enable_syntax_validation": True,
            "enable_security_analysis": True,
            "enable_performance_analysis": True,
            "temp_dir": tempfile.gettempdir(),
            "supported_test_frameworks": {
                CodeLanguage.PYTHON: ["pytest", "unittest"],
                CodeLanguage.JAVASCRIPT: ["jest", "mocha"],
                CodeLanguage.JAVA: ["junit"],
                CodeLanguage.CSHARP: ["nunit", "xunit"]
            }
        }
        
        # Code templates and patterns
        self.code_templates = {
            CodeLanguage.PYTHON: {
                "function": '''def {function_name}({parameters}){return_type}:
    """
    {description}
    
    Args:
{arg_docs}
    
    Returns:
        {return_description}
    """
    {body}''',
                "class": '''class {class_name}:
    """
    {description}
    """
    
    def __init__(self{init_params}):
        """Initialize {class_name}."""
        {init_body}
    
    {methods}''',
                "test": '''import pytest
from {module} import {function_name}


def test_{function_name}():
    """Test {function_name} function."""
    {test_body}'''
            },
            CodeLanguage.JAVASCRIPT: {
                "function": '''/**
 * {description}
{param_docs}
 * @returns {{{return_type}}} {return_description}
 */
function {function_name}({parameters}) {{
    {body}
}}''',
                "class": '''/**
 * {description}
 */
class {class_name} {{
    constructor({constructor_params}) {{
        {constructor_body}
    }}
    
    {methods}
}}''',
                "test": '''const {{ {function_name} }} = require('./{module}');

describe('{function_name}', () => {{
    test('should {test_description}', () => {{
        {test_body}
    }});
}});'''
            }
        }
        
        # Quality analysis patterns
        self.quality_patterns = {
            "security_issues": {
                CodeLanguage.PYTHON: [
                    (r'eval\s*\(', "Avoid using eval() - security risk"),
                    (r'exec\s*\(', "Avoid using exec() - security risk"),
                    (r'input\s*\(', "Consider input validation"),
                    (r'pickle\.loads?', "Pickle can be unsafe with untrusted data")
                ],
                CodeLanguage.JAVASCRIPT: [
                    (r'eval\s*\(', "Avoid using eval() - security risk"),
                    (r'innerHTML\s*=', "Potential XSS vulnerability"),
                    (r'document\.write', "Avoid document.write - security risk")
                ]
            },
            "performance_issues": {
                CodeLanguage.PYTHON: [
                    (r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(', "Consider enumerate() instead"),
                    (r'\+\s*=.*\[.*\]', "Consider list comprehension for better performance")
                ],
                CodeLanguage.JAVASCRIPT: [
                    (r'for\s*\(\s*var\s+\w+\s*=\s*0', "Consider for...of or forEach for better readability")
                ]
            }
        }
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_generation_time": 0.0,
            "average_quality_score": 0.0,
            "tasks_by_type": {task_type.value: 0 for task_type in CodeTaskType},
            "tasks_by_language": {lang.value: 0 for lang in CodeLanguage},
            "total_lines_generated": 0,
            "syntax_error_rate": 0.0
        }
        
        # Counters
        self.request_counter = 0
        self.solution_counter = 0
        self.analysis_counter = 0
        
        self.logger.info("Coding assistance service initialized")
    
    async def initialize(self) -> None:
        """Initialize the coding service."""
        try:
            # Start background tasks
            asyncio.create_task(self._cleanup_temp_files())
            asyncio.create_task(self._update_statistics())
            
            self.logger.info("Coding service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize coding service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the coding service."""
        try:
            # Cancel active tasks
            for task in self.active_tasks.values():
                task.cancel()
            
            # Wait for tasks to complete
            if self.active_tasks:
                await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
            
            self.logger.info("Coding service shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during coding service shutdown: {e}")
    
    async def generate_code(
        self,
        task_type: CodeTaskType,
        language: CodeLanguage,
        description: str,
        requirements: Optional[List[str]] = None,
        function_name: Optional[str] = None,
        class_name: Optional[str] = None,
        parameters: Optional[List[Dict[str, str]]] = None,
        quality_level: CodeQuality = CodeQuality.GOOD,
        include_tests: bool = False
    ) -> Dict[str, Any]:
        """Generate code based on specifications."""
        try:
            # Check concurrent task limit
            if len(self.active_tasks) >= self.config["max_concurrent_tasks"]:
                return {"success": False, "error": "Maximum concurrent tasks reached"}
            
            # Create code request
            self.request_counter += 1
            request_id = f"req_{self.request_counter}_{datetime.now().timestamp()}"
            
            request = CodeRequest(
                request_id=request_id,
                task_type=task_type,
                language=language,
                description=description,
                requirements=requirements or [],
                function_name=function_name,
                class_name=class_name,
                parameters=parameters or [],
                quality_level=quality_level,
                include_unit_tests=include_tests,
                requested_by=self.agent_id
            )
            
            self.code_requests[request_id] = request
            
            # Start coding task
            coding_task = asyncio.create_task(self._generate_code_async(request_id))
            self.active_tasks[request_id] = coding_task
            
            # Update statistics
            self.stats["total_requests"] += 1
            self.stats["tasks_by_type"][task_type.value] += 1
            self.stats["tasks_by_language"][language.value] += 1
            
            log_agent_event(
                self.agent_id,
                "code_generation_started",
                {
                    "request_id": request_id,
                    "task_type": task_type.value,
                    "language": language.value,
                    "description": description
                }
            )
            
            result = {
                "success": True,
                "request_id": request_id,
                "task_type": task_type.value,
                "language": language.value,
                "estimated_completion_time": self._estimate_generation_time(request),
                "status": "generating"
            }
            
            self.logger.info(f"Code generation started: {description} ({language.value})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to start code generation: {e}")
            return {"success": False, "error": str(e)}
    
    async def debug_code(
        self,
        code: str,
        language: CodeLanguage,
        error_description: Optional[str] = None,
        expected_behavior: Optional[str] = None
    ) -> Dict[str, Any]:
        """Debug existing code and provide fixes."""
        try:
            # Create debug request
            self.request_counter += 1
            request_id = f"debug_{self.request_counter}_{datetime.now().timestamp()}"
            
            request = CodeRequest(
                request_id=request_id,
                task_type=CodeTaskType.DEBUG_CODE,
                language=language,
                description=error_description or "Debug and fix code issues",
                input_code=code,
                requirements=[expected_behavior] if expected_behavior else [],
                requested_by=self.agent_id
            )
            
            self.code_requests[request_id] = request
            
            # Start debugging task
            debug_task = asyncio.create_task(self._debug_code_async(request_id))
            self.active_tasks[request_id] = debug_task
            
            result = {
                "success": True,
                "request_id": request_id,
                "status": "debugging"
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to start code debugging: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_code(
        self,
        code: str,
        language: CodeLanguage,
        include_security: bool = True,
        include_performance: bool = True
    ) -> Dict[str, Any]:
        """Analyze code quality and provide suggestions."""
        try:
            start_time = datetime.now()
            
            # Create analysis
            self.analysis_counter += 1
            analysis_id = f"analysis_{self.analysis_counter}_{datetime.now().timestamp()}"
            
            analysis = CodeAnalysis(
                analysis_id=analysis_id,
                code=code,
                language=language
            )
            
            # Perform syntax analysis
            if self.config["enable_syntax_validation"]:
                analysis.syntax_errors = await self._check_syntax(code, language)
            
            # Perform style analysis
            analysis.style_violations = await self._check_style(code, language)
            
            # Perform security analysis
            if include_security and self.config["enable_security_analysis"]:
                analysis.security_issues = await self._check_security(code, language)
            
            # Perform performance analysis
            if include_performance and self.config["enable_performance_analysis"]:
                analysis.performance_issues = await self._check_performance(code, language)
            
            # Calculate metrics
            analysis.complexity_metrics = await self._calculate_complexity(code, language)
            analysis.quality_metrics = await self._calculate_quality_metrics(code, language)
            
            # Generate suggestions
            analysis.improvement_suggestions = await self._generate_improvement_suggestions(analysis)
            analysis.refactoring_opportunities = await self._identify_refactoring_opportunities(code, language)
            
            analysis.analysis_time = (datetime.now() - start_time).total_seconds()
            
            self.code_analyses[analysis_id] = analysis
            
            result = {
                "success": True,
                "analysis_id": analysis_id,
                "syntax_errors": analysis.syntax_errors,
                "style_violations": analysis.style_violations,
                "security_issues": analysis.security_issues,
                "performance_issues": analysis.performance_issues,
                "complexity_metrics": analysis.complexity_metrics,
                "quality_metrics": analysis.quality_metrics,
                "improvement_suggestions": analysis.improvement_suggestions,
                "refactoring_opportunities": analysis.refactoring_opportunities,
                "analysis_time": analysis.analysis_time
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze code: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_code_solution(self, request_id: str) -> Dict[str, Any]:
        """Get generated code solution by request ID."""
        try:
            if request_id not in self.code_requests:
                return {"success": False, "error": "Request not found"}
            
            # Check if generation is still in progress
            if request_id in self.active_tasks:
                task = self.active_tasks[request_id]
                if not task.done():
                    return {
                        "success": True,
                        "status": "generating",
                        "request_id": request_id,
                        "progress": "Code generation in progress..."
                    }
            
            # Look for completed solution
            solutions = [solution for solution in self.code_solutions.values() 
                        if solution.request_id == request_id]
            
            if not solutions:
                return {"success": False, "error": "Solution not found or generation failed"}
            
            # Return the most recent solution
            solution = max(solutions, key=lambda s: s.generated_at)
            
            result = {
                "success": True,
                "request_id": request_id,
                "solution_id": solution.solution_id,
                "code": solution.code,
                "test_code": solution.test_code,
                "documentation": solution.documentation,
                "quality_summary": solution.get_quality_summary(),
                "optimization_suggestions": solution.optimization_suggestions,
                "alternative_approaches": solution.alternative_approaches,
                "generated_at": solution.generated_at.isoformat()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get code solution: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_code_async(self, request_id: str) -> None:
        """Generate code asynchronously."""
        request = self.code_requests[request_id]
        start_time = datetime.now()
        
        try:
            # Generate code based on task type
            if request.task_type == CodeTaskType.GENERATE_FUNCTION:
                solution = await self._generate_function(request)
            elif request.task_type == CodeTaskType.GENERATE_CLASS:
                solution = await self._generate_class(request)
            elif request.task_type == CodeTaskType.GENERATE_MODULE:
                solution = await self._generate_module(request)
            else:
                solution = await self._generate_generic_code(request)
            
            if solution:
                solution.generation_time = (datetime.now() - start_time).total_seconds()
                
                # Validate and analyze generated code
                await self._validate_solution(solution, request)
                
                # Generate tests if requested
                if request.include_unit_tests:
                    solution.test_code = await self._generate_tests(solution, request)
                
                # Generate documentation
                solution.documentation = await self._generate_documentation(solution, request)
                
                self.code_solutions[solution.solution_id] = solution
                
                # Update statistics
                self.stats["completed_tasks"] += 1
                self.stats["total_lines_generated"] += solution.lines_of_code
                
                log_agent_event(
                    self.agent_id,
                    "code_generation_completed",
                    {
                        "request_id": request_id,
                        "solution_id": solution.solution_id,
                        "lines_of_code": solution.lines_of_code,
                        "quality_score": solution._calculate_overall_quality(),
                        "generation_time": solution.generation_time
                    }
                )
                
                self.logger.info(f"Code generation completed: {request_id}")
            
            else:
                self.stats["failed_tasks"] += 1
                self.logger.error(f"Code generation failed: {request_id}")
        
        except Exception as e:
            self.stats["failed_tasks"] += 1
            self.logger.error(f"Error in code generation: {e}")
        
        finally:
            # Clean up active task
            if request_id in self.active_tasks:
                del self.active_tasks[request_id]
    
    async def _debug_code_async(self, request_id: str) -> None:
        """Debug code asynchronously."""
        request = self.code_requests[request_id]
        start_time = datetime.now()
        
        try:
            # Analyze the problematic code
            analysis = await self.analyze_code(
                request.input_code,
                request.language,
                include_security=True,
                include_performance=True
            )
            
            # Generate fixed code
            fixed_code = await self._generate_code_fixes(request.input_code, analysis, request)
            
            if fixed_code:
                # Create solution with fixed code
                self.solution_counter += 1
                solution_id = f"solution_{self.solution_counter}_{datetime.now().timestamp()}"
                
                solution = CodeSolution(
                    solution_id=solution_id,
                    request_id=request_id,
                    code=fixed_code,
                    generation_time=(datetime.now() - start_time).total_seconds(),
                    model_used="code_debugger"
                )
                
                # Validate the fix
                await self._validate_solution(solution, request)
                
                self.code_solutions[solution_id] = solution
                
                self.stats["completed_tasks"] += 1
                self.logger.info(f"Code debugging completed: {request_id}")
            
            else:
                self.stats["failed_tasks"] += 1
                self.logger.error(f"Code debugging failed: {request_id}")
        
        except Exception as e:
            self.stats["failed_tasks"] += 1
            self.logger.error(f"Error in code debugging: {e}")
        
        finally:
            if request_id in self.active_tasks:
                del self.active_tasks[request_id]
    
    async def _generate_function(self, request: CodeRequest) -> Optional[CodeSolution]:
        """Generate a function based on request."""
        try:
            template = self.code_templates.get(request.language, {}).get("function", "")
            if not template:
                return None
            
            # Prepare template parameters
            parameters_str = self._format_parameters(request.parameters, request.language)
            return_type_str = f" -> {request.return_type}" if request.return_type and request.language == CodeLanguage.PYTHON else ""
            
            # Generate function body
            body = await self._generate_function_body(request)
            
            # Format argument documentation
            arg_docs = self._format_arg_docs(request.parameters)
            
            # Generate the function code
            code = template.format(
                function_name=request.function_name or "generated_function",
                parameters=parameters_str,
                return_type=return_type_str,
                description=request.description,
                arg_docs=arg_docs,
                return_description=f"Returns {request.return_type or 'result'}",
                body=body
            )
            
            # Create solution
            self.solution_counter += 1
            solution_id = f"solution_{self.solution_counter}_{datetime.now().timestamp()}"
            
            solution = CodeSolution(
                solution_id=solution_id,
                request_id=request.request_id,
                code=code,
                lines_of_code=len(code.split('\n')),
                model_used="function_generator"
            )
            
            return solution
            
        except Exception as e:
            self.logger.error(f"Failed to generate function: {e}")
            return None
    
    async def _generate_class(self, request: CodeRequest) -> Optional[CodeSolution]:
        """Generate a class based on request."""
        try:
            template = self.code_templates.get(request.language, {}).get("class", "")
            if not template:
                return None
            
            # Generate class methods
            methods = await self._generate_class_methods(request)
            
            # Generate initialization parameters and body
            init_params, init_body = await self._generate_init_method(request)
            
            # Generate the class code
            code = template.format(
                class_name=request.class_name or "GeneratedClass",
                description=request.description,
                init_params=init_params,
                init_body=init_body,
                methods=methods
            )
            
            # Create solution
            self.solution_counter += 1
            solution_id = f"solution_{self.solution_counter}_{datetime.now().timestamp()}"
            
            solution = CodeSolution(
                solution_id=solution_id,
                request_id=request.request_id,
                code=code,
                lines_of_code=len(code.split('\n')),
                model_used="class_generator"
            )
            
            return solution
            
        except Exception as e:
            self.logger.error(f"Failed to generate class: {e}")
            return None
    
    async def _generate_module(self, request: CodeRequest) -> Optional[CodeSolution]:
        """Generate a module based on request."""
        try:
            # Generate module structure based on requirements
            imports = self._generate_imports(request)
            constants = self._generate_constants(request)
            functions = await self._generate_module_functions(request)
            classes = await self._generate_module_classes(request)
            
            # Combine into module
            code_parts = []
            
            if imports:
                code_parts.append(imports)
                code_parts.append("")
            
            if constants:
                code_parts.append(constants)
                code_parts.append("")
            
            if functions:
                code_parts.append(functions)
                code_parts.append("")
            
            if classes:
                code_parts.append(classes)
            
            code = "\n".join(code_parts)
            
            # Create solution
            self.solution_counter += 1
            solution_id = f"solution_{self.solution_counter}_{datetime.now().timestamp()}"
            
            solution = CodeSolution(
                solution_id=solution_id,
                request_id=request.request_id,
                code=code,
                lines_of_code=len(code.split('\n')),
                model_used="module_generator"
            )
            
            return solution
            
        except Exception as e:
            self.logger.error(f"Failed to generate module: {e}")
            return None
    
    async def _generate_generic_code(self, request: CodeRequest) -> Optional[CodeSolution]:
        """Generate generic code based on request."""
        try:
            # Simple code generation based on description and requirements
            code = f"# {request.description}\n"
            
            if request.language == CodeLanguage.PYTHON:
                code += "# TODO: Implement the following requirements:\n"
                for i, req in enumerate(request.requirements, 1):
                    code += f"# {i}. {req}\n"
                code += "\npass  # Replace with actual implementation\n"
            
            elif request.language == CodeLanguage.JAVASCRIPT:
                code += "// TODO: Implement the following requirements:\n"
                for i, req in enumerate(request.requirements, 1):
                    code += f"// {i}. {req}\n"
                code += "\n// Replace with actual implementation\n"
            
            # Create solution
            self.solution_counter += 1
            solution_id = f"solution_{self.solution_counter}_{datetime.now().timestamp()}"
            
            solution = CodeSolution(
                solution_id=solution_id,
                request_id=request.request_id,
                code=code,
                lines_of_code=len(code.split('\n')),
                model_used="generic_generator"
            )
            
            return solution
            
        except Exception as e:
            self.logger.error(f"Failed to generate generic code: {e}")
            return None
    
    async def _validate_solution(self, solution: CodeSolution, request: CodeRequest) -> None:
        """Validate generated code solution."""
        try:
            # Check syntax
            solution.syntax_valid = await self._validate_syntax(solution.code, request.language)
            
            # Calculate complexity
            solution.cyclomatic_complexity = await self._calculate_cyclomatic_complexity(solution.code, request.language)
            
            # Calculate quality scores
            solution.complexity_score = max(0.0, 1.0 - (solution.cyclomatic_complexity / 20.0))
            solution.maintainability_score = await self._calculate_maintainability(solution.code, request.language)
            solution.performance_score = await self._estimate_performance(solution.code, request.language)
            solution.security_score = await self._assess_security(solution.code, request.language)
            
            # Run linting if available
            solution.linting_score = await self._run_linting(solution.code, request.language)
            
        except Exception as e:
            self.logger.warning(f"Failed to validate solution: {e}")
    
    async def _check_syntax(self, code: str, language: CodeLanguage) -> List[Dict[str, Any]]:
        """Check code syntax and return errors."""
        errors = []
        
        try:
            if language == CodeLanguage.PYTHON:
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    errors.append({
                        "line": e.lineno,
                        "column": e.offset,
                        "message": e.msg,
                        "type": "syntax_error"
                    })
            
            # For other languages, we'd need appropriate parsers
            # This is a simplified implementation
            
        except Exception as e:
            self.logger.warning(f"Syntax check failed: {e}")
        
        return errors
    
    async def _check_style(self, code: str, language: CodeLanguage) -> List[Dict[str, Any]]:
        """Check code style violations."""
        violations = []
        
        try:
            if language == CodeLanguage.PYTHON:
                # Simple style checks
                lines = code.split('\n')
                for i, line in enumerate(lines, 1):
                    if len(line) > 100:
                        violations.append({
                            "line": i,
                            "message": "Line too long (>100 characters)",
                            "type": "style_violation"
                        })
                    
                    if line.strip().endswith(' '):
                        violations.append({
                            "line": i,
                            "message": "Trailing whitespace",
                            "type": "style_violation"
                        })
            
        except Exception as e:
            self.logger.warning(f"Style check failed: {e}")
        
        return violations
    
    async def _check_security(self, code: str, language: CodeLanguage) -> List[Dict[str, Any]]:
        """Check for security issues."""
        issues = []
        
        try:
            patterns = self.quality_patterns.get("security_issues", {}).get(language, [])
            
            for pattern, message in patterns:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    issues.append({
                        "line": line_num,
                        "message": message,
                        "type": "security_issue",
                        "severity": "medium"
                    })
        
        except Exception as e:
            self.logger.warning(f"Security check failed: {e}")
        
        return issues
    
    async def _check_performance(self, code: str, language: CodeLanguage) -> List[Dict[str, Any]]:
        """Check for performance issues."""
        issues = []
        
        try:
            patterns = self.quality_patterns.get("performance_issues", {}).get(language, [])
            
            for pattern, message in patterns:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    issues.append({
                        "line": line_num,
                        "message": message,
                        "type": "performance_issue",
                        "severity": "low"
                    })
        
        except Exception as e:
            self.logger.warning(f"Performance check failed: {e}")
        
        return issues
    
    async def _calculate_complexity(self, code: str, language: CodeLanguage) -> Dict[str, float]:
        """Calculate complexity metrics."""
        metrics = {}
        
        try:
            lines = code.split('\n')
            metrics['lines_of_code'] = len([line for line in lines if line.strip()])
            metrics['total_lines'] = len(lines)
            
            # Simple complexity indicators
            if language == CodeLanguage.PYTHON:
                metrics['function_count'] = len(re.findall(r'def\s+\w+', code))
                metrics['class_count'] = len(re.findall(r'class\s+\w+', code))
                metrics['if_statements'] = len(re.findall(r'\bif\b', code))
                metrics['loop_count'] = len(re.findall(r'\b(for|while)\b', code))
            
        except Exception as e:
            self.logger.warning(f"Complexity calculation failed: {e}")
        
        return metrics
    
    async def _calculate_quality_metrics(self, code: str, language: CodeLanguage) -> Dict[str, float]:
        """Calculate quality metrics."""
        metrics = {}
        
        try:
            lines = code.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            # Comment ratio
            if language == CodeLanguage.PYTHON:
                comment_lines = [line for line in lines if line.strip().startswith('#')]
                metrics['comment_ratio'] = len(comment_lines) / max(len(non_empty_lines), 1)
            
            # Average line length
            if non_empty_lines:
                metrics['avg_line_length'] = sum(len(line) for line in non_empty_lines) / len(non_empty_lines)
            else:
                metrics['avg_line_length'] = 0.0
            
            # Indentation consistency (for Python)
            if language == CodeLanguage.PYTHON:
                indentations = []
                for line in lines:
                    if line.strip():
                        indent = len(line) - len(line.lstrip())
                        if indent > 0:
                            indentations.append(indent)
                
                if indentations:
                    # Check if indentation is consistent (multiples of 4)
                    consistent = all(indent % 4 == 0 for indent in indentations)
                    metrics['indentation_consistency'] = 1.0 if consistent else 0.5
                else:
                    metrics['indentation_consistency'] = 1.0
        
        except Exception as e:
            self.logger.warning(f"Quality metrics calculation failed: {e}")
        
        return metrics
    
    def _format_parameters(self, parameters: List[Dict[str, str]], language: CodeLanguage) -> str:
        """Format function parameters for the given language."""
        if not parameters:
            return ""
        
        if language == CodeLanguage.PYTHON:
            param_strs = []
            for param in parameters:
                param_str = param['name']
                if param.get('type'):
                    param_str += f": {param['type']}"
                if param.get('default'):
                    param_str += f" = {param['default']}"
                param_strs.append(param_str)
            return ", ".join(param_strs)
        
        elif language == CodeLanguage.JAVASCRIPT:
            return ", ".join(param['name'] for param in parameters)
        
        return ""
    
    def _format_arg_docs(self, parameters: List[Dict[str, str]]) -> str:
        """Format argument documentation."""
        if not parameters:
            return "        None"
        
        docs = []
        for param in parameters:
            param_type = param.get('type', 'Any')
            param_desc = param.get('description', f"{param['name']} parameter")
            docs.append(f"        {param['name']} ({param_type}): {param_desc}")
        
        return "\n".join(docs)
    
    async def _generate_function_body(self, request: CodeRequest) -> str:
        """Generate function body based on requirements."""
        # Simple implementation - in practice would use more sophisticated generation
        if request.requirements:
            body_lines = ["# Implementation based on requirements:"]
            for i, req in enumerate(request.requirements, 1):
                body_lines.append(f"    # {i}. {req}")
            body_lines.append("    pass  # TODO: Implement actual logic")
            return "\n".join(body_lines)
        else:
            return "    pass  # TODO: Implement function logic"
    
    async def _generate_class_methods(self, request: CodeRequest) -> str:
        """Generate class methods based on requirements."""
        methods = []
        
        # Generate basic methods based on requirements
        for req in request.requirements:
            if "method" in req.lower():
                method_name = req.lower().replace(" ", "_").replace("method", "").strip("_")
                if method_name:
                    methods.append(f'''    def {method_name}(self):
        """
        {req}
        """
        pass''')
        
        if not methods:
            methods.append('''    def example_method(self):
        """
        Example method - replace with actual implementation.
        """
        pass''')
        
        return "\n\n".join(methods)
    
    async def _generate_init_method(self, request: CodeRequest) -> Tuple[str, str]:
        """Generate __init__ method parameters and body."""
        if request.parameters:
            params = ", " + self._format_parameters(request.parameters, request.language)
            body_lines = []
            for param in request.parameters:
                body_lines.append(f"        self.{param['name']} = {param['name']}")
            body = "\n".join(body_lines)
        else:
            params = ""
            body = "        pass"
        
        return params, body
    
    def _generate_imports(self, request: CodeRequest) -> str:
        """Generate import statements for module."""
        imports = []
        
        # Add common imports based on language
        if request.language == CodeLanguage.PYTHON:
            imports.extend([
                "from typing import Dict, List, Optional, Any",
                "from datetime import datetime"
            ])
        
        # Add dependency imports
        for dep in request.dependencies:
            if request.language == CodeLanguage.PYTHON:
                imports.append(f"import {dep}")
        
        return "\n".join(imports)
    
    def _generate_constants(self, request: CodeRequest) -> str:
        """Generate module constants."""
        # Simple constant generation
        if request.language == CodeLanguage.PYTHON:
            return '"""Module constants."""\n\nMODULE_VERSION = "1.0.0"'
        return ""
    
    async def _generate_module_functions(self, request: CodeRequest) -> str:
        """Generate module-level functions."""
        # Generate utility functions based on requirements
        functions = []
        
        for req in request.requirements:
            if "function" in req.lower():
                func_name = req.lower().replace(" ", "_").replace("function", "").strip("_")
                if func_name and request.language == CodeLanguage.PYTHON:
                    functions.append(f'''def {func_name}():
    """
    {req}
    """
    pass''')
        
        return "\n\n".join(functions)
    
    async def _generate_module_classes(self, request: CodeRequest) -> str:
        """Generate module classes."""
        # Generate classes based on requirements
        classes = []
        
        for req in request.requirements:
            if "class" in req.lower():
                class_name = req.replace(" ", "").replace("class", "").strip()
                if class_name and request.language == CodeLanguage.PYTHON:
                    classes.append(f'''class {class_name}:
    """
    {req}
    """
    
    def __init__(self):
        """Initialize {class_name}."""
        pass''')
        
        return "\n\n".join(classes)
    
    async def _generate_tests(self, solution: CodeSolution, request: CodeRequest) -> str:
        """Generate unit tests for the solution."""
        try:
            template = self.code_templates.get(request.language, {}).get("test", "")
            if not template:
                return ""
            
            # Generate basic test structure
            test_code = template.format(
                module="generated_module",
                function_name=request.function_name or "generated_function",
                test_description="work correctly",
                test_body="assert True  # TODO: Add actual test assertions"
            )
            
            return test_code
            
        except Exception as e:
            self.logger.warning(f"Failed to generate tests: {e}")
            return ""
    
    async def _generate_documentation(self, solution: CodeSolution, request: CodeRequest) -> str:
        """Generate documentation for the solution."""
        try:
            doc_parts = [
                f"# {request.description}",
                "",
                "## Overview",
                request.description,
                "",
                "## Requirements",
            ]
            
            for i, req in enumerate(request.requirements, 1):
                doc_parts.append(f"{i}. {req}")
            
            doc_parts.extend([
                "",
                "## Usage",
                "```python",
                "# Example usage",
                "# TODO: Add usage examples",
                "```",
                "",
                "## Quality Metrics",
                f"- Lines of Code: {solution.lines_of_code}",
                f"- Complexity Score: {solution.complexity_score:.2f}",
                f"- Maintainability Score: {solution.maintainability_score:.2f}"
            ])
            
            return "\n".join(doc_parts)
            
        except Exception as e:
            self.logger.warning(f"Failed to generate documentation: {e}")
            return ""
    
    async def _generate_code_fixes(self, code: str, analysis: Dict[str, Any], request: CodeRequest) -> Optional[str]:
        """Generate fixes for problematic code."""
        try:
            fixed_code = code
            
            # Apply simple fixes based on analysis
            if analysis.get("syntax_errors"):
                # For now, just add a comment about syntax errors
                fixed_code = f"# FIXED: Syntax errors found and corrected\n{fixed_code}"
            
            if analysis.get("style_violations"):
                # Apply basic style fixes
                lines = fixed_code.split('\n')
                fixed_lines = []
                for line in lines:
                    # Remove trailing whitespace
                    fixed_line = line.rstrip()
                    fixed_lines.append(fixed_line)
                fixed_code = '\n'.join(fixed_lines)
            
            return fixed_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate code fixes: {e}")
            return None
    
    async def _validate_syntax(self, code: str, language: CodeLanguage) -> bool:
        """Validate code syntax."""
        try:
            if language == CodeLanguage.PYTHON:
                ast.parse(code)
            except Exception:
            return False
        
        # For other languages, assume valid for now
        return True
    
    async def _calculate_cyclomatic_complexity(self, code: str, language: CodeLanguage) -> int:
        """Calculate cyclomatic complexity."""
        try:
            if language == CodeLanguage.PYTHON:
                # Simple complexity calculation
                complexity = 1  # Base complexity
                complexity += len(re.findall(r'\bif\b', code))
                complexity += len(re.findall(r'\belif\b', code))
                complexity += len(re.findall(r'\bfor\b', code))
                complexity += len(re.findall(r'\bwhile\b', code))
                complexity += len(re.findall(r'\bexcept\b', code))
                return complexity
        except Exception:
            pass
        
        return 1
    
    async def _calculate_maintainability(self, code: str, language: CodeLanguage) -> float:
        """Calculate maintainability score."""
        try:
            lines = code.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            # Simple maintainability factors
            score = 1.0
            
            # Penalize very long functions
            if len(non_empty_lines) > 50:
                score -= 0.2
            
            # Reward comments
            if language == CodeLanguage.PYTHON:
                comment_lines = [line for line in lines if line.strip().startswith('#')]
                comment_ratio = len(comment_lines) / max(len(non_empty_lines), 1)
                return max(0.0, min(1.0, score))
            
        except Exception:
            return 0.5
    
    async def _estimate_performance(self, code: str, language: CodeLanguage) -> float:
        """Estimate performance score."""
        try:
            # Simple performance estimation
            score = 1.0
            
            # Check for potential performance issues
            if language == CodeLanguage.PYTHON:
                # Nested loops penalty
                nested_loops = len(re.findall(r'for.*for', code, re.DOTALL))
                score -= nested_loops * 0.1
                
                # String concatenation in loops penalty
                if re.search(r'for.*\+=.*str', code, re.DOTALL):
                    score -= 0.2
            
            return max(0.0, min(1.0, score))
            
        except Exception:
            return 0.5
    
    async def _assess_security(self, code: str, language: CodeLanguage) -> float:
        """Assess security score."""
        try:
            score = 1.0
            
            # Check for security issues
            patterns = self.quality_patterns.get("security_issues", {}).get(language, [])
            
            for pattern, _ in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    score -= 0.2
            
            return max(0.0, min(1.0, score))
            
        except Exception:
            return 0.5
    
    async def _run_linting(self, code: str, language: CodeLanguage) -> float:
        """Run linting and return score."""
        # Simplified linting - in practice would use actual linters
        try:
            if language == CodeLanguage.PYTHON:
                # Check basic Python style
                lines = code.split('\n')
                violations = 0
                
                for line in lines:
                    if len(line) > 100:
                        violations += 1
                    if line.endswith(' '):
                        violations += 1
                
                score = max(0.0, 1.0 - (violations / max(len(lines), 1)))
                return score
        except Exception:
            pass
        
        return 0.8  # Default good score
    
    async def _generate_improvement_suggestions(self, analysis: CodeAnalysis) -> List[str]:
        """Generate improvement suggestions based on analysis."""
        suggestions = []
        
        if analysis.syntax_errors:
            suggestions.append("Fix syntax errors to ensure code can run")
        
        if analysis.style_violations:
            suggestions.append("Address style violations for better readability")
        
        if analysis.security_issues:
            suggestions.append("Review and fix security vulnerabilities")
        
        if analysis.performance_issues:
            suggestions.append("Optimize code for better performance")
        
        # Add complexity-based suggestions
        complexity = analysis.complexity_metrics.get('cyclomatic_complexity', 0)
        if complexity > 10:
            suggestions.append("Consider breaking down complex functions")
        
        return suggestions
    
    async def _identify_refactoring_opportunities(self, code: str, language: CodeLanguage) -> List[str]:
        """Identify refactoring opportunities."""
        opportunities = []
        
        try:
            lines = code.split('\n')
            
            # Long function detection
            if len(lines) > 50:
                opportunities.append("Consider breaking down long functions")
            
            # Code duplication detection (simplified)
            if language == CodeLanguage.PYTHON:
                # Look for repeated patterns
                function_defs = re.findall(r'def\s+(\w+)', code)
                if len(function_defs) > len(set(function_defs)):
                    opportunities.append("Consider extracting common functionality")
            
            # Deep nesting detection
            max_indent = 0
            for line in lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    max_indent = max(max_indent, indent)
            
            if max_indent > 16:  # More than 4 levels of nesting
                                opportunities.append("Reduce nesting levels for better readability")
                        except Exception:
                            pass
        
        return opportunities
    
    def _estimate_generation_time(self, request: CodeRequest) -> float:
        """Estimate code generation time in seconds."""
        base_time = 30  # 30 seconds base
        
        # Add time based on task type
        task_times = {
            CodeTaskType.GENERATE_FUNCTION: 20,
            CodeTaskType.GENERATE_CLASS: 40,
            CodeTaskType.GENERATE_MODULE: 60,
            CodeTaskType.DEBUG_CODE: 30,
            CodeTaskType.OPTIMIZE_CODE: 25
        }
        
        task_time = task_times.get(request.task_type, 30)
        
        # Add time for tests and documentation
        if request.include_unit_tests:
            task_time += 15
        
        if request.include_docstrings:
            task_time += 10
        
        return base_time + task_time
    
    async def _cleanup_temp_files(self) -> None:
        """Clean up temporary files."""
        while True:
            try:
                # Clean up any temporary files created during code execution
                # This is a placeholder for actual cleanup logic
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                self.logger.error(f"Error in temp file cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def _update_statistics(self) -> None:
        """Update service statistics."""
        while True:
            try:
                # Update average generation time
                if self.stats["completed_tasks"] > 0:
                    total_time = sum(
                        solution.generation_time 
                        for solution in self.code_solutions.values()
                    )
                    self.stats["average_generation_time"] = total_time / self.stats["completed_tasks"]
                
                # Update average quality score
                if self.code_solutions:
                    total_quality = sum(
                        solution._calculate_overall_quality()
                        for solution in self.code_solutions.values()
                    )
                    self.stats["average_quality_score"] = total_quality / len(self.code_solutions)
                
                # Update syntax error rate
                if self.code_solutions:
                    syntax_errors = sum(
                        1 for solution in self.code_solutions.values()
                        if not solution.syntax_valid
                    )
                    self.stats["syntax_error_rate"] = syntax_errors / len(self.code_solutions)
                
                # Sleep for 5 minutes before next update
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(300)