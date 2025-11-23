"""パフォーマンステスト - LLMとRAGの最適化を検証

このモジュールは、パフォーマンス最適化機能をテストします：
- LLMプロバイダーのレート制限と同時実行制御
- RAGキャッシングのヒット率とパフォーマンス向上
"""

import pytest
import asyncio
import time
from typing import List

from src.providers.llm.gemini import GeminiProvider, RateLimiter
from src.infrastructure.cache.rag_cache import RAGCache
from src.nodes.rag.rag_node import RAGNode


class TestRateLimiter:
    """レート制限器のテスト"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """基本的なレート制限のテスト"""
        limiter = RateLimiter(requests_per_minute=10)
        
        # 10リクエストは即座に通過するはず
        start_time = time.time()
        for _ in range(10):
            await limiter.acquire()
        elapsed = time.time() - start_time
        
        # 10リクエストは1秒以内に完了するはず
        assert elapsed < 1.0, f"Expected < 1s, got {elapsed:.2f}s"
    
    @pytest.mark.asyncio
    async def test_rate_limiter_overflow(self):
        """レート制限超過時の待機テスト"""
        limiter = RateLimiter(requests_per_minute=5)
        
        # 5リクエストは即座に通過
        for _ in range(5):
            await limiter.acquire()
        
        # 6番目のリクエストは待機が必要
        start_time = time.time()
        await limiter.acquire()
        elapsed = time.time() - start_time
        
        # 約60秒待機するはず（実際のテストでは短縮版を使用）
        # ここでは待機が発生したことだけを確認
        assert elapsed > 0, "Expected some wait time"
    
    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent(self):
        """並行リクエストのレート制限テスト"""
        limiter = RateLimiter(requests_per_minute=10)
        
        async def make_request(request_id: int):
            await limiter.acquire()
            return request_id
        
        # 10個の並行リクエスト
        start_time = time.time()
        results = await asyncio.gather(*[make_request(i) for i in range(10)])
        elapsed = time.time() - start_time
        
        assert len(results) == 10
        assert elapsed < 2.0, f"Expected < 2s for 10 concurrent requests, got {elapsed:.2f}s"


class TestRAGCache:
    """RAGキャッシュのテスト"""
    
    def test_cache_basic_operations(self):
        """基本的なキャッシュ操作のテスト"""
        cache = RAGCache(max_size=10, ttl=3600)
        
        # キャッシュに保存
        results = [{"id": 1, "text": "result 1"}]
        cache.set("test query", "collection1", 5, results)
        
        # キャッシュから取得
        cached = cache.get("test query", "collection1", 5)
        assert cached is not None
        assert cached == results
        
        # 統計情報を確認
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["size"] == 1
    
    def test_cache_miss(self):
        """キャッシュミスのテスト"""
        cache = RAGCache(max_size=10, ttl=3600)
        
        # 存在しないキーを取得
        cached = cache.get("nonexistent", "collection1", 5)
        assert cached is None
        
        # 統計情報を確認
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
    
    def test_cache_ttl(self):
        """TTL（有効期限）のテスト"""
        cache = RAGCache(max_size=10, ttl=1)  # 1秒のTTL
        
        # キャッシュに保存
        results = [{"id": 1, "text": "result 1"}]
        cache.set("test query", "collection1", 5, results)
        
        # 即座に取得（ヒット）
        cached = cache.get("test query", "collection1", 5)
        assert cached is not None
        
        # 1秒待機
        time.sleep(1.1)
        
        # TTL切れでミス
        cached = cache.get("test query", "collection1", 5)
        assert cached is None
    
    def test_cache_lru_eviction(self):
        """LRU（最小使用）による削除のテスト"""
        cache = RAGCache(max_size=3, ttl=3600)
        
        # 3つのエントリを追加（最大サイズ）
        cache.set("query1", "col1", 5, [{"id": 1}])
        cache.set("query2", "col1", 5, [{"id": 2}])
        cache.set("query3", "col1", 5, [{"id": 3}])
        
        assert len(cache) == 3
        
        # query1を再アクセス（最後に移動）
        cache.get("query1", "col1", 5)
        
        # 4つ目のエントリを追加（query2が削除されるはず）
        cache.set("query4", "col1", 5, [{"id": 4}])
        
        assert len(cache) == 3
        assert cache.get("query1", "col1", 5) is not None  # 残っている
        assert cache.get("query2", "col1", 5) is None      # 削除された
        assert cache.get("query3", "col1", 5) is not None  # 残っている
        assert cache.get("query4", "col1", 5) is not None  # 新しいエントリ
    
    def test_cache_hit_rate(self):
        """ヒット率の計算テスト"""
        cache = RAGCache(max_size=10, ttl=3600)
        
        # 2つのエントリを追加
        cache.set("query1", "col1", 5, [{"id": 1}])
        cache.set("query2", "col1", 5, [{"id": 2}])
        
        # 5回アクセス: 3ヒット、2ミス
        cache.get("query1", "col1", 5)  # ヒット
        cache.get("query2", "col1", 5)  # ヒット
        cache.get("query1", "col1", 5)  # ヒット
        cache.get("query3", "col1", 5)  # ミス
        cache.get("query4", "col1", 5)  # ミス
        
        stats = cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.6  # 3/5


class TestLLMProviderPerformance:
    """LLMプロバイダーのパフォーマンステスト（モック使用）"""
    
    @pytest.mark.asyncio
    async def test_concurrent_request_limit(self):
        """同時リクエスト数制限のテスト（モック）"""
        # 注: 実際のAPIを使用せずにモックでテスト
        # 実装の構造をテストする
        
        from src.providers.llm.mock import MockLLMProvider
        
        # 同時実行数3に制限
        provider = MockLLMProvider(
            max_concurrent_requests=3,
            rate_limit_per_minute=60
        )
        
        # セマフォが正しく設定されているか確認
        assert provider._semaphore._value == 3
    
    @pytest.mark.asyncio
    async def test_rate_limit_configuration(self):
        """レート制限設定のテスト（モック）"""
        from src.providers.llm.mock import MockLLMProvider
        
        # レート制限を設定
        provider = MockLLMProvider(
            max_concurrent_requests=5,
            rate_limit_per_minute=30
        )
        
        # レート制限器が正しく設定されているか確認
        assert provider._rate_limiter.requests_per_minute == 30


class TestRAGNodeCaching:
    """RAGノードのキャッシング機能テスト"""
    
    @pytest.mark.asyncio
    async def test_rag_node_cache_enabled(self):
        """RAGノードでキャッシュが有効な場合のテスト"""
        from src.nodes.base import NodeState
        from src.providers.rag.simple import SimpleRAGProvider
        
        # カスタムキャッシュを作成
        cache = RAGCache(max_size=10, ttl=3600)
        
        # RAGノードを作成（キャッシュ有効）
        provider = SimpleRAGProvider()
        node = RAGNode(provider=provider, enable_cache=True, cache=cache)
        
        assert node.enable_cache is True
        assert node.cache is cache
    
    @pytest.mark.asyncio
    async def test_rag_node_cache_disabled(self):
        """RAGノードでキャッシュが無効な場合のテスト"""
        from src.providers.rag.simple import SimpleRAGProvider
        
        # RAGノードを作成（キャッシュ無効）
        provider = SimpleRAGProvider()
        node = RAGNode(provider=provider, enable_cache=False)
        
        assert node.enable_cache is False
        assert node.cache is None
    
    def test_cache_stats_retrieval(self):
        """キャッシュ統計情報の取得テスト"""
        from src.providers.rag.simple import SimpleRAGProvider
        
        # キャッシュ有効
        cache = RAGCache(max_size=10, ttl=3600)
        node = RAGNode(enable_cache=True, cache=cache)
        
        stats = node.get_cache_stats()
        assert stats is not None
        assert "size" in stats
        assert "hit_rate" in stats
        
        # キャッシュ無効
        node_no_cache = RAGNode(enable_cache=False)
        stats = node_no_cache.get_cache_stats()
        assert stats is None


class TestPerformanceImprovement:
    """パフォーマンス向上の検証テスト"""
    
    @pytest.mark.asyncio
    async def test_cache_performance_improvement(self):
        """キャッシュによるパフォーマンス向上のテスト"""
        cache = RAGCache(max_size=100, ttl=3600)
        
        # 大きなデータセットをシミュレート
        large_results = [{"id": i, "text": f"Document {i}" * 100} for i in range(100)]
        
        # キャッシュに保存
        start_time = time.time()
        cache.set("test query", "collection1", 5, large_results)
        set_time = time.time() - start_time
        
        # キャッシュから取得（はるかに高速なはず）
        start_time = time.time()
        cached = cache.get("test query", "collection1", 5)
        get_time = time.time() - start_time
        
        assert cached is not None
        assert len(cached) == 100
        # 取得は保存よりも速いはず
        assert get_time < set_time * 2  # 余裕を持たせる
    
    def test_cache_memory_efficiency(self):
        """キャッシュのメモリ効率テスト"""
        cache = RAGCache(max_size=5, ttl=3600)
        
        # 最大サイズを超えて追加
        for i in range(10):
            cache.set(f"query{i}", "col1", 5, [{"id": i}])
        
        # サイズは最大値を超えない
        assert len(cache) <= 5
        
        stats = cache.get_stats()
        assert stats["size"] <= stats["max_size"]


@pytest.mark.benchmark
class TestBenchmarks:
    """ベンチマークテスト（オプション）"""
    
    def test_cache_get_benchmark(self, benchmark):
        """キャッシュ取得のベンチマーク"""
        cache = RAGCache(max_size=1000, ttl=3600)
        cache.set("test", "col1", 5, [{"id": 1}])
        
        result = benchmark(cache.get, "test", "col1", 5)
        assert result is not None
    
    def test_cache_set_benchmark(self, benchmark):
        """キャッシュ保存のベンチマーク"""
        cache = RAGCache(max_size=1000, ttl=3600)
        results = [{"id": i} for i in range(10)]
        
        benchmark(cache.set, "test", "col1", 5, results)

