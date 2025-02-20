from pathlib import Path


MAIN_DOC_URL = 'https://docs.python.org/3/'
PEP_DOC_URL = 'https://peps.python.org/'

BASE_DIR = Path(__file__).parent

DT_FORMAT = '%d.%m.%Y %H:%M:%S'
DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'

BASE_LOG_DIR = BASE_DIR / 'logs'
RESULTS_DIR = BASE_DIR / 'results'
LOG_FILE_PATH = BASE_LOG_DIR / 'parser.log'

RESULTS = 'results'
DOWNLOADS = 'downloads'


LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'

LOG_MAX_BYTES = 10**6
LOG_BACKUP_COUNT = 5

OUTPUT_PRETTY = 'pretty'
OUTPUT_FILE = 'file'

EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}
