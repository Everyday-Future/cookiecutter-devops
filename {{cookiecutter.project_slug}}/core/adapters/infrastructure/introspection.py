# core/adapters/infrastructure/introspection.py
import os
import ast
import logging
import pathspec
from PIL import Image
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, field

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('IntrospectionAdapter')


@dataclass
class IntrospectionConfig:
    """Configuration for codebase introspection"""
    exclude_dirs: List[str] = field(default_factory=lambda: [
        'venv', 'env', 'node_modules', '.next', '.git',
        '__pycache__', '.pytest_cache', 'build', 'dist',
        'data', 'docs'
    ])
    include_extensions: List[str] = field(default_factory=lambda: [
        '.py', '.ts', '.tsx', '.js', '.jsx', '.yml', '.yaml'
    ])
    exclude_extensions: List[str] = field(default_factory=lambda: [
        '.png', '.jpg', '.jpeg', '.gif', '.bmp',
        '.svg', '.ico', '.webp',  # image files
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',  # document files
        '.zip', '.tar', '.gz', '.rar',  # archive files
        '.exe', '.dll', '.so', '.dylib',  # binary files
        '.ttf', '.woff', '.woff2',  # font files
    ])
    max_import_depth: int = 3
    code_dirs: List[str] = field(default_factory=lambda: ['api', 'core', 'frontend'])


