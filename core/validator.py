# core/validator.py
"""
Code Validator for Physics Sandbox
Validates AI-generated JavaScript code for security and correctness.
"""

import re
import ast
from typing import Dict, List, Tuple


class PhysicsCodeValidator:
    """
    Validates Three.js + Cannon-es code for security and correctness.
    """
    
    # Whitelist of allowed globals and functions
    WHITELISTED_GLOBALS = {
        # Three.js
        'THREE', 'Scene', 'PerspectiveCamera', 'WebGLRenderer',
        'SphereGeometry', 'BoxGeometry', 'PlaneGeometry', 'CylinderGeometry',
        'MeshStandardMaterial', 'MeshPhongMaterial', 'MeshBasicMaterial',
        'Mesh', 'Vector3', 'Color', 'AmbientLight', 'DirectionalLight',
        'PointLight', 'HemisphereLight', 'OrbitControls', 'Clock',
        
        # Cannon-es
        'CANNON', 'World', 'Body', 'Sphere', 'Box', 'Plane', 'Cylinder',
        'NaiveBroadphase', 'SAPBroadphase', 'PointToPointConstraint',
        'DistanceConstraint', 'Spring', 'ContactMaterial', 'Material',
        'Vec3', 'Quaternion',
        
        # JavaScript built-ins
        'console', 'window', 'document', 'Math', 'Date', 'Array', 'Object',
        'Number', 'String', 'Boolean', 'parseInt', 'parseFloat', 'isNaN',
        'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
        'requestAnimationFrame', 'XMLHttpRequest', 'JSON', 'eval',
        
        # Common utilities
        'alert', 'confirm', 'prompt',
    }
    
    # Blocked patterns (security risks)
    BLOCKED_PATTERNS = [
        (r'eval\s*\(', "eval() is not allowed"),
        (r'Function\s*\(', "Function constructor is not allowed"),
        (r'document\.cookie', "Access to cookies is not allowed"),
        (r'document\.domain', "Access to domain is not allowed"),
        (r'fetch\s*\(', "Network requests are not allowed"),
        (r'XMLHttpRequest', "XMLHttpRequest is not allowed"),
        (r'location\.href', "Direct navigation is not allowed"),
        (r'location\.replace', "Navigation is not allowed"),
        (r'import\s*\(', "Dynamic imports are not allowed"),
        (r'require\s*\(', "require() is not allowed"),
        (r'delete\s+', "Object deletion is not allowed"),
        (r'__proto__', "Proto access is not allowed"),
        (r'constructor\s*\[', "Constructor access is not allowed"),
        (r'with\s*\(', "with statement is not allowed"),
        (r' debugger;', "Debugger statements are not allowed"),
        (r'\.innerHTML\s*=', "innerHTML manipulation is restricted"),
    ]
    
    # Resource limits
    MAX_OBJECT_CREATIONS = 20
    MAX_LINE_LENGTH = 1000
    MAX_NESTING_DEPTH = 5
    
    def __init__(self):
        self.issues = []
    
    def validate(self, code: str) -> Dict:
        """
        Validate code for security and correctness.
        
        Args:
            code: JavaScript code to validate
            
        Returns:
            dict with keys: valid, issues, security_level, suggestions
        """
        self.issues = []
        
        if not code or not code.strip():
            return {
                "valid": False,
                "issues": ["No code provided"],
                "security_level": "none",
                "suggestions": ["Please provide code to validate"]
            }
        
        # Basic checks
        self._check_syntax(code)
        self._check_blocked_patterns(code)
        self._check_resource_limits(code)
        self._check_threejs_requirements(code)
        self._check_cannon_requirements(code)
        
        security_level = self._calculate_security_level()
        
        return {
            "valid": len(self.issues) == 0,
            "issues": self.issues,
            "security_level": security_level,
            "suggestions": self._get_suggestions(),
            "stats": {
                "lines": len(code.split('\n')),
                "object_creations": self._count_object_creations(code),
                "functions": len(re.findall(r'function\s+\w+', code)),
            }
        }
    
    def _check_syntax(self, code: str) -> None:
        """Check for basic JavaScript syntax issues."""
        # Check for balanced braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            self.issues.append(f"Unbalanced braces: {{ = {open_braces}, }} = {close_braces}")
        
        # Check for balanced parentheses
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            self.issues.append(f"Unbalanced parentheses: ( = {open_parens}, ) = {close_parens}")
        
        # Check for balanced brackets
        open_brackets = code.count('[')
        close_brackets = code.count(']')
        if open_brackets != close_brackets:
            self.issues.append(f"Unbalanced brackets: [ = {open_brackets}, ] = {close_brackets}")
    
    def _check_blocked_patterns(self, code: str) -> None:
        """Check for blocked security patterns."""
        for pattern, message in self.BLOCKED_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                self.issues.append(message)
    
    def _check_resource_limits(self, code: str) -> None:
        """Check against resource limits."""
        lines = code.split('\n')
        
        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > self.MAX_LINE_LENGTH:
                self.issues.append(f"Line {i} exceeds maximum length ({len(line)} > {self.MAX_LINE_LENGTH})")
                break
        
        # Check nesting depth
        max_nesting = self._calculate_nesting_depth(lines)
        if max_nesting > self.MAX_NESTING_DEPTH:
            self.issues.append(f"Nesting depth ({max_nesting}) exceeds maximum ({self.MAX_NESTING_DEPTH})")
        
        # Check object creations
        object_count = self._count_object_creations(code)
        if object_count > self.MAX_OBJECT_CREATIONS:
            self.issues.append(f"Too many object creations ({object_count} > {self.MAX_OBJECT_CREATIONS})")
    
    def _check_threejs_requirements(self, code: str) -> None:
        """Check for required Three.js components."""
        required = [
            ('THREE\\.Scene', 'THREE.Scene creation'),
            ('THREE\\.(PerspectiveCamera|OrthographicCamera)', 'Camera setup'),
            ('THREE\\.WebGLRenderer', 'WebGLRenderer creation'),
            ('requestAnimationFrame', 'Animation loop'),
        ]
        
        for pattern, requirement in required:
            if not re.search(pattern, code):
                self.issues.append(f"Missing {requirement}")
    
    def _check_cannon_requirements(self, code: str) -> None:
        """Check for physics simulation requirements."""
        # Physics is optional, so this is a warning, not an error
        if 'CANNON' not in code and 'CANNON' not in code:
            # Check if physics is expected based on scene description
            if 'gravity' in code.lower() or 'physics' in code.lower():
                self.issues.append("Physics mentioned but Cannon-es not detected")
    
    def _count_object_creations(self, code: str) -> int:
        """Count Three.js object creations."""
        patterns = [
            r'new\s+THREE\.\w+Geometry',
            r'new\s+THREE\.\w+Material',
            r'new\s+THREE\.Mesh',
            r'new\s+CANNON\.\w+',
            r'new\s+THREE\.\w+Light',
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, code))
        
        return count
    
    def _calculate_nesting_depth(self, lines: List[str]) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        current_depth = 0
        
        for line in lines:
            # Remove strings to avoid false positives
            line = re.sub(r'"[^"]*"|\'[^\']*\'', '', line)
            
            current_depth += line.count('{') - line.count('}')
            current_depth += line.count('(') - line.count(')')
            current_depth += line.count('[') - line.count(']')
            
            max_depth = max(max_depth, abs(current_depth))
        
        return max_depth
    
    def _calculate_security_level(self) -> str:
        """Calculate security level based on issues."""
        if not self.issues:
            return "high"
        elif len(self.issues) <= 2:
            return "medium"
        else:
            return "low"
    
    def _get_suggestions(self) -> List[str]:
        """Get suggestions for fixing issues."""
        suggestions = []
        
        for issue in self.issues:
            if "Unbalanced" in issue:
                suggestions.append("Check your braces, parentheses, and brackets")
            elif "Missing" in issue:
                suggestions.append("Ensure all required Three.js components are included")
            elif "Too many" in issue:
                suggestions.append("Reduce the number of objects in your scene")
            elif "depth" in issue:
                suggestions.append("Reduce nesting by breaking code into functions")
        
        return suggestions
    
    def whitelist_function(self, func_name: str) -> bool:
        """
        Add a function to the whitelist.
        
        Args:
            func_name: Name of function to whitelist
            
        Returns:
            True if added successfully
        """
        if func_name and isinstance(func_name, str):
            self.WHITELISTED_GLOBALS.add(func_name)
            return True
        return False
    
    def add_blocked_pattern(self, pattern: str, message: str) -> bool:
        """
        Add a new blocked pattern.
        
        Args:
            pattern: Regex pattern to block
            message: Error message for this pattern
            
        Returns:
            True if added successfully
        """
        if pattern and message:
            self.BLOCKED_PATTERNS.append((pattern, message))
            return True
        return False
