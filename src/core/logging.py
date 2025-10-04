"""ログ設定"""
import logging
import sys


def setup_logging(level=logging.INFO):
    """ロギングのセットアップ

    Args:
        level: ログレベル (default: logging.INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def get_logger(name: str) -> logging.Logger:
    """ロガーを取得

    Args:
        name: ロガー名

    Returns:
        logging.Logger: ロガーインスタンス
    """
    return logging.getLogger(name)
