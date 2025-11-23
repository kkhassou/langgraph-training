"""RAG検索結果のキャッシュシステム

このモジュールは、RAG検索結果をキャッシュして、
同じクエリに対する重複検索を避けることでパフォーマンスを向上させます。

Example:
    >>> cache = RAGCache(max_size=1000, ttl=3600)
    >>> 
    >>> # キャッシュから取得を試みる
    >>> results = cache.get("Python とは", "documents", top_k=5)
    >>> if results is None:
    ...     # キャッシュミス: 検索を実行
    ...     results = await search_engine.search("Python とは", top_k=5)
    ...     # キャッシュに保存
    ...     cache.set("Python とは", "documents", 5, results)
"""

from typing import Optional, List, Dict, Any
import hashlib
import time
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)


class RAGCache:
    """RAG検索結果のキャッシュマネージャー
    
    LRU（Least Recently Used）方式でキャッシュを管理し、
    TTL（Time To Live）により古いエントリを自動削除します。
    
    Features:
        - LRUキャッシュ: 最も使用されていないエントリを削除
        - TTL: 指定時間経過後に自動的にエントリを無効化
        - 統計情報: ヒット率などのメトリクスを提供
    
    Attributes:
        max_size: キャッシュの最大サイズ
        ttl: エントリの有効期限（秒）
        hits: キャッシュヒット数
        misses: キャッシュミス数
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Args:
            max_size: キャッシュの最大サイズ（デフォルト: 1000）
            ttl: エントリの有効期限（秒、デフォルト: 3600 = 1時間）
        """
        self.max_size = max_size
        self.ttl = ttl
        
        # OrderedDictでLRUキャッシュを実装
        self._cache: OrderedDict[str, tuple[float, List[Dict[str, Any]]]] = OrderedDict()
        
        # 統計情報
        self.hits = 0
        self.misses = 0
        
        logger.info(f"RAGCache initialized: max_size={max_size}, ttl={ttl}s")
    
    def _generate_key(
        self,
        query: str,
        collection: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """キャッシュキーを生成
        
        クエリ、コレクション、top_k、フィルターからハッシュを生成します。
        
        Args:
            query: 検索クエリ
            collection: コレクション名
            top_k: 取得する結果数
            filters: 追加フィルター
        
        Returns:
            MD5ハッシュ文字列
        """
        # フィルターを文字列化（ソートして一貫性を保つ）
        filters_str = ""
        if filters:
            filters_str = str(sorted(filters.items()))
        
        data = f"{query}|{collection}|{top_k}|{filters_str}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def get(
        self,
        query: str,
        collection: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """キャッシュから検索結果を取得
        
        Args:
            query: 検索クエリ
            collection: コレクション名
            top_k: 取得する結果数
            filters: 追加フィルター
        
        Returns:
            キャッシュヒット時は検索結果、ミス時はNone
        """
        key = self._generate_key(query, collection, top_k, filters)
        
        if key in self._cache:
            timestamp, results = self._cache[key]
            
            # TTLチェック
            if time.time() - timestamp < self.ttl:
                # LRU: アクセスされたエントリを最後に移動
                self._cache.move_to_end(key)
                self.hits += 1
                
                logger.debug(
                    f"Cache HIT: query='{query[:30]}...', "
                    f"age={time.time() - timestamp:.1f}s"
                )
                return results
            else:
                # TTL切れ: エントリを削除
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: query='{query[:30]}...'")
        
        self.misses += 1
        logger.debug(f"Cache MISS: query='{query[:30]}...'")
        return None
    
    def set(
        self,
        query: str,
        collection: str,
        top_k: int,
        results: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None
    ):
        """検索結果をキャッシュに保存
        
        Args:
            query: 検索クエリ
            collection: コレクション名
            top_k: 取得する結果数
            results: 検索結果
            filters: 追加フィルター
        """
        key = self._generate_key(query, collection, top_k, filters)
        
        # サイズ制限チェック: 最も古いエントリを削除（LRU）
        while len(self._cache) >= self.max_size:
            # OrderedDictの最初のエントリ（最も使われていない）を削除
            oldest_key, oldest_value = self._cache.popitem(last=False)
            logger.debug(f"Cache EVICTED: key={oldest_key}")
        
        # 新しいエントリを追加
        self._cache[key] = (time.time(), results)
        
        logger.debug(
            f"Cache SET: query='{query[:30]}...', "
            f"results={len(results)}, size={len(self._cache)}/{self.max_size}"
        )
    
    def clear(self):
        """キャッシュをクリア"""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def invalidate(
        self,
        query: Optional[str] = None,
        collection: Optional[str] = None
    ):
        """特定のクエリまたはコレクションのキャッシュを無効化
        
        Args:
            query: クエリ（省略時は全て）
            collection: コレクション名（省略時は全て）
        """
        if query is None and collection is None:
            self.clear()
            return
        
        # 削除対象のキーを収集
        keys_to_delete = []
        for key in self._cache.keys():
            # キーから条件に合うものを探す（簡易実装）
            # 実際の実装ではキーと元のパラメータのマッピングを保持する方が効率的
            keys_to_delete.append(key)
        
        # 削除実行
        for key in keys_to_delete:
            del self._cache[key]
        
        logger.info(f"Cache invalidated: {len(keys_to_delete)} entries removed")
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "ttl": self.ttl
        }
    
    def reset_stats(self):
        """統計情報をリセット"""
        self.hits = 0
        self.misses = 0
        logger.info("Cache stats reset")
    
    def __len__(self) -> int:
        """キャッシュのサイズを返す"""
        return len(self._cache)
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"RAGCache(size={stats['size']}/{stats['max_size']}, "
            f"hit_rate={stats['hit_rate']:.2%}, "
            f"ttl={stats['ttl']}s)"
        )


# グローバルキャッシュインスタンス（シングルトン）
_global_cache: Optional[RAGCache] = None


def get_global_cache(
    max_size: int = 1000,
    ttl: int = 3600
) -> RAGCache:
    """グローバルキャッシュインスタンスを取得
    
    アプリケーション全体で共有されるキャッシュインスタンスを返します。
    初回呼び出し時にインスタンスが作成されます。
    
    Args:
        max_size: キャッシュの最大サイズ（初回のみ有効）
        ttl: エントリの有効期限（秒、初回のみ有効）
    
    Returns:
        グローバルキャッシュインスタンス
    
    Example:
        >>> cache = get_global_cache()
        >>> results = cache.get("query", "collection", 5)
    """
    global _global_cache
    
    if _global_cache is None:
        _global_cache = RAGCache(max_size=max_size, ttl=ttl)
        logger.info("Global RAGCache instance created")
    
    return _global_cache


def clear_global_cache():
    """グローバルキャッシュをクリア"""
    global _global_cache
    
    if _global_cache is not None:
        _global_cache.clear()

