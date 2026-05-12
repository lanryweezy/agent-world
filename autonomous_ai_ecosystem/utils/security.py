"""
Security utilities for code analysis and validation.

This module provides security-focused utilities for sanitizing code,
validating code safety, and detecting potential security vulnerabilities.
"""

import ast
import re
import keyword
from typing import List, Dict, Tuple
from enum import Enum
import hashlib


class SecurityLevel(Enum):
    """Security levels for code validation."""
    SAFE = "safe"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    DANGEROUS = "dangerous"


class VulnerabilityType(Enum):
    """Types of security vulnerabilities."""
    CODE_INJECTION = "code_injection"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    UNSAFE_DESERIALIZATION = "unsafe_deserialization"
    DANGEROUS_IMPORTS = "dangerous_imports"
    DYNAMIC_EXECUTION = "dynamic_execution"
    FILE_SYSTEM_ACCESS = "file_system_access"
    NETWORK_ACCESS = "network_access"
    SYSTEM_CALLS = "system_calls"
    REFLECTION_ABUSE = "reflection_abuse"


def sanitize_code(code: str) -> str:
    """
    Sanitize code by removing potentially dangerous elements.
    
    Args:
        code: Raw code string to sanitize
        
    Returns:
        Sanitized code string
    """
    if not code:
        return ""
    
    # Remove comments that might contain injection attempts
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    
    # Remove dangerous function calls
    dangerous_patterns = [
        r'\beval\s*\(',
        r'\bexec\s*\(',
        r'\b__import__\s*\(',
        r'\bcompile\s*\(',
        r'\bopen\s*\([^)]*["\'][wax]',  # File writes/appends
        r'\bos\.system\s*\(',
        r'\bsubprocess\.',
        r'\bshutil\.rmtree\s*\(',
    ]
    
    for pattern in dangerous_patterns:
        code = re.sub(pattern, '# REMOVED_DANGEROUS_CALL', code, flags=re.IGNORECASE)
    
    # Limit string length to prevent buffer overflow attempts
    max_string_length = 10000
    if len(code) > max_string_length:
        code = code[:max_string_length] + "\n# CODE_TRUNCATED_FOR_SAFETY"
    
    return code


def validate_code_safety(code: str) -> Tuple[SecurityLevel, List[str]]:
    """
    Validate code safety and return security level with issues found.
    
    Args:
        code: Code string to validate
        
    Returns:
        Tuple of (SecurityLevel, list of security issues)
    """
    if not code:
        return SecurityLevel.SAFE, []
    
    issues = []
    security_level = SecurityLevel.SAFE
    
    try:
        # Parse the code to AST
        tree = ast.parse(code)
        
        # Analyze the AST for security issues
        analyzer = SecurityAnalyzer()
        analyzer.visit(tree)
        
        issues.extend(analyzer.security_issues)
        security_level = analyzer.overall_security_level
        
    except SyntaxError as e:
        issues.append(f"Syntax error: {e}")
        security_level = SecurityLevel.HIGH_RISK
    except Exception as e:
        issues.append(f"Analysis error: {e}")
        security_level = SecurityLevel.MEDIUM_RISK
    
    # Additional string-based checks
    string_issues, string_level = _check_string_patterns(code)
    issues.extend(string_issues)
    
    # Take the higher security level
    if string_level.value > security_level.value:
        security_level = string_level
    
    return security_level, issues


def detect_vulnerabilities(code: str) -> Dict[VulnerabilityType, List[str]]:
    """
    Detect specific types of vulnerabilities in code.
    
    Args:
        code: Code string to analyze
        
    Returns:
        Dictionary mapping vulnerability types to lists of specific issues
    """
    vulnerabilities = {}
    
    try:
        tree = ast.parse(code)
        detector = VulnerabilityDetector()
        detector.visit(tree)
        vulnerabilities.update(detector.vulnerabilities)
    except:
        pass  # Continue with string-based detection
    
    # String-based vulnerability detection
    string_vulns = _detect_string_vulnerabilities(code)
    
    # Merge results
    for vuln_type, issues in string_vulns.items():
        if vuln_type in vulnerabilities:
            vulnerabilities[vuln_type].extend(issues)
        else:
            vulnerabilities[vuln_type] = issues
    
    return vulnerabilities


