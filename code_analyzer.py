import os
import sys
import ast
import regex as re
from collections import namedtuple


class CodeAnalyzer:
    def __init__(self, path: str):
        self.files: list[str] = self.load_dir(path)
        self.file: str = ''
        self.tree: ast.Module = ast.parse('')
        self.lines: list[str] = []
        self.line_num: int = 0
        self.line: str = ''
        self.issue_template = namedtuple('Issue', ['file', 'line_num', 'code', 'message'])
        self.issues: list = []
        self.line_checks = (
            self.check_length,
            self.check_indent,
            self.check_semicolon,
            self.check_inline,
            self.check_todo,
            self.check_blank_lines,
            self.check_space_class_def,
        )
        self.analyze()

    def __str__(self) -> str:
        return '\n'.join([f'{issue.file}: Line {issue.line_num}: {issue.code} {issue.message}'
                          for issue in sorted(self.issues)])

    @staticmethod
    def load_dir(path: str) -> list[str]:
        if os.path.isfile(path):
            return [path]
        if os.path.isdir(path):
            file_list = []
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.py'):
                        file_list.append(os.path.join(root, file))
            if len(file_list) == 0:
                raise ValueError('No files to check')
            return sorted(file_list)
        raise ValueError(f'{path} is not a file or a directory.')

    def load_file(self):
        assert os.path.isfile(self.file), f'{self.file} is not a file.'
        with open(self.file) as file:
            source = file.read()
            self.lines = source.rstrip().split('\n')
            self.tree = ast.parse(source)

    def issue_append(self, line_num: int, code: str, message: str):
        self.issues.append(self.issue_template(file=self.file,
                                               line_num=line_num,
                                               code=code,
                                               message=message))

    # check methods return a string if issue is found, else ''
    def check_length(self) -> None:
        code, message = 'S001', 'Too long'
        if len(self.line) > 79:
            self.issue_append(self.line_num, code, message)

    def check_indent(self) -> None:
        code, message = 'S002', 'Indentation is not a multiple of 4'
        if re.match(r'\s*', self.line).end() % 4 != 0:
            self.issue_append(self.line_num, code, message)

    def check_semicolon(self) -> None:
        code, message = 'S003', 'Unnecessary semicolon'
        if re.match(r'^[^#]*;\s*(#.*)?$', self.line):
            self.issue_append(self.line_num, code, message)

    def check_inline(self) -> None:
        code, message = 'S004', 'At least two spaces required before inline comments'
        if re.match(r'^[^#]*\S ?#', self.line):
            self.issue_append(self.line_num, code, message)

    def check_todo(self) -> None:
        code, message = 'S005', 'TODO found'
        if re.match(r'^[^#]*#.*todo', self.line, re.IGNORECASE):
            self.issue_append(self.line_num, code, message)

    def check_blank_lines(self) -> None:
        code, message = 'S006', 'More than two blank lines used before this line'
        line_index = self.line_num - 1
        if (line_index >= 3
                and self.lines[line_index].strip()
                and not ''.join(self.lines[line_index - 3: line_index]).strip()):
            self.issue_append(self.line_num, code, message)

    def check_space_class_def(self) -> None:
        code, message = "S007", "Too many spaces after '{name}'"
        match = re.match(r'^\s*(class|def)\s{2,}', self.line)
        if match:
            name = match.groups()[0]
            self.issue_append(self.line_num, code, message.format(name=name))

    def analyze(self):
        for self.file in self.files:
            self.load_file()
            self.analyze_lines()
            self.analyze_tree()

    def analyze_lines(self):
        for self.line_num, self.line in enumerate(self.lines, start=1):
            for check in self.line_checks:
                check()

    @staticmethod
    def is_not_snake(name: str):
        return bool(re.match(r'\w*\p{lu}\w*', name))

    @staticmethod
    def is_not_camel(name: str):
        return bool(re.match(r'\P{lu}\w*|\w*_\w*', name))

    def analyze_tree(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):

                # check class name case
                if self.is_not_camel(node.name):
                    code, message = 'S008', f"Class name '{node.name}' should use CamelCase"
                    self.issue_append(node.lineno, code, message)
            elif isinstance(node, ast.FunctionDef):

                # check function name case
                if self.is_not_snake(node.name):
                    code, message = 'S009', f"Function name '{node.name}' should use snake_case"
                    self.issue_append(node.lineno, code, message)

                # check argument name case
                for arg in node.args.args:
                    arg_name = arg.arg
                    if self.is_not_snake(arg_name):
                        code, message = 'S010', f"Argument name '{arg_name}' should use snake_case"
                        self.issue_append(node.lineno, code, message)

                # check variable name case
                for inner_node in ast.walk(node):
                    if isinstance(inner_node, ast.Name):
                        var_name = inner_node.id
                        if isinstance(inner_node.ctx, ast.Store) and self.is_not_snake(var_name):
                            code, message = 'S011', f"Variable name '{var_name}' in function should use snake_case"
                            self.issue_append(inner_node.lineno, code, message)

                # check for mutable default value
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Set, ast.Dict)):
                        code, message = 'S012', "Default argument value is mutable"
                        self.issue_append(node.lineno, code, message)
                        break


def main():
    assert len(sys.argv) > 1, "Path to a file or a directory required."
    file_path = sys.argv[1]
    analyzer = CodeAnalyzer(file_path)
    print(analyzer)


if __name__ == '__main__':
    main()
