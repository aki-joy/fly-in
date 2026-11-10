class FlyInError(Exception):
    """configやparseなどのエラーのベースエラークラス"""


class MapLoadError(FlyInError):
    """マップファイルを開けない・デコードできないときに挙げられるエラー"""


class ParseError(FlyInError):
    """parseに失敗したときに挙げられるエラー"""

    def __init__(self, line_no: int | None, reason: str) -> None:
        self.line_no = line_no
        self.reason = reason
        where = f"line {line_no}: " if line_no is not None else ""
        super().__init__(f"{where}{reason}")


class NoPathError(FlyInError):
    """start_hubからend_hubへ辿り着く経路がないときに挙げられるエラー"""
