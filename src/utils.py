import logging
import csv

from collections import Counter
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from requests import RequestException
from exceptions import ParserFindTagException
from constants import PEP_DOC_URL, BASE_DIR
from tqdm import tqdm


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузки страницы {url}',
            stack_info=True,
        )


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def save_to_csv(status_counts, filename='pep_summary.csv'):
    results_dir = BASE_DIR / 'results'
    results_dir.mkdir(exist_ok=True)
    file_path = results_dir / filename
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Статус", "Количество"])
        for status, count in status_counts.items():
            writer.writerow([status, count])    
    print(f"Файл сохранён в: {file_path}")


def get_pep_status(session, pep_url):
    response = get_response(session, pep_url)
    if response is None:
        return None
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Ищем статус в теге <abbr> с атрибутом title
    status_tag = soup.find('abbr', title=True)
    if status_tag:
        status = status_tag.text.strip()
        logging.info(f"PEP URL: {pep_url} - Статус: {status}")
        return status
    
    logging.warning(f"PEP URL: {pep_url} - Статус не найден")
    return None



def parse_pep_list(session):
    """Получает список всех PEP-документов и их ссылки."""
    response = get_response(session, PEP_DOC_URL)
    if response is None:
        return []

    soup = BeautifulSoup(response.text, 'lxml')
    section = find_tag(soup, 'section', attrs={'id': 'index-by-category'})
    table_rows = section.find_all('tr')[1:]  # Пропускаем заголовок таблицы

    pep_links = []
    for row in table_rows:
        columns = row.find_all('td')
        if not columns:
            continue

        pep_number = columns[1].text.strip()
        if pep_number == '0':  # Пропускаем PEP 0
            continue

        pep_link = urljoin(PEP_DOC_URL, columns[1].find('a')['href'])
        pep_links.append((pep_number, pep_link))

    return pep_links


def process_pep_data(session, pep_links):
    """Обрабатывает список PEP и считает их статусы."""
    status_counts = Counter()

    for pep_number, pep_url in tqdm(pep_links, desc="Парсинг PEP"):
        status = get_pep_status(session, pep_url)
        if status:
            status_counts[status] += 1

    status_counts["Total"] = sum(status_counts.values())  # Итоговая строка
    return status_counts
