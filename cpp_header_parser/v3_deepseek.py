import re
import json
from collections import defaultdict

class VariableType:
    def __init__(self, type_str):
        self.type_ = type_str.strip()

    def is_pod(self):
        pod_types = {'int', 'float', 'double', 'char', 'bool', 'short', 'long', 
                    'unsigned', 'signed', 'void', 'size_t', 'uint8_t', 'int8_t', 
                    'uint16_t', 'int16_t', 'uint32_t', 'int32_t', 'uint64_t', 'int64_t'}
        return any(pod_type in self.type_ for pod_type in pod_types)

    def is_template(self):
        return '<' in self.type_ and '>' in self.type_

    def template_type(self):
        if self.is_template():
            start = self.type_.find('<') + 1
            end = self.type_.rfind('>')
            return self.type_[start:end].strip()
        return None


class StructDescription:
    def __init__(self):
        self.variables = {}

    def add_variable(self, name, type_str):
        self.variables[name] = VariableType(type_str)


class GlobalStructs:
    def __init__(self):
        self.structs = {}

    def add_struct(self, name, description):
        self.structs[name] = description

    def to_dict(self):
        result = {}
        for struct_name, struct_desc in self.structs.items():
            result[struct_name] = {var_name: var_type.type_ 
                                 for var_name, var_type in struct_desc.variables.items()}
        return result


def remove_comments(text):
    # Remove all /* */ comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Remove all // comments
    text = re.sub(r'//.*?\n', '\n', text)
    return text


def remove_namespaces(text):
    """Remove namespace declarations while preserving their content and struct definitions"""
    lines = text.split('\n')
    result = []
    namespace_depth = 0
    
    for line in lines:
        # Check for namespace opening
        if re.match(r'\s*namespace\s+\w+\s*{', line):
            namespace_depth += 1
            continue
        
        # Check for closing brace that matches namespace
        if namespace_depth > 0 and '}' in line:
            # Count closing braces
            close_braces = line.count('}')
            if close_braces >= namespace_depth:
                line = line.replace('}', '', namespace_depth)
                namespace_depth = 0
            else:
                namespace_depth -= close_braces
                line = line.replace('}', '', close_braces)
        
        if namespace_depth == 0:
            result.append(line)
    
    return '\n'.join(result)


def retrieve_structs_from_cpp_header(cpp_header):
    global_structs = GlobalStructs()
    
    # Remove comments first
    cpp_header = remove_comments(cpp_header)
    
    # Remove namespaces carefully
    cpp_header = remove_namespaces(cpp_header)
    
    # Remove preprocessor directives
    cpp_header = re.sub(r'^\s*#.*$', '', cpp_header, flags=re.MULTILINE)
    
    # Remove enum definitions
    cpp_header = re.sub(r'enum\s+(class\s+)?\w+\s*{[^}]*};', '', cpp_header, flags=re.DOTALL)
    
    # Remove typedefs and using aliases
    cpp_header = re.sub(r'(typedef|using)\s+.*?;', '', cpp_header, flags=re.DOTALL)
    
    # First remove all nested struct definitions but keep their names
    nested_structs = set()
    def replace_nested(match):
        nested_structs.add(match.group(1))
        return ''  # Remove the nested struct definition
    
    # Temporarily remove nested structs while preserving top-level ones
    temp_header = re.sub(
        r'struct\s+(\w+)\s*{[^}]*}\s*(?=.*?struct\s+\w+\s*{[^}]*};)', 
        replace_nested, 
        cpp_header,
        flags=re.DOTALL
    )
    
    # Now find all top-level structs
    struct_pattern = re.compile(
        r'struct\s+(\w+)\s*{([^}]*)};',
        re.DOTALL
    )
    
    for match in struct_pattern.finditer(temp_header):
        struct_name = match.group(1).strip()
        struct_body = match.group(2).strip()
        
        struct_desc = StructDescription()
        
        # Process each field declaration
        field_decls = [f.strip() for f in struct_body.split(';') if f.strip()]
        
        for field in field_decls:
            # Skip lines that don't look like field declarations
            if not field or field.startswith('//') or field.startswith('/*'):
                continue
            
            # Remove inline comments
            field = re.sub(r'//.*$', '', field)
            field = re.sub(r'/\*.*\*/', '', field)
            
            # Remove default initializers
            field = re.sub(r'=\s*[^;]+', '', field)
            
            # Match type and variable name
            var_match = re.match(r'(.+?)\s+(\w+)\s*$', field.strip())
            if var_match:
                type_str = var_match.group(1).strip()
                var_name = var_match.group(2).strip()
                
                # Clean up type string (remove extra spaces)
                type_str = ' '.join(type_str.split())
                
                struct_desc.add_variable(var_name, type_str)
        
        global_structs.add_struct(struct_name, struct_desc)
    
    return global_structs
# The C++ header content
cpp_header = """
// This is a comment at the beginning of the file.

#include <vector>
#include <string>
#include <array>

namespace MyNamespace {

enum class Color {
    RED,
    GREEN,
    BLUE
};

using StringAlias = std::string;

struct InnerStruct {
    int inner_value;
    StringAlias inner_name;
};

struct SampleStruct {
    int id;             // A simple integer
    float value;        /* Another comment */
    bool flag;
    Color color;
    InnerStruct inner_data; // Using the separately defined InnerStruct
    std::vector<int> data_points;
    std::array<float, 3> coordinates;
    StringAlias name;
    unsigned long long counter;
    const char* message;
    ExternalType from_other_header; // Type potentially from another header
};

struct EmptyStruct {};

struct NestedContainerStruct {
    struct ContainedStruct { // Nested named struct
        int x;
        int y;
    };
    ContainedStruct item;
    std::vector<ContainedStruct> items;
};

} // namespace MyNamespace

struct AnotherStruct {
    double pi = 3.14159;
};

#define SOME_CONSTANT 100

// Another comment at the end.
"""

if __name__ == "__main__":
    global_structs = retrieve_structs_from_cpp_header(cpp_header)
    structs_dict = global_structs.to_dict()
    
    # Print JSON output
    print("\nJSON Output:")
    print(json.dumps(structs_dict, indent=2))
    
    # Test cases
    expected_output = {
        "InnerStruct": {
            "inner_value": "int",
            "inner_name": "StringAlias"
        },
        "SampleStruct": {
            "id": "int",
            "value": "float",
            "flag": "bool",
            "color": "Color",
            "inner_data": "InnerStruct",
            "data_points": "std::vector<int>",
            "coordinates": "std::array<float, 3>",
            "name": "StringAlias",
            "counter": "unsigned long long",
            "message": "const char*",
            "from_other_header": "ExternalType"
        },
        "EmptyStruct": {},
        "NestedContainerStruct": {
            "item": "ContainedStruct",
            "items": "std::vector<ContainedStruct>"
        },
        "AnotherStruct": {
            "pi": "double"
        }
    }
    
    print("\nTest Results:")
    print("=" * 40)
    if structs_dict == expected_output:
        print("✅ Output matches expected result!")
    else:
        print("❌ Output does not match expected result!")
        print("\nDifferences:")
        for struct in expected_output:
            if struct not in structs_dict:
                print(f"Missing struct: {struct}")
            elif structs_dict[struct] != expected_output[struct]:
                print(f"Struct {struct} fields differ:")
                print(f"  Expected: {expected_output[struct]}")
                print(f"  Got:      {structs_dict[struct]}")