def is_safe_identifier(name: str) -> bool:
    """
    Check if an identifier is safe to use.
    
    Args:
        name: Identifier name to check
        
    Returns:
        True if the identifier is safe
    """
    if not name or not isinstance(name, str):
        return False
    
    # Check if it's a valid Python identifier
    if not name.isidentifier():
        return False
    
    # Check if it's a Python keyword
    if keyword.iskeyword(name):
        return False
    
    # Check for dangerous patterns
    dangerous_patterns = [
        '__',  # Dunder methods can be dangerous
        'eval',
        'exec',
        'compile',
        'import',
        'open',
        'file',
        'input',
        'raw_input'
    ]
    
    name_lower = name.lower()
    for pattern in dangerous_patterns:
        if pattern in name_lower:
            return False
    
    return True


def calculate_code_hash(code: str) -> str:
    """
    Calculate a hash of the code for integrity checking.
    
    Args:
        code: Code string to hash
        
    Returns:
        SHA-256 hash of the code
    """
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def validate_import_safety(module_name: str) -> Tuple[bool, str]:
    """
    Validate if an import is safe.
    
    Args:
        module_name: Name of the module to import
        
    Returns:
        Tuple of (is_safe, reason)
    """
    if not module_name:
        return False, "Empty module name"
    
    # Allowed modules (safe standard library modules)
    safe_modules = {
        'math', 'random', 'datetime', 'json', 'typing', 'dataclasses',
        'enum', 'collections', 'itertools', 'functools', 'operator',
        'copy', 'uuid', 'hashlib', 'base64', 'urllib.parse', 'decimal',
        'fractions', 'statistics', 'string', 're', 'textwrap'
    }
    
    # Dangerous modules
    dangerous_modules = {
        'os', 'sys', 'subprocess', 'shutil', 'glob', 'tempfile',
        'socket', 'urllib.request', 'http', 'ftplib', 'smtplib',
        'eval', 'exec', 'compile', '__import__', 'importlib',
        'ctypes', 'multiprocessing', 'threading', 'pickle',
        'marshal', 'shelve', 'dbm'
    }
    
    # Check exact matches first
    if module_name in safe_modules:
        return True, "Module is in safe list"
    
    if module_name in dangerous_modules:
        return False, f"Module '{module_name}' is potentially dangerous"
    
    # Check for dangerous patterns
    dangerous_patterns = ['os.', 'sys.', 'subprocess.', '__']
    for pattern in dangerous_patterns:
        if pattern in module_name:
            return False, f"Module contains dangerous pattern: {pattern}"
    
    # Unknown modules are medium risk
    return False, f"Unknown module '{module_name}' - requires manual review"


