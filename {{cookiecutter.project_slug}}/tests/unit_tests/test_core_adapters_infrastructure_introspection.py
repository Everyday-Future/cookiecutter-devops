import os
import pytest
from pathlib import Path
from PIL import Image
from core.adapters.infrastructure.introspection import IntrospectionAdapter, IntrospectionConfig

# Test Data Constants
TEST_NEXTJS_ROUTES = [
    ('page.tsx', '/'),
    ('about/page.tsx', '/about'),
    ('blog/[slug]/page.tsx', '/blog/[slug]'),
    ('(auth)/login/page.tsx', '/(auth)/login'),
]

TEST_FLASK_ROUTES = [
    '''
@app.route('/api/users', methods=['GET', 'POST'])
def users():
    pass
''',
    '''
@app.route('/api/items/<item_id>')
def get_item(item_id):
    pass
'''
]

TEST_TREE_STRUCTURE = {
    'frontend': {
        'app': {
            'page.tsx': 'export default function Home() {}',
            'about': {
                'page.tsx': 'export default function About() {}'
            }
        },
        'components': {
            'Button.tsx': 'export const Button = () => {}'
        }
    },
    'api': {
        'routes.py': '@app.route("/api/test")\ndef test(): pass',
        'models.py': 'class User: pass'
    },
    'node_modules': {
        'package': {
            'index.js': 'module.exports = {}'
        }
    },
    '.gitignore': '''
node_modules/
__pycache__/
*.pyc
'''
}


@pytest.fixture
def test_config():
    """Fixture for test configuration"""
    return IntrospectionConfig(
        exclude_dirs=['node_modules', '__pycache__'],
        include_extensions=['.py', '.tsx', '.ts'],
        exclude_extensions=['.jpg', '.png'],
        code_dirs=['api', 'frontend']
    )


@pytest.fixture
def test_dir(tmp_path):
    """Fixture to create a temporary test directory with sample files"""

    def create_files(structure, base_path):
        for name, content in structure.items():
            path = base_path / name
            if isinstance(content, dict):
                path.mkdir(exist_ok=True)
                create_files(content, path)
            else:
                path.write_text(content)

    create_files(TEST_TREE_STRUCTURE, tmp_path)
    return tmp_path


@pytest.fixture
def adapter(test_dir, test_config):
    """Fixture to create IntrospectionAdapter instance"""
    return IntrospectionAdapter(test_dir, test_config)


class TestIntrospectionConfig:
    """Tests for IntrospectionConfig class"""

    def test_default_config(self):
        """Test default configuration values"""
        config = IntrospectionConfig()
        assert 'node_modules' in config.exclude_dirs
        assert '.py' in config.include_extensions
        assert '.jpg' in config.exclude_extensions
        assert config.max_import_depth == 3
        assert 'api' in config.code_dirs

    def test_custom_config(self):
        """Test custom configuration values"""
        custom_config = IntrospectionConfig(
            exclude_dirs=['custom_exclude'],
            include_extensions=['.custom'],
            max_import_depth=5
        )
        assert 'custom_exclude' in custom_config.exclude_dirs
        assert '.custom' in custom_config.include_extensions
        assert custom_config.max_import_depth == 5


class TestRouteDiscovery:
    """Tests for route discovery functionality"""

    def test_nextjs_routes(self, adapter):
        """Test Next.js route discovery"""
        routes = adapter.catalog_routes()
        assert '/' in routes['nextjs']
        assert '/about' in routes['nextjs']

    def test_flask_routes(self, adapter):
        """Test Flask route discovery"""
        routes = adapter.catalog_routes()
        assert any('/api/test' in route for route in routes['flask'])

    def test_empty_routes(self, tmp_path, test_config):
        """Test route discovery with empty project"""
        empty_adapter = IntrospectionAdapter(tmp_path, test_config)
        routes = empty_adapter.catalog_routes()
        assert len(routes['nextjs']) == 0
        assert len(routes['flask']) == 0

    def test_malformed_routes(self, test_dir, test_config):
        """Test handling of malformed route definitions"""
        # Create file with syntax error
        bad_route = test_dir / 'api' / 'bad_route.py'
        bad_route.write_text('@app.route("/bad"\ndef broken():')

        adapter = IntrospectionAdapter(test_dir, test_config)
        routes = adapter.catalog_routes()
        assert routes['flask'] is not None  # Should not crash


class TestLinesCounting:
    """Tests for lines of code counting functionality"""

    def test_count_lines(self, adapter):
        """Test basic line counting"""
        stats = adapter.count_lines_of_code()
        assert stats['total_lines'] > 0
        assert stats['files_processed'] > 0
        assert '.tsx' in stats['lines_by_extension']
        assert '.py' in stats['lines_by_extension']

    def test_empty_directory(self, tmp_path, test_config):
        """Test line counting in empty directory"""
        empty_adapter = IntrospectionAdapter(tmp_path, test_config)
        stats = empty_adapter.count_lines_of_code()
        assert stats['total_lines'] == 0
        assert stats['files_processed'] == 0

    def test_excluded_files(self, adapter):
        """Test that excluded files are not counted"""
        stats = adapter.count_lines_of_code()
        excluded_file = adapter.root_dir / 'node_modules' / 'package' / 'index.js'
        assert excluded_file.exists()
        for ext in stats['lines_by_extension']:
            assert not any(f.endswith('.js') for f in stats['lines_by_extension'])


