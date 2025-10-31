import logging
import sys
from Sisyphus.Utils.Terminal.Style import Style

# Define simple color styles per level
LEVEL_STYLES = {
    logging.DEBUG: Style.fg(0x777777),
    logging.INFO: Style.fg(0x00ffff),      # cyan
    logging.WARNING: Style.fg(0xffd700),   # gold/yellow
    logging.ERROR: Style.fg(0xff3333),     # red
    logging.CRITICAL: Style.fg(0xff0000).bold(),
}

class ColorFormatter(logging.Formatter):
    """Formatter that applies color via Sisyphus Style for terminal output."""
    def format(self, record):
        msg = super().format(record)
        style = LEVEL_STYLES.get(record.levelno, Style.fg(0xffffff))
        return style(msg)

def attach_color_console_handler(logger):
    """Attach color console handler if running in interactive terminal."""
    if not sys.stdout.isatty():
        return  # skip if not a TTY (like uwsgi or file)

    # Prevent duplicate handlers
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler):
            return

    handler = logging.StreamHandler(sys.stdout)
    formatter = ColorFormatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
