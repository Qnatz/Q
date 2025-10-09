# test_fixes.py
import sys
import os
sys.path.append('/root/Q')

from tools.tool_registry import ToolRegistry
from tools.builtin_tools.file_operation_tool import FileOperationTool

def test_file_operations():
    """Test that file operations work correctly"""
    registry = ToolRegistry()
    
    # Test writing a file
    test_content = "Test content"
    write_result = registry.execute_tool(
        'file_operation',
        parameters={
            'operation': 'write',
            'path': '/tmp/test_file.txt',
            'content': test_content,
            'overwrite': True
        }
    )
    
    print(f"Write result: {write_result.status}, {write_result.error_message}")
    
    # Test reading the file
    read_result = registry.execute_tool(
        'file_operation',
        parameters={
            'operation': 'read', 
            'path': '/tmp/test_file.txt'
        }
    )
    
    print(f"Read result: {read_result.status}, {read_result.error_message}")
    if read_result.status.name == 'SUCCESS':
        print(f"File content: {read_result.result.get('content', 'No content')}")
    
    return write_result.status.name == 'SUCCESS' and read_result.status.name == 'SUCCESS'

if __name__ == "__main__":
    success = test_file_operations()
    print(f"Test {'PASSED' if success else 'FAILED'}")
