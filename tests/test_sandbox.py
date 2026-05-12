"""
Unit tests for the sandboxed code execution environment.

Tests the sandbox system for safe code execution, resource limits,
and security restrictions.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock

from autonomous_ai_ecosystem.agents.sandbox import (
    CodeSandbox, SandboxMode, ExecutionStatus, SandboxLimits,
    ExecutionResult, RestrictedBuiltins
)
from autonomous_ai_ecosystem.agents.code_analyzer import CodeAnalyzer


class TestCodeSandbox:
    """Test cases for the CodeSandbox."""
    
    @pytest.fixture
    def mock_code_analyzer(self):
        """Create a mock code analyzer."""
        analyzer = Mock(spec=CodeAnalyzer)
        return analyzer
    
    @pytest.fixture
    def code_sandbox(self, mock_code_analyzer):
        """Create a CodeSandbox instance for testing."""
        return CodeSandbox("test_agent", mock_code_analyzer)
    
    @pytest.mark.asyncio
    async def test_initialization(self, code_sandbox):
        """Test sandbox initialization."""
        await code_sandbox.initialize()
        
        assert code_sandbox.agent_id == "test_agent"
        assert len(code_sandbox.environments) == 1  # Default environment
        assert "default" in code_sandbox.environments
        assert os.path.exists(code_sandbox.sandbox_dir)
    
    @pytest.mark.asyncio
    async def test_execute_safe_code(self, code_sandbox):
        """Test execution of safe code."""
        await code_sandbox.initialize()
        
        safe_code = '''
result = 2 + 3
print(f"Result: {result}")
'''
        
        execution_result = await code_sandbox.execute_code(safe_code)
        
        assert execution_result.status == ExecutionStatus.SUCCESS
        assert "Result: 5" in execution_result.stdout
        assert execution_result.execution_time > 0
        assert len(execution_result.security_violations) == 0
    
    @pytest.mark.asyncio
    async def test_execute_code_with_function(self, code_sandbox):
        """Test execution of code with function definition."""
        await code_sandbox.initialize()
        
        function_code = '''
def add_numbers(a, b):
    return a + b

result = add_numbers(10, 20)
print(f"Sum: {result}")
'''
        
        execution_result = await code_sandbox.execute_code(function_code)
        
        assert execution_result.status == ExecutionStatus.SUCCESS
        assert "Sum: 30" in execution_result.stdout
    
    @pytest.mark.asyncio
    async def test_execute_code_with_input_data(self, code_sandbox):
        """Test execution with input data."""
        await code_sandbox.initialize()
        
        code_with_input = '''
x = input_value * 2
print(f"Double: {x}")
'''
        
        input_data = {"input_value": 15}
        execution_result = await code_sandbox.execute_code(code_with_input, input_data=input_data)
        
        assert execution_result.status == ExecutionStatus.SUCCESS
        assert "Double: 30" in execution_result.stdout
    
    @pytest.mark.asyncio
    async def test_execute_code_with_expected_output(self, code_sandbox):
        """Test execution with expected output validation."""
        await code_sandbox.initialize()
        
        code = '''
print("Hello, World!")
'''
        
        # Test with correct expected output
        execution_result = await code_sandbox.execute_code(
            code, 
            expected_output="Hello, World!"
        )
        
        assert execution_result.status == ExecutionStatus.SUCCESS
        
        # Test with incorrect expected output
        execution_result = await code_sandbox.execute_code(
            code, 
            expected_output="Goodbye, World!"
        )
        
        assert execution_result.status == ExecutionStatus.FAILED
        assert "Output mismatch" in execution_result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_dangerous_code(self, code_sandbox):
        """Test execution of dangerous code."""
        await code_sandbox.initialize()
        
        dangerous_code = '''
eval("print('This should be blocked')")
'''
        
        execution_result = await code_sandbox.execute_code(dangerous_code)
        
        # Should be blocked due to security violation
        assert execution_result.status == ExecutionStatus.SECURITY_VIOLATION
        assert len(execution_result.security_violations) > 0
    
    @pytest.mark.asyncio
    async def test_execute_code_with_syntax_error(self, code_sandbox):
        """Test execution of code with syntax errors."""
        await code_sandbox.initialize()
        
        invalid_code = '''
def broken_function(
    print("Missing closing parenthesis")
'''
        
        execution_result = await code_sandbox.execute_code(invalid_code)
        
        assert execution_result.status == ExecutionStatus.SYNTAX_ERROR
        assert "syntax" in execution_result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_code_with_runtime_error(self, code_sandbox):
        """Test execution of code with runtime errors."""
        await code_sandbox.initialize()
        
        error_code = '''
x = 10 / 0  # Division by zero
'''
        
        execution_result = await code_sandbox.execute_code(error_code)
        
        assert execution_result.status == ExecutionStatus.RUNTIME_ERROR
        assert "division by zero" in execution_result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_code_timeout(self, code_sandbox):
        """Test execution timeout."""
        await code_sandbox.initialize()
        
        # Create environment with very short timeout
        await code_sandbox.create_sandbox_environment(
            "timeout_test",
            SandboxMode.RESTRICTED,
            SandboxLimits(max_execution_time=0.1)  # 100ms timeout
        )
        
        infinite_loop_code = '''
while True:
    pass  # Infinite loop
'''
        
        execution_result = await code_sandbox.execute_code(
            infinite_loop_code, 
            environment_id="timeout_test"
        )
        
        assert execution_result.status == ExecutionStatus.TIMEOUT
        assert "timed out" in execution_result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_create_custom_sandbox_environment(self, code_sandbox):
        """Test creation of custom sandbox environments."""
        await code_sandbox.initialize()
        
        success = await code_sandbox.create_sandbox_environment(
            "custom_env",
            SandboxMode.LIMITED,
            SandboxLimits(max_execution_time=15.0, max_memory_mb=150),
            allowed_modules=["math", "json", "datetime"],
            blocked_modules=["os", "sys"]
        )
        
        assert success
        assert "custom_env" in code_sandbox.environments
        
        env = code_sandbox.environments["custom_env"]
        assert env.mode == SandboxMode.LIMITED
        assert env.limits.max_execution_time == 15.0
        assert env.limits.max_memory_mb == 150
        assert "math" in env.allowed_modules
        assert "os" in env.blocked_modules
    
    @pytest.mark.asyncio
    async def test_test_code_modification(self, code_sandbox):
        """Test code modification testing functionality."""
        await code_sandbox.initialize()
        
        original_code = '''
def add_numbers(a, b):
    return a + b

result = add_numbers(5, 3)
print(result)
'''
        
        modified_code = '''
def add_numbers(a, b):
    return a + b + 1  # Modified to add 1

result = add_numbers(5, 3)
print(result)
'''
        
        test_cases = [
            {
                "input": {},
                "expected_output": "8"  # Original would output 8, modified would output 9
            }
        ]
        
        test_results = await code_sandbox.test_code_modification(
            original_code, modified_code, test_cases
        )
        
        assert "modification_safe" in test_results
        assert "all_tests_passed" in test_results
        assert "original_results" in test_results
        assert "modified_results" in test_results
        assert len(test_results["original_results"]) == 1
        assert len(test_results["modified_results"]) == 1
    
    @pytest.mark.asyncio
    async def test_safe_module_imports(self, code_sandbox):
        """Test that safe modules can be imported."""
        await code_sandbox.initialize()
        
        # Create environment that allows math module
        await code_sandbox.create_sandbox_environment(
            "math_env",
            SandboxMode.LIMITED,
            allowed_modules=["math"]
        )
        
        math_code = '''
import math
result = math.sqrt(16)
print(f"Square root: {result}")
'''
        
        execution_result = await code_sandbox.execute_code(
            math_code, 
            environment_id="math_env"
        )
        
        assert execution_result.status == ExecutionStatus.SUCCESS
        assert "Square root: 4.0" in execution_result.stdout
    
    @pytest.mark.asyncio
    async def test_blocked_module_imports(self, code_sandbox):
        """Test that blocked modules cannot be imported."""
        await code_sandbox.initialize()
        
        # Try to import a blocked module
        blocked_import_code = '''
import os
os.system("echo 'This should be blocked'")
'''
        
        execution_result = await code_sandbox.execute_code(blocked_import_code)
        
        assert execution_result.status == ExecutionStatus.SECURITY_VIOLATION
        assert "import" in execution_result.error_message.lower()
    
    def test_restricted_builtins(self):
        """Test restricted builtins configuration."""
        safe_builtins = RestrictedBuiltins.SAFE_BUILTINS
        dangerous_builtins = RestrictedBuiltins.DANGEROUS_BUILTINS
        
        # Check that safe builtins include basic operations
        assert "len" in safe_builtins
        assert "str" in safe_builtins
        assert "int" in safe_builtins
        assert "list" in safe_builtins
        
        # Check that dangerous builtins are properly identified
        assert "eval" in dangerous_builtins
        assert "exec" in dangerous_builtins
        assert "open" in dangerous_builtins
        assert "__import__" in dangerous_builtins
        
        # Ensure no overlap between safe and dangerous
        assert len(safe_builtins.intersection(dangerous_builtins)) == 0
    
    @pytest.mark.asyncio
    async def test_execution_history_tracking(self, code_sandbox):
        """Test that execution history is properly tracked."""
        await code_sandbox.initialize()
        
        # Execute several pieces of code
        codes = [
            "print('Test 1')",
            "print('Test 2')",
            "print('Test 3')"
        ]
        
        for code in codes:
            await code_sandbox.execute_code(code)
        
        history = code_sandbox.get_execution_history()
        
        assert len(history) == 3
        assert all(isinstance(result, ExecutionResult) for result in history)
        assert all(result.status == ExecutionStatus.SUCCESS for result in history)
    
    @pytest.mark.asyncio
    async def test_sandbox_statistics(self, code_sandbox):
        """Test sandbox statistics tracking."""
        await code_sandbox.initialize()
        
        # Execute some code to generate statistics
        await code_sandbox.execute_code("print('Success')")
        await code_sandbox.execute_code("eval('malicious')")  # Should fail
        
        stats = code_sandbox.get_sandbox_statistics()
        
        assert "total_executions" in stats
        assert "successful_executions" in stats
        assert "failed_executions" in stats
        assert "security_violations" in stats
        assert stats["total_executions"] == 2
        assert stats["successful_executions"] == 1
        assert stats["security_violations"] == 1
    
    @pytest.mark.asyncio
    async def test_output_size_limiting(self, code_sandbox):
        """Test that output size is limited."""
        await code_sandbox.initialize()
        
        # Create environment with small output limit
        await code_sandbox.create_sandbox_environment(
            "limited_output",
            SandboxMode.RESTRICTED,
            SandboxLimits(max_output_size=50)
        )
        
        large_output_code = '''
for i in range(100):
    print(f"Line {i}: This is a long line of text that should be truncated")
'''
        
        execution_result = await code_sandbox.execute_code(
            large_output_code,
            environment_id="limited_output"
        )
        
        assert execution_result.status == ExecutionStatus.SUCCESS
        assert len(execution_result.stdout) <= 50
    
    @pytest.mark.asyncio
    async def test_concurrent_executions(self, code_sandbox):
        """Test concurrent code executions."""
        await code_sandbox.initialize()
        
        # Create multiple execution tasks
        codes = [
            "import time; time.sleep(0.1); print('Task 1')",
            "import time; time.sleep(0.1); print('Task 2')",
            "import time; time.sleep(0.1); print('Task 3')"
        ]
        
        # Note: The current implementation may not support true concurrency
        # due to Python's GIL, but we can test the interface
        tasks = [code_sandbox.execute_code(code) for code in codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that all executions completed
        assert len(results) == 3
        for result in results:
            if isinstance(result, ExecutionResult):
                # Some may succeed if they can import time, others may fail due to restrictions
                assert result.status in [ExecutionStatus.SUCCESS, ExecutionStatus.SECURITY_VIOLATION]


class TestSandboxSecurity:
    """Test cases for sandbox security features."""
    
    @pytest.fixture
    def mock_code_analyzer(self):
        """Create a mock code analyzer."""
        analyzer = Mock(spec=CodeAnalyzer)
        return analyzer
    
    @pytest.fixture
    def code_sandbox(self, mock_code_analyzer):
        """Create a CodeSandbox instance for testing."""
        return CodeSandbox("security_test", mock_code_analyzer)
    
    @pytest.mark.asyncio
    async def test_block_file_operations(self, code_sandbox):
        """Test that file operations are blocked."""
        await code_sandbox.initialize()
        
        file_operation_code = '''
with open("/etc/passwd", "r") as f:
    content = f.read()
print(content)
'''
        
        execution_result = await code_sandbox.execute_code(file_operation_code)
        
        assert execution_result.status == ExecutionStatus.SECURITY_VIOLATION
    
    @pytest.mark.asyncio
    async def test_block_system_calls(self, code_sandbox):
        """Test that system calls are blocked."""
        await code_sandbox.initialize()
        
        system_call_code = '''
import os
os.system("ls -la")
'''
        
        execution_result = await code_sandbox.execute_code(system_call_code)
        
        assert execution_result.status == ExecutionStatus.SECURITY_VIOLATION
    
    @pytest.mark.asyncio
    async def test_block_subprocess_calls(self, code_sandbox):
        """Test that subprocess calls are blocked."""
        await code_sandbox.initialize()
        
        subprocess_code = '''
import subprocess
subprocess.run(["echo", "hello"])
'''
        
        execution_result = await code_sandbox.execute_code(subprocess_code)
        
        assert execution_result.status == ExecutionStatus.SECURITY_VIOLATION
    
    @pytest.mark.asyncio
    async def test_block_network_access(self, code_sandbox):
        """Test that network access is blocked."""
        await code_sandbox.initialize()
        
        network_code = '''
import urllib.request
response = urllib.request.urlopen("http://example.com")
'''
        
        execution_result = await code_sandbox.execute_code(network_code)
        
        assert execution_result.status == ExecutionStatus.SECURITY_VIOLATION
    
    @pytest.mark.asyncio
    async def test_block_dangerous_builtins(self, code_sandbox):
        """Test that dangerous builtins are blocked."""
        await code_sandbox.initialize()
        
        dangerous_codes = [
            "eval('print(\"dangerous\")')",
            "exec('print(\"dangerous\")')",
            "__import__('os')",
            "compile('print(\"dangerous\")', '<string>', 'exec')"
        ]
        
        for dangerous_code in dangerous_codes:
            execution_result = await code_sandbox.execute_code(dangerous_code)
            assert execution_result.status == ExecutionStatus.SECURITY_VIOLATION
    
    @pytest.mark.asyncio
    async def test_allow_safe_operations(self, code_sandbox):
        """Test that safe operations are allowed."""
        await code_sandbox.initialize()
        
        safe_codes = [
            "result = len([1, 2, 3, 4, 5]); print(result)",
            "text = str(42); print(text)",
            "numbers = list(range(5)); print(numbers)",
            "total = sum([1, 2, 3, 4, 5]); print(total)"
        ]
        
        for safe_code in safe_codes:
            execution_result = await code_sandbox.execute_code(safe_code)
            assert execution_result.status == ExecutionStatus.SUCCESS


# Integration tests
class TestSandboxIntegration:
    """Integration tests for sandbox with other components."""
    
    @pytest.mark.asyncio
    async def test_sandbox_with_code_analyzer_integration(self):
        """Test sandbox integration with code analyzer."""
        # Create real code analyzer
        code_analyzer = CodeAnalyzer("integration_test")
        await code_analyzer.initialize()
        
        # Create sandbox with real analyzer
        sandbox = CodeSandbox("integration_test", code_analyzer)
        await sandbox.initialize()
        
        try:
            # Test safe code
            safe_code = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(5)
print(f"Fibonacci(5) = {result}")
'''
            
            execution_result = await sandbox.execute_code(safe_code)
            assert execution_result.status == ExecutionStatus.SUCCESS
            assert "Fibonacci(5) = 5" in execution_result.stdout
            
            # Test dangerous code
            dangerous_code = '''
import os
def dangerous_function():
    os.system("echo 'This should be blocked'")
    return "done"

result = dangerous_function()
print(result)
'''
            
            execution_result = await sandbox.execute_code(dangerous_code)
            assert execution_result.status == ExecutionStatus.SECURITY_VIOLATION
            
        finally:
            await code_analyzer.shutdown()
            await sandbox.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])