import argparse
import sys
import urllib.request
import json
import re

def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='Dependency graph visualization tool'
    )
    
    parser.add_argument(
        '--package',
        type=str,
        required=True,
        help='Package name'
    )
    
    parser.add_argument(
        '--source',
        type=str,
        required=True,
        help='Repository URL or path to test repository file'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Test repository mode'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='dependency_graph.png',
        help='Output graph image filename'
    )
    
    parser.add_argument(
        '--ascii-tree',
        action='store_true',
        help='Output dependencies in ASCII tree format'
    )
    
    return parser.parse_args()

def validate_arguments(args):
    """Валидация аргументов"""
    errors = []
    
    if not args.package or not args.package.strip():
        errors.append("Package name cannot be empty")
    
    if not args.source or not args.source.strip():
        errors.append("Source cannot be empty")
    
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

def get_package_dependencies(package_name, source_url):
    """
    Получает прямые зависимости пакета из PyPI
    Без использования менеджеров пакетов
    """
    try:
        # Формируем URL для PyPI API
        pypi_url = f"https://pypi.org/pypi/{package_name}/json"
        
        # Получаем данные о пакете через HTTP запрос
        with urllib.request.urlopen(pypi_url) as response:
            data = json.loads(response.read().decode())
        
        # Извлекаем зависимости из поля requires_dist
        dependencies = []
        if 'info' in data and 'requires_dist' in data['info']:
            requires_dist = data['info']['requires_dist']
            if requires_dist:
                for requirement in requires_dist:
                    # Извлекаем только имя пакета из строки требования
                    # Пример: "urllib3 (>=1.21.1,<3)" -> "urllib3"
                    match = re.match(r'^([a-zA-Z0-9_-]+)', requirement)
                    if match:
                        dependencies.append(match.group(1))
        
        return dependencies
        
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: Cannot find package '{package_name}' on PyPI", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching dependencies: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """Основная функция"""
    try:
        # Парсим аргументы
        args = parse_arguments()
        
        # Валидируем аргументы
        validate_arguments(args)
        
        # Этап 2: Получаем и выводим прямые зависимости
        if not args.test_mode:
            print(f"Fetching direct dependencies for package: {args.package}")
            dependencies = get_package_dependencies(args.package, args.source)
            
            # (Только для этого этапа) Выводим прямые зависимости
            print(f"Direct dependencies of '{args.package}':")
            if dependencies:
                for i, dep in enumerate(dependencies, 1):
                    print(f"  {i}. {dep}")
            else:
                print("  No dependencies found")
        
    except Exception as e:
        print(f"Critical error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()