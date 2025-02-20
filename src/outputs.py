import csv
import logging
import datetime as dt

from prettytable import PrettyTable

from constants import DATETIME_FORMAT, RESULTS_DIR


def control_output(results, cli_args):
    """Определяет способ вывода результатов."""
    output_methods = {
        'pretty': pretty_output,
        'file': file_output,
    }
    output_method = output_methods.get(cli_args.output, default_output)
    output_method(results, cli_args)


def default_output(results, *_):
    """Выводит результаты в стандартном текстовом формате."""
    for row in results:
        print(*row)


def pretty_output(results, *_):
    """Выводит результаты в табличном формате."""
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    """Сохраняет результаты в CSV-файл."""
    RESULTS_DIR.mkdir(exist_ok=True)

    parser_mode = cli_args.mode
    now_formatted = dt.datetime.now().strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = RESULTS_DIR / file_name

    with open(file_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, dialect='unix')
        writer.writerows(results)

    logging.info('Файл с результатами был сохранён: %s', file_path)
