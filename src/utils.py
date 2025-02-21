import csv
import logging
from collections import Counter
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from requests import RequestException
from tqdm import tqdm

from constants import PEP_DOC_URL, EXPECTED_STATUS, RESULTS_DIR
from exceptions import ParserFindTagException, RequestError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_response(session, url, encoding='utf-8'):
    """Выполняет GET-запрос и возвращает объект ответа."""
    try:
        response = session.get(url)
        response.encoding = encoding
        return response
    except RequestException as error:
        raise RequestError(f'Ошибка при загрузке страницы {url}: {error}')


def get_soup(session, url, parser='lxml'):
    """Получает HTML-страницу и возвращает объект BeautifulSoup."""
    response = get_response(session, url)
    return BeautifulSoup(response.text, parser)


def find_tag(soup, tag, attrs=None):
    """Ищет тег в HTML-дереве, выбрасывает исключение, если не найден."""
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        raise ParserFindTagException(error_msg)
    return searched_tag


def save_to_csv(status_counts, filename='pep_summary.csv'):
    """Сохраняет данные в CSV-файл."""
    RESULTS_DIR.mkdir(exist_ok=True)
    file_path = RESULTS_DIR / filename

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Статус", "Количество"])
        for status, count in status_counts.items():
            writer.writerow([status, count])

    print(f"Файл сохранён в: {file_path}")


def get_pep_status(session, pep_url):
    """Получает статус PEP-документа."""
    soup = get_soup(session, pep_url)
    status_tag = soup.find('abbr', title=True)
    return status_tag.text.strip() if status_tag else None


def parse_pep_list(session):
    """Получает список всех PEP-документов и их ссылки."""
    soup = get_soup(session, PEP_DOC_URL)
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
    errors = []

    for second_letter, pep_number, pep_url in tqdm(
        pep_links,
        desc="Парсинг PEP"
    ):
        expected_statuses = EXPECTED_STATUS.get(second_letter, ("Unknown",))

        try:
            actual_status = get_pep_status(session, pep_url)
        except RuntimeError as error:
            errors.append(str(error))
            continue

        if actual_status:
            status_counts[actual_status] += 1
            if actual_status not in expected_statuses:
                mismatched_peps.append((
                    pep_url,
                    actual_status,
                    expected_statuses
                ))

    if errors:
        logger.error(
            "Ошибки при парсинге PEP-документов:\n%s", "\n".join(errors))

    if mismatched_peps:
        logger.warning("Несовпадающие статусы:")
        for pep_url, actual_status, expected_statuses in mismatched_peps:
            logger.warning(
                f"{pep_url}\n"
                f"Статус в карточке: {actual_status}\n"
                f"Ожидаемые статусы: {list(expected_statuses)}\n"
            )

    status_counts["Total"] = sum(status_counts.values())
    return status_counts