class SecurityAnalyzer(ast.NodeVisitor):
    """AST visitor for security analysis."""
    
    def __init__(self):
        self.security_issues = []
        self.overall_security_level = SecurityLevel.SAFE
        self.dangerous_calls = set()
        self.imports = set()
    
    def visit_Call(self, node):
        """Visit function calls."""
        func_name = self._get_function_name(node)
        
        if func_name:
            # Check for dangerous function calls
            dangerous_functions = {
                'eval': SecurityLevel.DANGEROUS,
                'exec': SecurityLevel.DANGEROUS,
                'compile': SecurityLevel.DANGEROUS,
                '__import__': SecurityLevel.DANGEROUS,
                'getattr': SecurityLevel.HIGH_RISK,
                'setattr': SecurityLevel.HIGH_RISK,
                'delattr': SecurityLevel.HIGH_RISK,
                'globals': SecurityLevel.HIGH_RISK,
                'locals': SecurityLevel.HIGH_RISK,
                'vars': SecurityLevel.HIGH_RISK,
                'open': SecurityLevel.MEDIUM_RISK,
                'input': SecurityLevel.MEDIUM_RISK,
                'raw_input': SecurityLevel.MEDIUM_RISK
            }
            
            if func_name in dangerous_functions:
                risk_level = dangerous_functions[func_name]
                self.security_issues.append(f"Dangerous function call: {func_name}")
                self.dangerous_calls.add(func_name)
                
                if risk_level.value > self.overall_security_level.value:
                    self.overall_security_level = risk_level
        
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Visit import statements."""
        for alias in node.names:
            module_name = alias.name
            self.imports.add(module_name)
            
            is_safe, reason = validate_import_safety(module_name)
            if not is_safe:
                self.security_issues.append(f"Unsafe import: {module_name} - {reason}")
                if self.overall_security_level == SecurityLevel.SAFE:
                    self.overall_security_level = SecurityLevel.MEDIUM_RISK
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Visit from-import statements."""
        if node.module:
            self.imports.add(node.module)
            
            is_safe, reason = validate_import_safety(node.module)
            if not is_safe:
                self.security_issues.append(f"Unsafe import: {node.module} - {reason}")
                if self.overall_security_level == SecurityLevel.SAFE:
                    self.overall_security_level = SecurityLevel.MEDIUM_RISK
        
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Visit attribute access."""
        # Check for dangerous attribute patterns
        if isinstance(node.value, ast.Name):
            if node.value.id == 'os' and node.attr in ['system', 'popen', 'spawn']:
                self.security_issues.append(f"Dangerous OS operation: os.{node.attr}")
                self.overall_security_level = SecurityLevel.DANGEROUS
        
        self.generic_visit(node)
    
    def _get_function_name(self, node):
        """Extract function name from a call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None


class VulnerabilityDetector(ast.NodeVisitor):
    """AST visitor for specific vulnerability detection."""
    
    def __init__(self):
        self.vulnerabilities = {vuln_type: [] for vuln_type in VulnerabilityType}
    
    def visit_Call(self, node):
        """Visit function calls to detect vulnerabilities."""
        func_name = self._get_function_name(node)
        
        if func_name:
            # Code injection vulnerabilities
            if func_name in ['eval', 'exec', 'compile']:
                self.vulnerabilities[VulnerabilityType.CODE_INJECTION].append(
                    f"Code injection risk: {func_name}() call"
                )
            
            # Dynamic execution
            if func_name in ['eval', 'exec', '__import__']:
                self.vulnerabilities[VulnerabilityType.DYNAMIC_EXECUTION].append(
                    f"Dynamic execution: {func_name}() call"
                )
            
            # File system access
            if func_name in ['open', 'file'] or (
                isinstance(node.func, ast.Attribute) and 
                node.func.attr in ['open', 'remove', 'rmdir', 'mkdir']
            ):
                self.vulnerabilities[VulnerabilityType.FILE_SYSTEM_ACCESS].append(
                    f"File system access: {func_name}() call"
                )
            
            # System calls
            if (isinstance(node.func, ast.Attribute) and 
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'os' and
                node.func.attr in ['system', 'popen', 'spawn']):
                self.vulnerabilities[VulnerabilityType.SYSTEM_CALLS].append(
                    f"System call: os.{node.func.attr}()"
                )
            
            # Command injection
            if func_name in ['system', 'popen'] or 'subprocess' in str(node.func):
                self.vulnerabilities[VulnerabilityType.COMMAND_INJECTION].append(
                    f"Command injection risk: {func_name}() call"
                )
            
            # Reflection abuse
            if func_name in ['getattr', 'setattr', 'delattr', 'hasattr']:
                self.vulnerabilities[VulnerabilityType.REFLECTION_ABUSE].append(
                    f"Reflection usage: {func_name}() call"
                )
        
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Visit imports to detect dangerous modules."""
        for alias in node.names:
            module_name = alias.name
            
            dangerous_modules = {
                'os': VulnerabilityType.SYSTEM_CALLS,
                'sys': VulnerabilityType.SYSTEM_CALLS,
                'subprocess': VulnerabilityType.SYSTEM_CALLS,
                'shutil': VulnerabilityType.SYSTEM_CALLS,
                'socket': VulnerabilityType.NETWORK_ACCESS,
                'urllib': VulnerabilityType.NETWORK_ACCESS,
                'http': VulnerabilityType.NETWORK_ACCESS,
                'pickle': VulnerabilityType.UNSAFE_DESERIALIZATION,
                'marshal': VulnerabilityType.UNSAFE_DESERIALIZATION,
                'shelve': VulnerabilityType.UNSAFE_DESERIALIZATION,
                'ctypes': VulnerabilityType.SYSTEM_CALLS
            }
            
            for dangerous_module, vuln_type in dangerous_modules.items():
                if dangerous_module in module_name:
                    self.vulnerabilities[vuln_type].append(
                        f"Dangerous import: {module_name}"
                    )
        
        self.generic_visit(node)
    
    def _get_function_name(self, node):
        """Extract function name from a call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None