class IntrospectionAdapter:
    """Unified adapter for codebase introspection functionality"""

    def __init__(self, root_dir: Union[str, Path], config: Optional[IntrospectionConfig] = None):
        self.root_dir = Path(root_dir)
        self.config = config or IntrospectionConfig()
        self._gitignore_spec = self._parse_gitignore()
        self._execution_stats = {}

    def _parse_gitignore(self) -> pathspec.PathSpec:
        """Parse .gitignore patterns"""
        gitignore_path = self.root_dir / '.gitignore'
        if not gitignore_path.exists():
            return pathspec.PathSpec([])

        with open(gitignore_path, 'r') as f:
            gitignore = f.read().splitlines()

        return pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern,
            gitignore
        )

    def _is_ignored(self, path: Union[str, Path]) -> bool:
        """Check if a path should be ignored"""
        path = Path(path)
        rel_path = str(path.relative_to(self.root_dir))

        # Check excluded directories
        for excluded in self.config.exclude_dirs:
            if excluded in path.parts:
                return True

        # Check file extension
        if path.is_file():
            ext = path.suffix.lower()
            if self.config.include_extensions and ext not in self.config.include_extensions:
                return True
            if ext in self.config.exclude_extensions:
                return True

        # Check gitignore patterns
        return self._gitignore_spec.match_file(rel_path)

    def catalog_routes(self) -> Dict[str, List[str]]:
        """
        Catalog both Next.js and Flask routes in the project
        Returns:
            Dict with 'nextjs' and 'flask' route lists
        """
        nextjs_routes = []
        flask_routes = []

        # Find Next.js routes
        app_dir = self.root_dir / 'frontend' / 'app'
        if app_dir.exists():
            for root, _, files in os.walk(app_dir):
                if any(f in files for f in ['page.js', 'page.tsx', 'page.jsx']):
                    rel_path = os.path.relpath(root, app_dir)
                    route = '/' + str(rel_path).replace(os.path.sep, '/')
                    if rel_path == '.':
                        route = '/'
                    nextjs_routes.append(route)

        # Find Flask routes
        api_dir = self.root_dir / 'api'
        if api_dir.exists():
            for root, _, files in os.walk(api_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = Path(root) / file
                        if self._is_ignored(file_path):
                            continue

                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                tree = ast.parse(f.read())

                            for node in ast.walk(tree):
                                if isinstance(node, ast.FunctionDef):
                                    for decorator in node.decorator_list:
                                        if isinstance(decorator, ast.Call) and \
                                                hasattr(decorator.func, 'attr') and \
                                                decorator.func.attr == 'route':
                                            route_path = decorator.args[0].s if decorator.args else ''
                                            methods = ['GET']  # default
                                            for kw in decorator.keywords:
                                                if kw.arg == 'methods':
                                                    methods = [m.s for m in kw.value.elts]
                                            flask_routes.append(f"{route_path} {methods} {node.name}()")
                        except Exception as e:
                            logger.warning(f"Error processing {file_path}: {str(e)}")

        return {
            'nextjs': sorted(nextjs_routes),
            'flask': sorted(flask_routes)
        }

    def count_lines_of_code(self) -> Dict:
        """Count lines of code in the project"""
        total_lines = 0
        lines_by_extension = {}
        files_processed = 0

        for root, _, files in os.walk(self.root_dir):
            root_path = Path(root)
            if self._is_ignored(root_path):
                continue

            for file in files:
                file_path = root_path / file
                if self._is_ignored(file_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_lines = sum(1 for line in f if line.strip())
                        ext = file_path.suffix.lower()

                        total_lines += file_lines
                        lines_by_extension[ext] = lines_by_extension.get(ext, 0) + file_lines
                        files_processed += 1

                except (UnicodeDecodeError, PermissionError):
                    continue

        return {
            'total_lines': total_lines,
            'files_processed': files_processed,
            'lines_by_extension': dict(sorted(
                lines_by_extension.items(),
                key=lambda x: x[1],
                reverse=True
            ))
        }

    @staticmethod
    def generate_icon_set(source_icon: Union[str, Path], output_dir: Union[str, Path],
                          sizes: Optional[List[int]] = None):
        """Generate a set of icons in different sizes"""
        source_path = Path(source_icon)
        output_path = Path(output_dir)

        if not source_path.exists():
            raise FileNotFoundError(f"Source icon not found: {source_path}")

        if sizes is None:
            sizes = [72, 96, 128, 144, 152, 192, 384, 512]

        output_path.mkdir(parents=True, exist_ok=True)

        with Image.open(source_path) as img:
            for size in sizes:
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                output_file = output_path / f"icon-{size}x{size}.png"
                resized.save(output_file, "PNG", optimize=True)
                logger.info(f"Generated {size}x{size} icon: {output_file}")

    def get_directory_tree(self, start_path: Optional[Union[str, Path]] = None,
                           max_depth: int = -1,
                           dirs_only: bool = False) -> Tuple[str, Dict]:
        """Generate a directory tree structure"""
        start_path = Path(start_path or self.root_dir)
        tree_lines = []
        stats = {'directories': 0, 'files': 0}

        def _inner(path: Path, prefix: str = '', depth: int = max_depth):
            if depth == 0:
                return

            try:
                contents = sorted(
                    path.iterdir(),
                    key=lambda x: (not x.is_dir(), x.name.lower())
                )
                filtered_contents = [
                    p for p in contents
                    if not self._is_ignored(p) and (p.is_dir() or not dirs_only)
                ]

                if depth != 0:  # Only process contents if not at max depth
                    for i, item in enumerate(filtered_contents):
                        is_last = i == len(filtered_contents) - 1
                        marker = '└── ' if is_last else '├── '
                        tree_lines.append(prefix + marker + item.name)

                        if item.is_dir():
                            stats['directories'] += 1
                            next_prefix = prefix + ('    ' if is_last else '│   ')
                            _inner(item, next_prefix, depth - 1 if depth > 0 else depth)
                        else:
                            stats['files'] += 1

            except PermissionError:
                logger.warning(f"Permission denied: {path}")

        tree_lines.append(start_path.name)
        _inner(start_path)

        return '\n'.join(tree_lines), stats

    def label_files(self, target_folders: Optional[List[str]] = None) -> Tuple[int, List[str]]:
        """Label all code files with their paths"""
        if target_folders is None:
            target_folders = self.config.code_dirs

        files_processed = 0
        follow_up_list = []

        def _process_file(file_path: Path) -> bool:
            if self._is_ignored(file_path):
                return False

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.readlines()

                rel_path = str(file_path.relative_to(self.root_dir))
                comment_char = '//' if file_path.suffix in ['.tsx', '.ts', '.js', '.jsx'] else '#'
                new_label = f"{comment_char} {rel_path}\n"

                # Update or add the label
                if content and (content[0].startswith('#') or content[0].startswith('//')):
                    content[0] = new_label
                else:
                    content.insert(0, new_label)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(content)
                return True

            except Exception as e:
                logger.warning(f"Error processing {file_path}: {str(e)}")
                follow_up_list.append(str(file_path))
                return False

        # Process top-level files
        for file_path in self.root_dir.glob('*'):
            if file_path.is_file() and file_path.suffix in self.config.include_extensions:
                if _process_file(file_path):
                    files_processed += 1

        # Process files in target folders
        for folder in target_folders:
            folder_path = self.root_dir / folder
            if not folder_path.exists():
                continue

            for file_path in folder_path.rglob('*'):
                if file_path.is_file() and file_path.suffix in self.config.include_extensions:
                    if _process_file(file_path):
                        files_processed += 1

        return files_processed, follow_up_list

    def get_execution_stats(self) -> Dict:
        """Get execution statistics"""
        return self._execution_stats
