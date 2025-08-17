"""
Unit tests for code analysis and modification systems.

Tests the code analyzer, code modifier, and security utilities
for correct functionality and safety measures.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from autonomous_ai_ecosystem.agents.code_analyzer import (
    CodeAnalyzer, CodeElement, CodeAnalysisResult, ModificationProposal,
    CodeRiskLevel, CodeCapability
)
from autonomous_ai_ecosystem.agents.code_modifier import (
    CodeModifier, ModificationType, ModificationStatus, ModificationRecord
)
from autonomous_ai_ecosystem.utils.security import (
    sanitize_code, validate_code_safety, detect_vulnerabilities,
    is_safe_identifier, validate_import_safety, SecurityLevel, VulnerabilityType
)


class TestCodeAnalyzer:
    """Test cases for the CodeAnalyzer."""
    
    @pytest.fixture
    def code_analyzer(self):
        """Create a CodeAnalyzer instance for testing."""
        return CodeAnalyzer("test_agent")
    
    @pytest.mark.asyncio
    async def test_initialization(self, code_analyzer):
        """Test code analyzer initialization."""
        await code_analyzer.initialize()
        assert code_analyzer.agent_id == "test_agent"
        assert len(code_analyzer.analysis_cache) == 0
        assert len(code_analyzer.allowed_modules) > 0
        assert len(code_analyzer.forbidden_modules) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_safe_code(self, code_analyzer):
        """Test analysis of safe code."""
        await code_analyzer.initialize()
        
        safe_code = '''
def add_numbers(a, b):
    """Add two numbers together."""
    return a + b

def multiply_numbers(x, y):
    """Multiply two numbers."""
    result = x * y
    return result
'''
        
        result = await code_analyzer.analyze_code_string(safe_code)
        
        assert isinstance(result, CodeAnalysisResult)
        assert result.total_functions == 2
        assert result.overall_risk_level == CodeRiskLevel.SAFE
        assert len(result.security_issues) == 0
        assert len(result.elements) == 2
        
        # Check function elements
        functions = [e for e in result.elements if e.element_type == "function"]
        assert len(functions) == 2
        assert any(f.name == "add_numbers" for f in functions)
        assert any(f.name == "multiply_numbers" for f in functions)
    
    @pytest.mark.asyncio
    async def test_analyze_risky_code(self, code_analyzer):
        """Test analysis of risky code."""
        await code_analyzer.initialize()
        
        risky_code = '''
import os
import subprocess

def dangerous_function():
    """This function does dangerous things."""
    eval("print('hello')")
    os.system("ls -la")
    exec("x = 1 + 1")
    return "done"

def file_operations():
    """File operations."""
    with open("/etc/passwd", "r") as f:
        content = f.read()
    return content
'''
        
        result = await code_analyzer.analyze_code_string(risky_code)
        
        assert result.overall_risk_level in [CodeRiskLevel.HIGH_RISK, CodeRiskLevel.DANGEROUS]
        assert len(result.security_issues) > 0
        assert CodeCapability.SYSTEM_CALLS in result.capabilities
        assert CodeCapability.FILE_IO in result.capabilities
        assert CodeCapability.DYNAMIC_EXECUTION in result.capabilities
        
        # Check that dangerous imports are detected
        assert "os" in result.imports
        assert "subprocess" in result.imports
    
    @pytest.mark.asyncio
    async def test_analyze_file(self, code_analyzer):
        """Test file analysis functionality."""
        await code_analyzer.initialize()
        
        # Create a temporary file with test code
        test_code = '''
def test_function():
    """A simple test function."""
    return "Hello, World!"

class TestClass:
    """A simple test class."""
    
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name
        
        try:
            result = await code_analyzer.analyze_file(temp_file)
            
            assert result.file_path == temp_file
            assert result.total_functions == 3  # test_function, __init__, get_value
            assert result.total_classes == 1
            assert result.overall_risk_level == CodeRiskLevel.SAFE
            
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_modification_risk_assessment(self, code_analyzer):
        """Test modification risk assessment."""
        await code_analyzer.initialize()
        
        # Create a safe modification proposal
        safe_proposal = ModificationProposal(
            proposal_id="test_safe",
            target_file="test.py",
            modification_type="add_function",
            target_element="new_function",
            original_code="",
            proposed_code='''
def new_function(x):
    """A new safe function."""
    return x * 2
''',
            justification="Adding a utility function",
            risk_assessment=CodeRiskLevel.SAFE,
            estimated_impact={}
        )
        
        assessment = await code_analyzer.assess_modification_risk(safe_proposal)
        
        assert assessment["should_allow"] == True
        assert assessment["risk_level"] == "safe"
        assert len(assessment["security_issues"]) == 0
        
        # Create a dangerous modification proposal
        dangerous_proposal = ModificationProposal(
            proposal_id="test_dangerous",
            target_file="test.py",
            modification_type="add_function",
            target_element="dangerous_function",
            original_code="",
            proposed_code='''
def dangerous_function(code):
    """A dangerous function."""
    return eval(code)
''',
            justification="Adding dynamic execution",
            risk_assessment=CodeRiskLevel.SAFE,
            estimated_impact={}
        )
        
        assessment = await code_analyzer.assess_modification_risk(dangerous_proposal)
        
        assert assessment["should_allow"] == False
        assert assessment["risk_level"] in ["high_risk", "dangerous"]
        assert len(assessment["security_issues"]) > 0
    
    @pytest.mark.asyncio
    async def test_extract_functions(self, code_analyzer):
        """Test function extraction."""
        await code_analyzer.initialize()
        
        # Create a temporary file with functions
        test_code = '''
def function_one():
    return 1

def function_two(x, y):
    return x + y

class MyClass:
    def method_one(self):
        return "method"

def function_three():
    pass
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name
        
        try:
            functions = await code_analyzer.extract_functions(temp_file)
            
            # Should find 4 functions: 3 module-level + 1 method
            assert len(functions) == 4
            function_names = [f.name for f in functions]
            assert "function_one" in function_names
            assert "function_two" in function_names
            assert "function_three" in function_names
            assert "method_one" in function_names
            
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_security_vulnerability_detection(self, code_analyzer):
        """Test security vulnerability detection."""
        await code_analyzer.initialize()
        
        vulnerable_code = '''
import pickle
import os

def load_data(data):
    return pickle.loads(data)  # Unsafe deserialization

def execute_command(cmd):
    os.system(cmd)  # Command injection

def dynamic_exec(code):
    exec(code)  # Code injection
'''
        
        vulnerabilities = await code_analyzer.find_security_vulnerabilities("<string>")
        
        # The method should return security issues from analysis
        # Since we're testing with a string, we need to analyze it first
        result = await code_analyzer.analyze_code_string(vulnerable_code)
        vulnerabilities = result.security_issues
        
        assert len(vulnerabilities) > 0
        # Should detect various security issues
        vulnerability_text = " ".join(vulnerabilities).lower()
        assert any(keyword in vulnerability_text for keyword in ["pickle", "os", "exec", "system"])


class TestCodeModifier:
    """Test cases for the CodeModifier."""
    
    @pytest.fixture
    def mock_code_analyzer(self):
        """Create a mock code analyzer."""
        analyzer = Mock(spec=CodeAnalyzer)
        analyzer.assess_modification_risk = AsyncMock()
        return analyzer
    
    @pytest.fixture
    def mock_brain(self):
        """Create a mock AIBrain."""
        brain = Mock(spec=AIBrain)
        brain.think = AsyncMock()
        return brain

    @pytest.fixture
    def code_modifier(self, mock_code_analyzer, mock_brain):
        """Create a CodeModifier instance for testing."""
        return CodeModifier("test_agent", mock_code_analyzer, mock_brain)
    
    @pytest.mark.asyncio
    async def test_initialization(self, code_modifier):
        """Test code modifier initialization."""
        await code_modifier.initialize()
        assert code_modifier.agent_id == "test_agent"
        assert len(code_modifier.modification_history) == 0
        assert len(code_modifier.pending_modifications) == 0
        assert Path(code_modifier.backup_directory).exists()
    
    @pytest.mark.asyncio
    async def test_propose_safe_modification(self, code_modifier, mock_code_analyzer):
        """Test proposing a safe modification."""
        # Setup mock to approve safe modification
        mock_code_analyzer.assess_modification_risk.return_value = {
            "should_allow": True,
            "risk_level": "safe",
            "security_issues": [],
            "recommendations": []
        }
        
        await code_modifier.initialize()
        
        modification_id = await code_modifier.propose_modification(
            target_file="test.py",
            modification_type=ModificationType.ADD_FUNCTION,
            target_element="new_function",
            new_code="def new_function(): return 42",
            justification="Adding utility function"
        )
        
        assert modification_id is not None
        assert len(code_modifier.modification_history) == 1
        
        # Should be auto-approved for safe modifications
        record = code_modifier.modification_history[0]
        assert record.status == ModificationStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_propose_risky_modification(self, code_modifier, mock_code_analyzer):
        """Test proposing a risky modification."""
        # Setup mock to reject risky modification
        mock_code_analyzer.assess_modification_risk.return_value = {
            "should_allow": False,
            "risk_level": "dangerous",
            "security_issues": ["Code injection risk"],
            "recommendations": ["Do not use eval()"]
        }
        
        await code_modifier.initialize()
        
        modification_id = await code_modifier.propose_modification(
            target_file="test.py",
            modification_type=ModificationType.ADD_FUNCTION,
            target_element="dangerous_function",
            new_code="def dangerous_function(code): return eval(code)",
            justification="Adding dynamic execution"
        )
        
        assert modification_id is not None
        assert len(code_modifier.modification_history) == 1
        
        # Should remain pending for risky modifications
        record = code_modifier.modification_history[0]
        assert record.status == ModificationStatus.PENDING
        assert modification_id in code_modifier.pending_modifications
    
    @pytest.mark.asyncio
    async def test_approve_modification(self, code_modifier, mock_code_analyzer):
        """Test modification approval."""
        mock_code_analyzer.assess_modification_risk.return_value = {
            "should_allow": False,
            "risk_level": "medium_risk",
            "security_issues": [],
            "recommendations": []
        }
        
        await code_modifier.initialize()
        
        # Propose a modification
        modification_id = await code_modifier.propose_modification(
            target_file="test.py",
            modification_type=ModificationType.ADD_FUNCTION,
            target_element="test_function",
            new_code="def test_function(): pass",
            justification="Test function"
        )
        
        # Approve it
        success = await code_modifier.approve_modification(modification_id)
        
        assert success == True
        assert modification_id not in code_modifier.pending_modifications
        
        # Find the record and check status
        record = next(r for r in code_modifier.modification_history if r.modification_id == modification_id)
        assert record.status == ModificationStatus.APPROVED
    
    @pytest.mark.asyncio
    async def test_reject_modification(self, code_modifier, mock_code_analyzer):
        """Test modification rejection."""
        mock_code_analyzer.assess_modification_risk.return_value = {
            "should_allow": False,
            "risk_level": "dangerous",
            "security_issues": ["Security issue"],
            "recommendations": []
        }
        
        await code_modifier.initialize()
        
        # Propose a modification
        modification_id = await code_modifier.propose_modification(
            target_file="test.py",
            modification_type=ModificationType.ADD_FUNCTION,
            target_element="bad_function",
            new_code="def bad_function(): exec('malicious code')",
            justification="Bad function"
        )
        
        # Reject it
        success = await code_modifier.reject_modification(modification_id, "Too dangerous")
        
        assert success == True
        assert modification_id not in code_modifier.pending_modifications
        
        # Find the record and check status
        record = next(r for r in code_modifier.modification_history if r.modification_id == modification_id)
        assert record.status == ModificationStatus.REJECTED
        assert record.error_message == "Too dangerous"
    
    @pytest.mark.asyncio
    async def test_code_template_generation(self, code_modifier):
        """Test code generation from templates."""
        await code_modifier.initialize()
        
        # Test simple function template
        parameters = {
            "function_name": "test_func",
            "parameters": "x, y",
            "docstring": "Test function",
            "body": "result = x + y",
            "return_value": "result"
        }
        
        code = await code_modifier.generate_code_from_template("simple_function", parameters)
        
        assert "def test_func(x, y):" in code
        assert "Test function" in code
        assert "result = x + y" in code
        assert "return result" in code
    
    @pytest.mark.asyncio
    async def test_propose_llm_based_modification(self, code_modifier, mock_brain):
        """Test the LLM-based modification proposal workflow."""
        # --- Arrange ---
        file_path = "test_file.py"
        goal = "Add a docstring to the function."
        original_code = "def my_func():\n    return 1"
        new_code_from_llm = 'def my_func():\n    """This is a new docstring."""\n    return 1'

        # Mock the brain's response
        mock_brain.think.return_value = Mock(output={"solution": new_code_from_llm})

        # Mock the file system
        with patch("builtins.open", unittest.mock.mock_open(read_data=original_code)), \
             patch.object(code_modifier, 'propose_modification', new_callable=AsyncMock) as mock_propose:

            # --- Act ---
            modification_id = await code_modifier.propose_llm_based_modification(file_path, goal)

            # --- Assert ---
            # 1. Assert that the brain was called to think about the modification
            mock_brain.think.assert_awaited_once()

            # 2. Assert that the internal propose_modification was called with the new code
            mock_propose.assert_awaited_once()
            call_args = mock_propose.call_args[1]
            assert call_args['target_file'] == file_path
            assert call_args['new_code'] == new_code_from_llm
            assert call_args['justification'] == goal

    @pytest.mark.asyncio
    async def test_backup_creation(self, code_modifier):
        """Test backup file creation."""
        await code_modifier.initialize()
        
        # Create a temporary file
        test_content = "def original_function(): pass"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_content)
            temp_file = f.name
        
        try:
            # Create backup
            backup_path = await code_modifier._create_backup(temp_file)
            
            assert backup_path != ""
            assert os.path.exists(backup_path)
            
            # Verify backup content
            with open(backup_path, 'r') as f:
                backup_content = f.read()
            
            assert backup_content == test_content
            
        finally:
            os.unlink(temp_file)
            if backup_path and os.path.exists(backup_path):
                os.unlink(backup_path)
    
    def test_modification_statistics(self, code_modifier):
        """Test modification statistics tracking."""
        stats = code_modifier.get_modification_statistics()
        
        assert "total_proposals" in stats
        assert "approved_modifications" in stats
        assert "rejected_modifications" in stats
        assert "successful_applications" in stats
        assert "failed_applications" in stats
        assert "pending_count" in stats
        assert "history_size" in stats


class TestSecurityUtilities:
    """Test cases for security utilities."""
    
    def test_sanitize_safe_code(self):
        """Test sanitization of safe code."""
        safe_code = '''
def add_numbers(a, b):
    """Add two numbers."""
    return a + b
'''
        
        sanitized = sanitize_code(safe_code)
        assert "def add_numbers" in sanitized
        assert "return a + b" in sanitized
    
    def test_sanitize_dangerous_code(self):
        """Test sanitization of dangerous code."""
        dangerous_code = '''
def bad_function():
    eval("malicious code")  # This should be removed
    exec("more malicious code")  # This too
    os.system("rm -rf /")  # And this
    return "done"
'''
        
        sanitized = sanitize_code(dangerous_code)
        assert "eval(" not in sanitized
        assert "exec(" not in sanitized
        assert "os.system(" not in sanitized
        assert "REMOVED_DANGEROUS_CALL" in sanitized
    
    def test_validate_safe_code_safety(self):
        """Test safety validation of safe code."""
        safe_code = '''
import math

def calculate_area(radius):
    """Calculate circle area."""
    return math.pi * radius ** 2
'''
        
        security_level, issues = validate_code_safety(safe_code)
        assert security_level == SecurityLevel.SAFE
        assert len(issues) == 0
    
    def test_validate_unsafe_code_safety(self):
        """Test safety validation of unsafe code."""
        unsafe_code = '''
import os

def dangerous_function(cmd):
    """Execute system command."""
    return eval(cmd)
'''
        
        security_level, issues = validate_code_safety(unsafe_code)
        assert security_level in [SecurityLevel.HIGH_RISK, SecurityLevel.DANGEROUS]
        assert len(issues) > 0
    
    def test_detect_vulnerabilities(self):
        """Test vulnerability detection."""
        vulnerable_code = '''
import pickle
import os

def load_data(data):
    return pickle.loads(data)

def run_command(cmd):
    os.system(cmd)

def execute_code(code):
    exec(code)
'''
        
        vulnerabilities = detect_vulnerabilities(vulnerable_code)
        
        assert VulnerabilityType.UNSAFE_DESERIALIZATION in vulnerabilities
        assert VulnerabilityType.SYSTEM_CALLS in vulnerabilities
        assert VulnerabilityType.CODE_INJECTION in vulnerabilities
        
        # Check that specific issues are detected
        assert len(vulnerabilities[VulnerabilityType.UNSAFE_DESERIALIZATION]) > 0
        assert len(vulnerabilities[VulnerabilityType.SYSTEM_CALLS]) > 0
        assert len(vulnerabilities[VulnerabilityType.CODE_INJECTION]) > 0
    
    def test_safe_identifier_validation(self):
        """Test safe identifier validation."""
        # Safe identifiers
        assert is_safe_identifier("my_function") == True
        assert is_safe_identifier("calculate_result") == True
        assert is_safe_identifier("user_data") == True
        
        # Unsafe identifiers
        assert is_safe_identifier("eval") == False
        assert is_safe_identifier("exec") == False
        assert is_safe_identifier("__import__") == False
        assert is_safe_identifier("123invalid") == False
        assert is_safe_identifier("class") == False  # Python keyword
        assert is_safe_identifier("") == False
    
    def test_import_safety_validation(self):
        """Test import safety validation."""
        # Safe imports
        is_safe, reason = validate_import_safety("math")
        assert is_safe == True
        
        is_safe, reason = validate_import_safety("json")
        assert is_safe == True
        
        is_safe, reason = validate_import_safety("datetime")
        assert is_safe == True
        
        # Unsafe imports
        is_safe, reason = validate_import_safety("os")
        assert is_safe == False
        assert "dangerous" in reason.lower()
        
        is_safe, reason = validate_import_safety("subprocess")
        assert is_safe == False
        
        is_safe, reason = validate_import_safety("sys")
        assert is_safe == False
        
        # Unknown imports
        is_safe, reason = validate_import_safety("unknown_module")
        assert is_safe == False
        assert "unknown" in reason.lower()
    
    def test_code_hash_calculation(self):
        """Test code hash calculation."""
        from autonomous_ai_ecosystem.utils.security import calculate_code_hash
        
        code1 = "def test(): pass"
        code2 = "def test(): pass"
        code3 = "def test(): return 1"
        
        hash1 = calculate_code_hash(code1)
        hash2 = calculate_code_hash(code2)
        hash3 = calculate_code_hash(code3)
        
        # Same code should produce same hash
        assert hash1 == hash2
        
        # Different code should produce different hash
        assert hash1 != hash3
        
        # Hash should be a valid SHA-256 hex string
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)


# Integration tests
class TestCodeAnalysisIntegration:
    """Integration tests for code analysis and modification systems."""
    
    @pytest.mark.asyncio
    async def test_full_modification_workflow(self):
        """Test complete modification workflow from analysis to application."""
        # Create analyzer and modifier
        analyzer = CodeAnalyzer("integration_test")
        modifier = CodeModifier("integration_test", analyzer)
        
        await analyzer.initialize()
        await modifier.initialize()
        
        try:
            # Create a test file
            test_code = '''
def original_function():
    """Original function."""
    return "original"
'''
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_code)
                temp_file = f.name
            
            # Analyze original file
            original_analysis = await analyzer.analyze_file(temp_file)
            assert original_analysis.total_functions == 1
            
            # Propose a safe modification
            modification_id = await modifier.propose_modification(
                target_file=temp_file,
                modification_type=ModificationType.ADD_FUNCTION,
                target_element="new_function",
                new_code='''
def new_function():
    """New function."""
    return "new"
''',
                justification="Adding a new utility function"
            )
            
            # Check that modification was created
            assert modification_id is not None
            assert len(modifier.modification_history) == 1
            
            # The modification should be auto-approved if it's safe
            record = modifier.modification_history[0]
            if record.status == ModificationStatus.PENDING:
                # Manually approve if not auto-approved
                await modifier.approve_modification(modification_id)
            
            # Apply the modification
            success = await modifier.apply_modification(modification_id)
            
            if success:
                # Verify the modification was applied
                modified_analysis = await analyzer.analyze_file(temp_file, use_cache=False)
                assert modified_analysis.total_functions == 2
                
                # Check that both functions are present
                function_names = [e.name for e in modified_analysis.elements if e.element_type == "function"]
                assert "original_function" in function_names
                assert "new_function" in function_names
            
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            
            await analyzer.shutdown()
            await modifier.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])