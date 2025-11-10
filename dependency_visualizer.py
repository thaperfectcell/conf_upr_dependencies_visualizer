import argparse
import sys
import urllib.request
import json
import re
import os
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
    Завершает программу при обнаружении циклических зависимостей
    """
    graph = {}
    visited = set()
    recursion_stack = set()
    cycles = []
    
    def bfs(package):
        # Проверка на циклическую зависимость - ЗАВЕРШАЕМ ПРОГРАММУ
        if package in recursion_stack:
            print(f"Error: Cyclic dependency detected involving package '{package}'", file=sys.stderr)
            sys.exit(1)  # ЗАВЕРШАЕМ ПРОГРАММУ
        
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

def get_load_order(dependency_graph, start_package):
    """
    Определяет порядок загрузки зависимостей
    Использует топологическую сортировку
    """
    # Строим обратный граф для подсчета входящих степеней
    in_degree = {}
    reverse_graph = {}
    
    # Инициализируем структуры данных
    for package in dependency_graph:
        in_degree[package] = 0
        reverse_graph[package] = []
    
    # Заполняем обратный граф и считаем входящие степени
    for package, dependencies in dependency_graph.items():
        for dep in dependencies:
            if dep in reverse_graph:
                reverse_graph[dep].append(package)
                in_degree[package] += 1
            else:
                # Если зависимость не в графе, добавляем ее
                reverse_graph[dep] = [package]
                in_degree[dep] = 0
                in_degree[package] = in_degree.get(package, 0) + 1
    
    # Алгоритм Кана (топологическая сортировка)
    queue = deque()
    load_order = []
    
    # Добавляем узлы с нулевой входящей степенью
    for package, degree in in_degree.items():
        if degree == 0:
            queue.append(package)
    
    while queue:
        current = queue.popleft()
        load_order.append(current)
        
        # Уменьшаем входящую степень соседей
        for neighbor in reverse_graph.get(current, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Проверяем наличие циклов (невозможность топологической сортировки)
    if len(load_order) != len(in_degree):
        print("Warning: Graph has cycles, load order may be incomplete")
    
    return load_order

def generate_mermaid_graph(dependency_graph, start_package):
    """
    Генерирует текстовое представление графа на языке Mermaid
    Экранирует имена пакетов которые являются ключевыми словами
    """
    mermaid_code = "graph TD\n"
    
    # Добавляем все узлы и связи
    for package, dependencies in dependency_graph.items():
        for dep in dependencies:
            # Экранируем имена пакетов которые могут быть ключевыми словами
            safe_package = escape_mermaid_id(package)
            safe_dep = escape_mermaid_id(dep)
            mermaid_code += f"    {safe_package} --> {safe_dep}\n"
    
    # Выделяем стартовый пакет
    safe_start = escape_mermaid_id(start_package)
    mermaid_code += f"    style {safe_start} fill:#99f,stroke:#333,stroke-width:2px\n"
    
    return mermaid_code

def escape_mermaid_id(name):
    """
    Экранирует идентификаторы для Mermaid
    Если имя является ключевым словом, оборачиваем в кавычки
    """
    keywords = {'click', 'style', 'graph', 'TD', 'LR', 'RL', 'BT'}
    
    # Если имя содержит не-ASCII символы или является ключевым словом
    if not name.isidentifier() or name in keywords:
        return f'"{name}"'
    return name

def print_ascii_tree(dependency_graph, start_package, prefix="", is_last=True):
    """
    Выводит зависимости в виде ASCII-дерева
    """
    def build_tree(package, prefix, is_last):
        """Рекурсивно строит дерево"""
        # Текущий узел
        connector = "└── " if is_last else "├── "
        print(prefix + connector + package)
        
        # Новый префикс для дочерних элементов
        new_prefix = prefix + ("    " if is_last else "│   ")
        
        # Рекурсивно обрабатываем зависимости
        dependencies = dependency_graph.get(package, [])
        for i, dep in enumerate(dependencies):
            is_last_dep = i == len(dependencies) - 1
            build_tree(dep, new_prefix, is_last_dep)
    
    print(f"Dependency tree for {start_package}:")
    build_tree(start_package, "", True)

def save_mermaid_to_png(mermaid_code, output_file):
    """
    Сохраняет Mermaid граф в PNG файл и текстовый файл с кодом
    """
    try:
        # Сохраняем Mermaid код в текстовый файл
        text_output = output_file.replace('.png', '.mmd')
        with open(text_output, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        print(f"Mermaid code saved to: {text_output}")
        
        # Создаем временный файл с Mermaid кодом для конвертации
        mermaid_file = "temp_graph.mmd"
        with open(mermaid_file, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        
        # Конвертируем в PNG используя mermaid-cli
        os.system(f"mmdc -i {mermaid_file} -o {output_file} -t dark")
        
        # Удаляем временный файл
        os.remove(mermaid_file)
        
        print(f"Graph image saved to: {output_file}")
        
    except Exception as e:
        print(f"Warning: Could not generate PNG. Install mermaid-cli: npm install -g @mermaid-js/mermaid-cli")
        print(f"Mermaid code saved to: {output_file.replace('.png', '.mmd')}")
        
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
            def get_deps_real(package):
                return get_package_dependencies(package, args.source)
            
            get_dependencies_func = get_deps_real
        
        # Строим граф зависимостей
        dependency_graph, cycles = build_dependency_graph(args.package, get_dependencies_func)
        
        # Выводим граф
        print(f"\nDependency graph for '{args.package}':")
        for package, deps in dependency_graph.items():
            print(f"  {package} -> {deps}")
        
        # УБИРАЕМ вывод cycles, так как теперь программа завершается при их обнаружении
        print("\nNo cyclic dependencies found")
        
        # Порядок загрузки зависимостей
        load_order = get_load_order(dependency_graph, args.package)
        print(f"\nLoad order for '{args.package}':")
        for i, package in enumerate(load_order, 1):
            print(f"  {i}. {package}")
        
        # ЭТАП 5: Визуализация
        print(f"\n=== STAGE 5: Visualization ===")
        
        # 1. Генерируем Mermaid граф
        mermaid_code = generate_mermaid_graph(dependency_graph, args.package)
        print(f"\nMermaid graph generated:")
        print(mermaid_code)
        
        # 2. Сохраняем в PNG
        save_mermaid_to_png(mermaid_code, args.output)
        
        # 3. ASCII-дерево если задан параметр
        if args.ascii_tree:
            print(f"\nASCII Tree:")
            print_ascii_tree(dependency_graph, args.package)
        
    except Exception as e:
        print(f"Critical error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()