def _check_string_patterns(code: str) -> Tuple[List[str], SecurityLevel]:
    """Check for dangerous patterns in code strings."""
    issues = []
    security_level = SecurityLevel.SAFE
    
    # Dangerous string patterns
    dangerous_patterns = [
        (r'\beval\s*\(', SecurityLevel.DANGEROUS, "eval() function call"),
        (r'\bexec\s*\(', SecurityLevel.DANGEROUS, "exec() function call"),
        (r'\b__import__\s*\(', SecurityLevel.DANGEROUS, "__import__() function call"),
        (r'\bos\.system\s*\(', SecurityLevel.DANGEROUS, "os.system() call"),
        (r'\bsubprocess\.', SecurityLevel.HIGH_RISK, "subprocess module usage"),
        (r'\.\./', SecurityLevel.MEDIUM_RISK, "Path traversal pattern"),
        (r'["\'].*\.\./.*["\']', SecurityLevel.MEDIUM_RISK, "Potential path traversal"),
        (r'pickle\.loads?\s*\(', SecurityLevel.HIGH_RISK, "Unsafe deserialization"),
        (r'marshal\.loads?\s*\(', SecurityLevel.HIGH_RISK, "Unsafe deserialization"),
    ]
    
    for pattern, level, description in dangerous_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(description)
            if level.value > security_level.value:
                security_level = level
    
    return issues, security_level


def _detect_string_vulnerabilities(code: str) -> Dict[VulnerabilityType, List[str]]:
    """Detect vulnerabilities using string pattern matching."""
    vulnerabilities = {vuln_type: [] for vuln_type in VulnerabilityType}
    
    # Pattern-based vulnerability detection
    patterns = {
        VulnerabilityType.CODE_INJECTION: [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'\bcompile\s*\('
        ],
        VulnerabilityType.COMMAND_INJECTION: [
            r'\bos\.system\s*\(',
            r'\bsubprocess\.',
            r'\bpopen\s*\('
        ],
        VulnerabilityType.PATH_TRAVERSAL: [
            r'\.\./',
            r'["\'].*\.\./.*["\']',
            r'["\'].*/etc/passwd.*["\']'
        ],
        VulnerabilityType.UNSAFE_DESERIALIZATION: [
            r'pickle\.loads?\s*\(',
            r'marshal\.loads?\s*\(',
            r'shelve\.open\s*\('
        ],
        VulnerabilityType.DANGEROUS_IMPORTS: [
            r'import\s+os\b',
            r'import\s+sys\b',
            r'import\s+subprocess\b',
            r'from\s+os\s+import',
            r'from\s+sys\s+import'
        ]
    }
    
    for vuln_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                vulnerabilities[vuln_type].extend([
                    f"Pattern match: {match}" for match in matches
                ])
    
    return vulnerabilities