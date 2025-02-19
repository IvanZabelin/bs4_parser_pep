import logging
import csv

from collections import Counter
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from requests import RequestException
from tqdm import tqdm

from exceptions import ParserFindTagException
from constants import PEP_DOC_URL, BASE_DIR, EXPECTED_STATUS


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logger.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logger.error(error_msg, stack_info=True)
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

    status_tag = soup.find('abbr', title=True)
    if status_tag:
        return status_tag.text.strip()
    return None


def parse_pep_list(session):
    """Получает список всех PEP-документов и их ссылки."""
    response = get_response(session, PEP_DOC_URL)
    if response is None:
        return []

    soup = BeautifulSoup(response.text, 'lxml')
    section = find_tag(soup, 'section', attrs={'id': 'index-by-category'})
    table_rows = section.find_all('tr')[1:]

    pep_links = []
    for row in table_rows:
        columns = row.find_all('td')
        if not columns:
            continue

        pep_number = columns[1].text.strip()
        if pep_number == '0':
            continue

        abbr_tag_elem = columns[0].find('abbr')
        abbr_text = abbr_tag_elem.text.strip() if abbr_tag_elem else ''
        second_letter = abbr_text[1] if len(abbr_text) > 1 else ''
        pep_link = urljoin(PEP_DOC_URL, columns[1].find('a')['href'])

        pep_links.append((second_letter, pep_number, pep_link))

    return pep_links


def process_pep_data(session, pep_links):
    """Обрабатывает список PEP и считает их статусы, сверяя с ожидаемыми."""
    status_counts = Counter()
    mismatched_peps = []

    for second_letter, pep_number, pep_url in tqdm(
        pep_links, desc="Парсинг PEP"
    ):
        expected_statuses = EXPECTED_STATUS.get(second_letter, ("Unknown",))
        actual_status = get_pep_status(session, pep_url)

        if actual_status:
            status_counts[actual_status] += 1

            if actual_status not in expected_statuses:
                mismatched_peps.append(
                    (pep_url, actual_status, expected_statuses)
                )

    # Логируем несовпадающие статусы
    if mismatched_peps:
        logger.warning("Несовпадающие статусы:")
        for pep_url, actual_status, expected_statuses in mismatched_peps:
            logger.warning(
                f"{pep_url}\n"
                f"Статус в карточке: {actual_status}\n"
                f"Ожидаемые статусы: {list(expected_statuses)}\n"
            )

    # Добавляем итоговую строку
    status_counts["Total"] = sum(status_counts.values())

    return status_counts
