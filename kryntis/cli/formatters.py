"""Core CLI Formatter."""

class CLIFormatter:
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

    @classmethod
    def cyan(cls, text: str) -> str:
        return f"{cls.OKCYAN}{text}{cls.ENDC}"

    @classmethod
    def green(cls, text: str) -> str:
        return f"{cls.OKGREEN}{text}{cls.ENDC}"

    @classmethod
    def yellow(cls, text: str) -> str:
        return f"{cls.WARNING}{text}{cls.ENDC}"

    @classmethod
    def bold(cls, text: str) -> str:
        return f"{cls.BOLD}{text}{cls.ENDC}"