class TestIconGeneration:
    """Tests for icon generation functionality"""

    @pytest.fixture
    def source_icon(self, tmp_path):
        """Fixture to create a test source icon"""
        icon_path = tmp_path / 'source_icon.png'
        img = Image.new('RGB', (512, 512), color='red')
        img.save(icon_path)
        return icon_path

    def test_icon_generation(self, adapter, source_icon, tmp_path):
        """Test basic icon generation"""
        output_dir = tmp_path / 'icons'
        sizes = [16, 32, 64]
        adapter.generate_icon_set(source_icon, output_dir, sizes)

        for size in sizes:
            icon_path = output_dir / f'icon-{size}x{size}.png'
            assert icon_path.exists()
            with Image.open(icon_path) as img:
                assert img.size == (size, size)

    def test_missing_source_icon(self, adapter, tmp_path):
        """Test error handling for missing source icon"""
        with pytest.raises(FileNotFoundError):
            adapter.generate_icon_set(
                tmp_path / 'nonexistent.png',
                tmp_path / 'icons'
            )

    def test_invalid_sizes(self, adapter, source_icon, tmp_path):
        """Test handling of invalid sizes"""
        output_dir = tmp_path / 'icons'
        with pytest.raises(ValueError):
            adapter.generate_icon_set(source_icon, output_dir, sizes=[-1, 0])


class TestDirectoryTree:
    """Tests for directory tree generation functionality"""

    def test_basic_tree(self, adapter):
        """Test basic tree generation"""
        tree, stats = adapter.get_directory_tree()
        assert isinstance(tree, str)
        assert stats['directories'] > 0
        assert stats['files'] > 0
        # Don't test for specific symbols, just ensure directories exist
        assert 'api' in tree
        assert 'frontend' in tree

    def test_max_depth(self, adapter):
        """Test depth limitation"""
        tree, _ = adapter.get_directory_tree(max_depth=1)
        # Count actual directory levels by checking indentation
        lines = [line for line in tree.split('\n') if line.strip()]
        max_indent = max(len(line) - len(line.lstrip()) for line in lines) // 4  # Each level is 4 spaces
        assert max_indent <= 1, f"Tree exceeded max depth: \n{tree}"

    def test_dirs_only(self, adapter):
        """Test directory-only tree"""
        tree, stats = adapter.get_directory_tree(dirs_only=True)
        assert stats['files'] == 0
        assert not any(line.endswith('.py') for line in tree.split('\n'))
        assert not any(line.endswith('.tsx') for line in tree.split('\n'))


class TestFileLabeliing:
    """Tests for file labeling functionality"""

    def test_basic_labeling(self, adapter):
        """Test basic file labeling"""
        files_processed, follow_up = adapter.label_files()
        assert files_processed > 0
        assert len(follow_up) == 0

        # Check if files are correctly labeled
        sample_file = adapter.root_dir / 'api' / 'routes.py'
        with open(sample_file, 'r') as f:
            first_line = f.readline().strip()
            expected_path = str(Path('api/routes.py'))  # Ensure consistent path separators
            assert first_line.startswith(f'# {expected_path}')

    def test_specific_folders(self, adapter):
        """Test labeling specific folders"""
        files_processed, _ = adapter.label_files(['api'])
        assert files_processed > 0

        # Only api files should be labeled
        frontend_file = adapter.root_dir / 'frontend' / 'app' / 'page.tsx'
        with open(frontend_file, 'r') as f:
            first_line = f.readline().strip()
            assert not first_line.startswith('// frontend/app/page.tsx')


class TestGitignoreIntegration:
    """Tests for .gitignore integration"""

    def test_gitignore_parsing(self, adapter):
        """Test .gitignore parsing"""
        assert adapter._gitignore_spec is not None

        # Test ignored patterns
        node_modules_file = adapter.root_dir / 'node_modules' / 'test.js'
        assert adapter._is_ignored(node_modules_file)

    def test_custom_gitignore(self, test_dir, test_config):
        """Test custom .gitignore patterns"""
        gitignore_path = test_dir / '.gitignore'
        gitignore_path.write_text('*.test\n/custom_dir/')

        adapter = IntrospectionAdapter(test_dir, test_config)

        assert adapter._is_ignored(test_dir / 'file.test')
        assert adapter._is_ignored(test_dir / 'custom_dir' / 'file.py')
        assert not adapter._is_ignored(test_dir / 'api' / 'routes.py')


@pytest.mark.integration
class TestIntegration:
    """Integration tests for IntrospectionAdapter"""

    def test_full_workflow(self, adapter):
        """Test complete workflow with all features"""
        # 1. Count lines
        loc_stats = adapter.count_lines_of_code()
        assert loc_stats['total_lines'] > 0
        assert loc_stats['files_processed'] > 0

        # 2. Label files
        files_processed, _ = adapter.label_files()
        assert files_processed > 0

        # 3. Verify file labeling
        sample_file = adapter.root_dir / 'api' / 'routes.py'
        with open(sample_file, 'r') as f:
            first_line = f.readline().strip()
            expected_path = str(Path('api/routes.py'))
            assert first_line.startswith(f'# {expected_path}')

        # 4. Check routes
        routes = adapter.catalog_routes()
        assert routes['nextjs'] or routes['flask']

        # 5. Check directory structure
        tree, stats = adapter.get_directory_tree()
        assert stats['directories'] > 0
        assert stats['files'] > 0
        assert 'api' in tree
        assert 'frontend' in tree

    def test_error_recovery(self, adapter):
        """Test recovery from errors in one component"""
        # Create some problematic files
        bad_file = adapter.root_dir / 'api' / 'syntax_error.py'
        bad_file.write_text('def broken():')

        # Run through main operations
        routes = adapter.catalog_routes()
        loc_stats = adapter.count_lines_of_code()
        files_processed, follow_up = adapter.label_files()

        # Verify other operations still work
        assert isinstance(routes, dict)
        assert isinstance(loc_stats, dict)
        assert files_processed > 0
