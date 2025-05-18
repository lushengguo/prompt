import re
import json
from collections import defaultdict


class VariableType:
    def __init__(self, type_):
        self.type_ = type_.strip()

    def is_pod(self):
        # Very basic check, you can expand this list
        pod_types = {'int', 'float', 'double', 'bool', 'char', 'short', 'long', 'unsigned', 'const char*'}
        return any(self.type_.startswith(pod) for pod in pod_types)

    def is_template(self):
        return re.match(r'^\w+<.+>$', self.type_) is not None

    def template_type(self):
        if self.is_template():
            return re.findall(r'<(.+)>', self.type_)[0]
        return None

    def __repr__(self):
        return self.type_


class StructDescription:
    def __init__(self):
        self.variables = {}

    def add_variable(self, name, vtype):
        self.variables[name] = VariableType(vtype)


class GlobalStructs:
    structs = {}

    @classmethod
    def add_struct(cls, name, struct_desc):
        cls.structs[name] = struct_desc

    @classmethod
    def to_json(cls):
        return json.dumps({k: {vn: str(vt) for vn, vt in v.variables.items()} for k, v in cls.structs.items()}, indent=4)

    @classmethod
    def print_readable(cls):
        for sname, sdesc in cls.structs.items():
            print(f"Struct: {sname}")
            for vname, vtype in sdesc.variables.items():
                print(f"  {vname}: {vtype}")
            print()


def remove_comments(code):
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    return code


def retrieve_structs_from_cpp_header(cpp_header):
    GlobalStructs.structs.clear()
    cpp_header = remove_comments(cpp_header)

    # Match struct definitions
    struct_pattern = re.compile(r'struct\s+(\w+)\s*\{([^}]*)\}', re.MULTILINE | re.DOTALL)
    for struct_name, body in struct_pattern.findall(cpp_header):
        struct_desc = StructDescription()

        # Extract variable declarations inside struct body
        for line in body.split(';'):
            line = line.strip()
            if not line:
                continue
            parts = line.rsplit(' ', 1)
            if len(parts) != 2:
                continue
            vtype, vname = parts
            vtype = vtype.strip()
            vname = vname.strip()
            struct_desc.add_variable(vname, vtype)

        GlobalStructs.add_struct(struct_name, struct_desc)

    return GlobalStructs


if __name__ == "__main__":
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

    retrieve_structs_from_cpp_header(cpp_header)
    print("JSON Output:")
    print(GlobalStructs.to_json())
    print("\nReadable Output:")
    GlobalStructs.print_readable()
