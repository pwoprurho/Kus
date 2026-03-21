# scripts/audit_skills.py
import os
import re
import sys
import subprocess

# Vulnerability Patterns
SHELL_PATTERNS = [
    r"os\.system\(",
    r"subprocess\.Popen\(.*shell=True",
    r"subprocess\.call\(.*shell=True",
    r"subprocess\.run\(.*shell=True",
    r"eval\(",
    r"exec\(",
]

DANGEROUS_COMMANDS = [
    r"/bin/sh",
    r"/bin/bash",
    r"curl.*\|.*sh",
    r"wget.*\|.*sh",
    r"rm -rf /",
    r"chmod 777",
]

def audit_file(filepath):
    """Scan a file for dangerous patterns."""
    findings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # 1. Check for Python shell patterns
            if filepath.endswith('.py'):
                for pattern in SHELL_PATTERNS:
                    if re.search(pattern, content):
                        findings.append(f"Potential Unsafe Execution: {pattern}")
            
            # 2. Check for dangerous shell commands (Markdown/Scripts)
            for cmd in DANGEROUS_COMMANDS:
                if re.search(cmd, content, re.IGNORECASE):
                    findings.append(f"Dangerous Command Match: {cmd}")
                    
    except Exception as e:
        findings.append(f"Audit Error: {str(e)}")
        
    return findings

def audit_directory(root_path):
    """Audit all files in the registry."""
    print(f"--- Starting Security Audit: {root_path} ---")
    total_files = 0
    total_findings = 0
    
    for root, _, files in os.walk(root_path):
        for file in files:
            if file.startswith('.') or 'node_modules' in root or '.git' in root:
                continue
                
            filepath = os.path.join(root, file)
            total_files += 1
            findings = audit_file(filepath)
            
            if findings:
                total_findings += 1
                print(f"[!] {filepath}")
                for f in findings:
                    print(f"    - {f}")
                    
    print(f"\nAudit Complete: {total_files} files scanned, {total_findings} flagged.")
    return total_findings

if __name__ == "__main__":
    hub_path = sys.argv[1] if len(sys.argv) > 1 else "C:\\Users\\Administrator\\kus\\kushub"
    
    # 1. Pattern Scan
    findings_count = audit_directory(hub_path)
    
    # 2. Bandit Scan (if available)
    try:
        print("\n--- Running Bandit Static Analysis ---")
        subprocess.run(["bandit", "-r", hub_path, "-f", "screen"], check=False)
    except FileNotFoundError:
        print("[Note] Bandit not installed. Skipping static analysis phase.")
    
    if findings_count > 0:
        sys.exit(1)
    sys.exit(0)
