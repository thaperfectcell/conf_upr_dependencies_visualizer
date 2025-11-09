import argparse
import sys

def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='Visualisation dependencies with graph tool'
    )
    
    # Добавляем все необходимые параметры
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
        help='URL of repo or path to the file of test repo'
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
        help='Name of the file containing image of graph'
    )
    
    parser.add_argument(
        '--ascii-tree',
        action='store_true',
        help='Dependencies otput mode ASCII'
    )
    
    return parser.parse_args()

def validate_arguments(args):
    """Валидация аргументов"""
    errors = []
    
    # Проверка имени пакета
    if not args.package or not args.package.strip():
        errors.append("Package name can't be empty")
    
    # Проверка источника
    if not args.source or not args.source.strip():
        errors.append("Source can't be empty")
    
    # Если есть ошибки, выводим их и завершаем программу
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

def main():
    """Main func"""
    try:
        # Парсим аргументы
        args = parse_arguments()
        
        # Валидируем аргументы
        validate_arguments(args)
        
        # (Только для этого этапа) Выводим все параметры
        print("App parameteres:")
        print(f"  Package: {args.package}")
        print(f"  Source: {args.source}")
        print(f"  Test mode: {args.test_mode}")
        print(f"  Output file: {args.output}")
        print(f"  ASCII tree: {args.ascii_tree}")
        
    except Exception as e:
        print(f"Critical error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()