"""
Sandboxed code execution environment for autonomous AI agents.

This module implements a secure sandbox for testing code modifications
before applying them to the main agent code, with resource limits and
safety restrictions.
"""

import ast
import sys
import io
import os
import threading
import time
import resource
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .code_analyzer import CodeAnalyzer, CodeRiskLevel
from ..utils.security import validate_code_safety, sanitize_code


class SandboxMode(Enum):
    """Sandbox execution modes."""
    RESTRICTED = "restricted"  # Highly restricted, safe operations only
    LIMITED = "limited"       # Limited access to some modules
    TESTING = "testing"       # For testing with more permissions
    VALIDATION = "validation" # For code validation only


class ExecutionStatus(Enum):
    """Status of code execution."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    MEMORY_LIMIT = "memory_limit"
    SECURITY_VIOLATION = "security_violation"
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"


@dataclass
class SandboxLimits:
    """Resource limits for sandbox execution."""
    max_execution_time: float = 5.0  # seconds
    max_memory_mb: int = 100         # megabytes
    max_output_size: int = 10000     # characters
    max_file_operations: int = 10    # number of file operations
    max_network_requests: int = 0    # network requests (0 = disabled)
    max_subprocess_calls: int = 0    # subprocess calls (0 = disabled)


@dataclass
class ExecutionResult:
    """Result of code execution in sandbox."""
    execution_id: str
    status: ExecutionStatus
    return_value: Any = None
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0.0
    memory_used: int = 0
    error_message: str = ""
    security_violations: List[str] = field(default_factory=list)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SandboxEnvironment:
    """Sandbox environment configuration."""
    environment_id: str
    mode: SandboxMode
    limits: SandboxLimits
    allowed_modules: Set[str] = field(default_factory=set)
    blocked_modules: Set[str] = field(default_factory=set)
    allowed_builtins: Set[str] = field(default_factory=set)
    custom_globals: Dict[str, Any] = field(default_factory=dict)
    working_directory: Optional[str] = None


class RestrictedBuiltins:
    """Restricted builtins for sandbox execution."""
    
    SAFE_BUILTINS = {
        # Basic types and operations
        'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes',
        'chr', 'complex', 'dict', 'divmod', 'enumerate', 'filter',
        'float', 'frozenset', 'hex', 'int', 'isinstance', 'issubclass',
        'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'oct',
        'ord', 'pow', 'range', 'repr', 'reversed', 'round', 'set',
        'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip',
        
        # Safe functions
        'hash', 'id', 'callable', 'hasattr', 'getattr', 'setattr',
        'delattr', 'dir', 'vars', 'locals', 'globals',
        
        # Exceptions
        'Exception', 'ValueError', 'TypeError', 'AttributeError',
        'KeyError', 'IndexError', 'RuntimeError', 'NotImplementedError',
        
        # Constants
        'True', 'False', 'None', 'Ellipsis', 'NotImplemented'
    }
    
    DANGEROUS_BUILTINS = {
        'eval', 'exec', 'compile', '__import__', 'open', 'input',
        'raw_input', 'file', 'reload', 'apply', 'buffer', 'coerce',
        'intern', 'execfile'
    }


class SandboxViolationError(Exception):
    """Exception raised when sandbox security is violated."""
    pass


class TimeoutError(Exception):
    """Exception raised when execution times out."""
    pass


class CodeSandbox(AgentModule):
    """
    Secure sandbox environment for testing code modifications
    with resource limits and security restrictions.
    """
    
    def __init__(self, agent_id: str, code_analyzer: CodeAnalyzer):
        super().__init__(agent_id)
        self.code_analyzer = code_analyzer
        self.logger = get_agent_logger(agent_id, "sandbox")
        
        # Sandbox environments
        self.environments: Dict[str, SandboxEnvironment] = {}
        self.default_environment_id = "default"
        
        # Execution tracking
        self.execution_history: List[ExecutionResult] = []
        self.active_executions: Dict[str, threading.Thread] = {}
        self.max_history_size = 1000
        
        # Security monitoring
        self.security_violations: List[Dict[str, Any]] = []
        self.blocked_operations: Set[str] = set()
        
        # Statistics
        self.sandbox_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "security_violations": 0,
            "timeouts": 0,
            "memory_violations": 0
        }
        
        # Temporary directory for sandbox operations
        self.sandbox_dir = f"data/agents/{agent_id}/sandbox"
        
        self.logger.info(f"Code sandbox initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the sandbox environment."""
        try:
            # Create sandbox directory
            Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)
            
            # Create default sandbox environment
            await self._create_default_environment()
            
            # Initialize security monitoring
            self._initialize_security_monitoring()
            
            self.logger.info("Code sandbox initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize sandbox: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the sandbox gracefully."""
        try:
            # Stop all active executions
            await self._stop_all_executions()
            
            # Clean up temporary files
            await self._cleanup_sandbox_files()
            
            self.logger.info("Code sandbox shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during sandbox shutdown: {e}")
    
    async def execute_code(
        self,
        code: str,
        environment_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        expected_output: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute code in a sandboxed environment.
        
        Args:
            code: Python code to execute
            environment_id: ID of sandbox environment to use
            input_data: Input data to provide to the code
            expected_output: Expected output for validation
            
        Returns:
            ExecutionResult with execution details
        """
        try:
            execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.execution_history)}"
            environment_id = environment_id or self.default_environment_id
            
            if environment_id not in self.environments:
                raise ValueError(f"Sandbox environment {environment_id} not found")
            
            environment = self.environments[environment_id]
            
            # Pre-execution security check
            security_level, security_issues = validate_code_safety(code)
            if security_level in [CodeRiskLevel.HIGH_RISK, CodeRiskLevel.DANGEROUS]:
                return ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.SECURITY_VIOLATION,
                    error_message=f"Code security level too high: {security_level.value}",
                    security_violations=security_issues
                )
            
            # Sanitize code
            sanitized_code = sanitize_code(code)
            
            # Execute in sandbox
            result = await self._execute_in_sandbox(
                execution_id, sanitized_code, environment, input_data
            )
            
            # Validate output if expected
            if expected_output and result.status == ExecutionStatus.SUCCESS:
                if result.stdout.strip() != expected_output.strip():
                    result.status = ExecutionStatus.FAILED
                    result.error_message = f"Output mismatch. Expected: {expected_output}, Got: {result.stdout}"
            
            # Store execution result
            self.execution_history.append(result)
            if len(self.execution_history) > self.max_history_size:
                self.execution_history.pop(0)
            
            # Update statistics
            self._update_sandbox_stats(result)
            
            log_agent_event(
                self.agent_id,
                "code_executed_in_sandbox",
                {
                    "execution_id": execution_id,
                    "status": result.status.value,
                    "execution_time": result.execution_time,
                    "security_violations": len(result.security_violations)
                }
            )
            
            self.logger.info(f"Executed code in sandbox {execution_id}: {result.status.value}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute code in sandbox: {e}")
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                error_message=str(e)
            )
    
    async def test_code_modification(
        self,
        original_code: str,
        modified_code: str,
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Test a code modification by running test cases.
        
        Args:
            original_code: Original code
            modified_code: Modified code to test
            test_cases: List of test cases with inputs and expected outputs
            
        Returns:
            Test results with pass/fail status
        """
        try:
            test_results = {
                "modification_safe": True,
                "all_tests_passed": True,
                "original_results": [],
                "modified_results": [],
                "test_summary": {
                    "total_tests": len(test_cases),
                    "passed": 0,
                    "failed": 0,
                    "errors": 0
                }
            }
            
            # Test original code
            for i, test_case in enumerate(test_cases):
                original_result = await self.execute_code(
                    original_code,
                    input_data=test_case.get("input", {}),
                    expected_output=test_case.get("expected_output")
                )
                test_results["original_results"].append(original_result)
            
            # Test modified code
            for i, test_case in enumerate(test_cases):
                modified_result = await self.execute_code(
                    modified_code,
                    input_data=test_case.get("input", {}),
                    expected_output=test_case.get("expected_output")
                )
                test_results["modified_results"].append(modified_result)
                
                # Check if modification is safe
                if modified_result.security_violations:
                    test_results["modification_safe"] = False
                
                # Check test results
                if modified_result.status == ExecutionStatus.SUCCESS:
                    test_results["test_summary"]["passed"] += 1
                elif modified_result.status in [ExecutionStatus.FAILED, ExecutionStatus.RUNTIME_ERROR]:
                    test_results["test_summary"]["failed"] += 1
                    test_results["all_tests_passed"] = False
                else:
                    test_results["test_summary"]["errors"] += 1
                    test_results["all_tests_passed"] = False
            
            return test_results
            
        except Exception as e:
            self.logger.error(f"Failed to test code modification: {e}")
            return {
                "modification_safe": False,
                "all_tests_passed": False,
                "error": str(e)
            }
    
    async def create_sandbox_environment(
        self,
        environment_id: str,
        mode: SandboxMode,
        limits: Optional[SandboxLimits] = None,
        allowed_modules: Optional[List[str]] = None,
        blocked_modules: Optional[List[str]] = None
    ) -> bool:
        """
        Create a new sandbox environment.
        
        Args:
            environment_id: Unique ID for the environment
            mode: Sandbox mode
            limits: Resource limits
            allowed_modules: List of allowed modules
            blocked_modules: List of blocked modules
            
        Returns:
            True if environment was created successfully
        """
        try:
            if environment_id in self.environments:
                raise ValueError(f"Environment {environment_id} already exists")
            
            # Set default limits based on mode
            if limits is None:
                limits = self._get_default_limits(mode)
            
            # Set default module restrictions
            if allowed_modules is None:
                allowed_modules = self._get_default_allowed_modules(mode)
            
            if blocked_modules is None:
                blocked_modules = self._get_default_blocked_modules(mode)
            
            # Create environment
            environment = SandboxEnvironment(
                environment_id=environment_id,
                mode=mode,
                limits=limits,
                allowed_modules=set(allowed_modules),
                blocked_modules=set(blocked_modules),
                allowed_builtins=RestrictedBuiltins.SAFE_BUILTINS.copy(),
                working_directory=os.path.join(self.sandbox_dir, environment_id)
            )
            
            # Create working directory
            Path(environment.working_directory).mkdir(parents=True, exist_ok=True)
            
            self.environments[environment_id] = environment
            
            self.logger.info(f"Created sandbox environment: {environment_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create sandbox environment {environment_id}: {e}")
            return False
    
    def get_execution_history(self, limit: int = 50) -> List[ExecutionResult]:
        """Get recent execution history."""
        return self.execution_history[-limit:]
    
    def get_sandbox_statistics(self) -> Dict[str, Any]:
        """Get sandbox statistics."""
        return {
            **self.sandbox_stats,
            "active_executions": len(self.active_executions),
            "environments_count": len(self.environments),
            "history_size": len(self.execution_history),
            "security_violations_count": len(self.security_violations)
        }
    
    # Private helper methods
    
    async def _create_default_environment(self) -> None:
        """Create the default sandbox environment."""
        await self.create_sandbox_environment(
            self.default_environment_id,
            SandboxMode.RESTRICTED,
            SandboxLimits(
                max_execution_time=3.0,
                max_memory_mb=50,
                max_output_size=5000
            )
        )
    
    def _initialize_security_monitoring(self) -> None:
        """Initialize security monitoring systems."""
        # Set up blocked operations
        self.blocked_operations.update([
            'eval', 'exec', 'compile', '__import__',
            'open', 'file', 'input', 'raw_input',
            'reload', 'apply', 'execfile'
        ])
    
    async def _execute_in_sandbox(
        self,
        execution_id: str,
        code: str,
        environment: SandboxEnvironment,
        input_data: Optional[Dict[str, Any]]
    ) -> ExecutionResult:
        """Execute code in the sandbox environment."""
        start_time = time.time()
        
        # Prepare execution context
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Create restricted globals
        restricted_globals = self._create_restricted_globals(environment, input_data)
        
        # Create restricted locals
        restricted_locals = {}
        
        try:
            # Parse code to AST for additional validation
            try:
                ast_tree = ast.parse(code)
                self._validate_ast_security(ast_tree, environment)
            except SyntaxError as e:
                return ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.SYNTAX_ERROR,
                    error_message=str(e),
                    execution_time=time.time() - start_time
                )
            except SandboxViolationError as e:
                return ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.SECURITY_VIOLATION,
                    error_message=str(e),
                    security_violations=[str(e)],
                    execution_time=time.time() - start_time
                )
            
            # Set up resource limits
            self._set_resource_limits(environment.limits)
            
            # Redirect stdout/stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # Execute with timeout
            result = await self._execute_with_timeout(
                code, restricted_globals, restricted_locals, environment.limits.max_execution_time
            )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.SUCCESS,
                return_value=result,
                stdout=stdout_capture.getvalue()[:environment.limits.max_output_size],
                stderr=stderr_capture.getvalue()[:environment.limits.max_output_size],
                execution_time=execution_time,
                resource_usage=self._get_resource_usage()
            )
            
        except TimeoutError:
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.TIMEOUT,
                error_message=f"Execution timed out after {environment.limits.max_execution_time}s",
                stdout=stdout_capture.getvalue()[:environment.limits.max_output_size],
                stderr=stderr_capture.getvalue()[:environment.limits.max_output_size],
                execution_time=time.time() - start_time
            )
        except MemoryError:
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.MEMORY_LIMIT,
                error_message="Memory limit exceeded",
                stdout=stdout_capture.getvalue()[:environment.limits.max_output_size],
                stderr=stderr_capture.getvalue()[:environment.limits.max_output_size],
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.RUNTIME_ERROR,
                error_message=str(e),
                stdout=stdout_capture.getvalue()[:environment.limits.max_output_size],
                stderr=stderr_capture.getvalue()[:environment.limits.max_output_size],
                execution_time=time.time() - start_time
            )
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def _create_restricted_globals(
        self, 
        environment: SandboxEnvironment, 
        input_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create restricted global namespace for execution."""
        # Start with safe builtins
        restricted_globals = {
            '__builtins__': {
                name: getattr(__builtins__, name) 
                for name in environment.allowed_builtins 
                if hasattr(__builtins__, name)
            }
        }
        
        # Add allowed modules
        for module_name in environment.allowed_modules:
            try:
                if module_name not in environment.blocked_modules:
                    restricted_globals[module_name] = __import__(module_name)
            except ImportError:
                pass  # Module not available
        
        # Add custom globals
        restricted_globals.update(environment.custom_globals)
        
        # Add input data
        if input_data:
            restricted_globals.update(input_data)
        
        return restricted_globals
    
    def _validate_ast_security(self, ast_tree: ast.AST, environment: SandboxEnvironment) -> None:
        """Validate AST for security violations."""
        for node in ast.walk(ast_tree):
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in self.blocked_operations:
                        raise SandboxViolationError(f"Blocked function call: {func_name}")
            
            # Check for dangerous imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_names = []
                if isinstance(node, ast.Import):
                    module_names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_names = [node.module]
                
                for module_name in module_names:
                    if module_name in environment.blocked_modules:
                        raise SandboxViolationError(f"Blocked module import: {module_name}")
                    if module_name not in environment.allowed_modules:
                        raise SandboxViolationError(f"Unauthorized module import: {module_name}")
            
            # Check for attribute access to dangerous objects
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    if node.value.id in ['os', 'sys'] and node.attr in ['system', 'exit', 'quit']:
                        raise SandboxViolationError(f"Blocked attribute access: {node.value.id}.{node.attr}")
    
    def _set_resource_limits(self, limits: SandboxLimits) -> None:
        """Set resource limits for execution."""
        try:
            # Set memory limit (in bytes)
            memory_limit = limits.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # Set CPU time limit
            cpu_limit = int(limits.max_execution_time)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            
        except (OSError, ValueError) as e:
            # Resource limits might not be available on all platforms
            self.logger.warning(f"Could not set resource limits: {e}")
    
    async def _execute_with_timeout(
        self,
        code: str,
        globals_dict: Dict[str, Any],
        locals_dict: Dict[str, Any],
        timeout: float
    ) -> Any:
        """Execute code with timeout."""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = exec(code, globals_dict, locals_dict)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            # Thread is still running, timeout occurred
            raise TimeoutError(f"Execution timed out after {timeout} seconds")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage."""
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "user_time": usage.ru_utime,
                "system_time": usage.ru_stime,
                "max_memory": usage.ru_maxrss,
                "page_faults": usage.ru_majflt + usage.ru_minflt
            }
        except Exception:
            return {}
    
    def _get_default_limits(self, mode: SandboxMode) -> SandboxLimits:
        """Get default limits for sandbox mode."""
        if mode == SandboxMode.RESTRICTED:
            return SandboxLimits(
                max_execution_time=3.0,
                max_memory_mb=50,
                max_output_size=5000
            )
        elif mode == SandboxMode.LIMITED:
            return SandboxLimits(
                max_execution_time=10.0,
                max_memory_mb=100,
                max_output_size=10000
            )
        elif mode == SandboxMode.TESTING:
            return SandboxLimits(
                max_execution_time=30.0,
                max_memory_mb=200,
                max_output_size=50000
            )
        else:  # VALIDATION
            return SandboxLimits(
                max_execution_time=5.0,
                max_memory_mb=75,
                max_output_size=10000
            )
    
    def _get_default_allowed_modules(self, mode: SandboxMode) -> List[str]:
        """Get default allowed modules for sandbox mode."""
        safe_modules = ['math', 'random', 'datetime', 'json', 'typing', 'dataclasses', 'enum']
        
        if mode == SandboxMode.RESTRICTED:
            return ['math', 'random', 'datetime']
        elif mode == SandboxMode.LIMITED:
            return safe_modules + ['collections', 'itertools', 'functools']
        elif mode == SandboxMode.TESTING:
            return safe_modules + ['collections', 'itertools', 'functools', 'copy', 'uuid']
        else:  # VALIDATION
            return safe_modules
    
    def _get_default_blocked_modules(self, mode: SandboxMode) -> List[str]:
        """Get default blocked modules for sandbox mode."""
        dangerous_modules = [
            'os', 'sys', 'subprocess', 'shutil', 'glob', 'tempfile',
            'socket', 'urllib', 'http', 'ftplib', 'smtplib',
            'ctypes', 'multiprocessing', 'threading', 'pickle',
            'marshal', 'shelve', 'dbm', 'importlib'
        ]
        
        return dangerous_modules
    
    def _update_sandbox_stats(self, result: ExecutionResult) -> None:
        """Update sandbox statistics."""
        self.sandbox_stats["total_executions"] += 1
        
        if result.status == ExecutionStatus.SUCCESS:
            self.sandbox_stats["successful_executions"] += 1
        else:
            self.sandbox_stats["failed_executions"] += 1
        
        if result.status == ExecutionStatus.SECURITY_VIOLATION:
            self.sandbox_stats["security_violations"] += 1
        elif result.status == ExecutionStatus.TIMEOUT:
            self.sandbox_stats["timeouts"] += 1
        elif result.status == ExecutionStatus.MEMORY_LIMIT:
            self.sandbox_stats["memory_violations"] += 1
    
    async def _stop_all_executions(self) -> None:
        """Stop all active executions."""
        for execution_id, thread in self.active_executions.items():
            if thread.is_alive():
                # Note: Python threads cannot be forcibly terminated
                # In a production system, you might use subprocess for better isolation
                self.logger.warning(f"Cannot forcibly stop execution {execution_id}")
        
        self.active_executions.clear()
    
    async def _cleanup_sandbox_files(self) -> None:
        """Clean up temporary sandbox files."""
        try:
            import shutil
            if os.path.exists(self.sandbox_dir):
                shutil.rmtree(self.sandbox_dir)
        except Exception as e:
            self.logger.error(f"Failed to cleanup sandbox files: {e}")