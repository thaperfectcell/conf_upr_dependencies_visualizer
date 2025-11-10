import argparse
import sys
import urllib.request
import json
import re
from collections import deque

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

def read_test_repository(file_path):
    """
    Читает тестовый репозиторий из файла
    Формат: A: B, C
    """
    dependencies = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line and ':' in line:
                    package, deps = line.split(':', 1)
                    package = package.strip()
                    # Извлекаем зависимости и убираем пробелы
                    dep_list = [dep.strip() for dep in deps.split(',') if dep.strip()]
                    dependencies[package] = dep_list
        return dependencies
    except Exception as e:
        print(f"Error reading test repository: {e}", file=sys.stderr)
        sys.exit(1)

def build_dependency_graph(start_package, get_dependencies_func):
    """
    Строит граф зависимостей с помощью BFS с рекурсией
    Обрабатывает циклические зависимости
    """
    graph = {}
    visited = set()
    recursion_stack = set()
    cycles = []
    
    def bfs(package):
        # Проверка на циклическую зависимость
        if package in recursion_stack:
            cycles.append(package)
            return []
        
        # Если пакет уже посещен, возвращаем его зависимости
        if package in visited:
            return graph.get(package, [])
        
        # Добавляем пакет в стек рекурсии и посещенные
        recursion_stack.add(package)
        visited.add(package)
        
        # Получаем прямые зависимости
        direct_dependencies = get_dependencies_func(package)
        graph[package] = direct_dependencies
        
        # Рекурсивно обходим все зависимости
        all_dependencies = set(direct_dependencies)
        for dep in direct_dependencies:
            child_dependencies = bfs(dep)
            all_dependencies.update(child_dependencies)
        
        # Убираем пакет из стека рекурсии
        recursion_stack.remove(package)
        
        return list(all_dependencies)
    
    # Запускаем BFS с корневого пакета
    bfs(start_package)
    
    return graph, cycles

def main():
    """Основная функция"""
    try:
        # Парсим аргументы
        args = parse_arguments()
        
        # Валидируем аргументы
        validate_arguments(args)
        
        # Определяем функцию для получения зависимостей в зависимости от режима
        if args.test_mode:
            # Режим тестирования: читаем из файла
            print(f"Test mode: reading dependencies from {args.source}")
            test_dependencies = read_test_repository(args.source)
            
            def get_deps_test(package):
                return test_dependencies.get(package, [])
            
            get_dependencies_func = get_deps_test
        else:
            # Режим работы с реальным PyPI
            print(f"Fetching dependencies for package: {args.package}")
            get_dependencies_func = get_package_dependencies
        
        # Строим граф зависимостей
        dependency_graph, cycles = build_dependency_graph(args.package, get_dependencies_func)
        
        # Выводим результаты
        print(f"\nDependency graph for '{args.package}':")
        for package, deps in dependency_graph.items():
            print(f"  {package} -> {deps}")
        
        if cycles:
            print(f"\nCyclic dependencies detected: {cycles}")
        else:
            print("\nNo cyclic dependencies found")
        
    except Exception as e:
        print(f"Critical error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()