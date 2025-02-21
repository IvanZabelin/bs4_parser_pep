import logging
import re
import requests
from urllib.parse import urljoin

from requests_cache import CachedSession
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, DOWNLOADS, MAIN_DOC_URL
from outputs import control_output
from exceptions import ParsingError, RequestError
from utils import (
    find_tag,
    parse_pep_list,
    process_pep_data,
    save_to_csv,
    get_soup,
)


def whats_new(session):
    """Парсит страницу с нововведениями в Python."""
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    try:
        soup = get_soup(session, whats_new_url)
    except RequestError as error:
        logging.error(
            "Ошибка при загрузке страницы нововведений %s: %s",
            whats_new_url,
            error
        )
        return []

    main_div = find_tag(
        soup, 'section', attrs={'id': 'what-s-new-in-python'}
    )
    div_with_ul = find_tag(
        main_div, 'div', attrs={'class': 'toctree-wrapper'}
    )
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    skipped_links = []

    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        try:
            soup = get_soup(session, version_link)
            h1 = find_tag(soup, 'h1')
            dl = find_tag(soup, 'dl')
            dl_text = dl.text.replace('\n', ' ')
            results.append((version_link, h1.text, dl_text))
        except RequestError as error:
            skipped_links.append(version_link)

    if skipped_links:
        logging.warning(
            "Пропущены итерации: не удалось получить %s",
            ', '.join(skipped_links)
        )

    return results


def latest_versions(session):
    """Парсит список последних версий Python."""
    try:
        soup = get_soup(session, MAIN_DOC_URL)
    except requests.RequestException as error:
        logging.error("Ошибка при загрузке главной страницы: %s", error)
        return []

    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')

    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ParsingError(
            'Не найден раздел "All versions" в боковом меню.'
        )

    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'

    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        version, status = text_match.groups() if text_match else (
            a_tag.text, ''
        )

        results.append((link, version, status))

    return results


def download(session):
    """Скачивает PDF-документацию по Python."""
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    try:
        soup = get_soup(session, downloads_url)
    except RequestError as error:
        logging.error(
            "Ошибка при загрузке страницы %s: %s", downloads_url, error)
        return

    table_tag = find_tag(soup, 'table')
    pdf_a4_tag = find_tag(
        table_tag, 'a', attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)

    try:
        response = session.get(archive_url)
        response.raise_for_status()
    except requests.RequestException as error:
        logging.error("Ошибка при скачивании архива: %s", error)
        return

    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / DOWNLOADS
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename

    with open(archive_path, 'wb') as file:
        file.write(response.content)

    logging.info("Архив был загружен и сохранён: %s", archive_path)


def pep(session):
    """Парсит PEP-документы, считает их статусы и сохраняет в CSV."""
    pep_links = parse_pep_list(session)

    status_counts = process_pep_data(session, pep_links)

    save_to_csv(status_counts, 'pep_summary.csv')

    return [("Статус", "Количество")] + list(status_counts.items())


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    """Точка входа в программу."""
    configure_logging()
    logging.info("Парсер запущен!")

    try:
        args_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
        args = args_parser.parse_args()
        logging.info("Аргументы командной строки: %s", args)

        session = CachedSession()
        if args.clear_cache:
            session.cache.clear()

        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)

        if results is not None:
            control_output(results, args)

    except Exception as e:
        logging.exception(
            "Во время выполнения программы произошла ошибка: %s", e
        )

    logging.info("Парсер завершил работу.")


if __name__ == '__main__':
    main()
