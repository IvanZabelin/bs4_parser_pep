class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег."""


class ParsingError(Exception):
    """Ошибка парсинга данных."""


class RequestError(Exception):
    """Ошибка при выполнении HTTP-запроса."""
