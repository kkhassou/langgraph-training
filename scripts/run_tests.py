#!/usr/bin/env python3
"""テスト実行スクリプト（Python版）

使用例:
    python scripts/run_tests.py
    python scripts/run_tests.py --type unit
    python scripts/run_tests.py --type integration --no-coverage
    python scripts/run_tests.py --markers "not slow"
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(
    test_type: str = "all",
    coverage: bool = True,
    markers: str = None,
    verbose: bool = True,
    parallel: bool = False
) -> int:
    """テストを実行
    
    Args:
        test_type: テストタイプ（all, unit, integration）
        coverage: カバレッジを測定するか
        markers: pytestマーカー
        verbose: 詳細出力するか
        parallel: 並列実行するか（pytest-xdistが必要）
    
    Returns:
        終了コード（0: 成功, 1以上: 失敗）
    """
    # プロジェクトルートを取得
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("=" * 60)
    print("  LangGraph Training - Test Suite")
    print("=" * 60)
    print()
    print(f"Test Type: {test_type}")
    print(f"Coverage: {coverage}")
    if markers:
        print(f"Markers: {markers}")
    print()
    
    # pytestコマンドの構築
    cmd = ["pytest"]
    
    # テストタイプに応じてパスを指定
    if test_type == "unit":
        cmd.extend(["tests/", "-m", "not integration"])
    elif test_type == "integration":
        cmd.extend(["tests/integration/", "-m", "integration"])
    elif test_type == "all":
        cmd.append("tests/")
    else:
        print(f"❌ Unknown test type: {test_type}")
        print("Usage: python run_tests.py --type [all|unit|integration]")
        return 1
    
    # 基本オプション
    if verbose:
        cmd.append("-v")
    cmd.extend(["--tb=short", "--color=yes"])
    
    # カバレッジオプション
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-branch"
        ])
    
    # カスタムマーカー
    if markers:
        cmd.extend(["-m", markers])
    
    # 並列実行
    if parallel:
        try:
            import xdist  # noqa
            cmd.extend(["-n", "auto"])
        except ImportError:
            print("⚠️  pytest-xdist not installed, running serially")
    
    # テスト実行
    print(f"Running command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            check=False
        )
        
        print()
        if result.returncode == 0:
            print("=" * 60)
            print("  ✅ All tests passed!")
            print("=" * 60)
            print()
            
            if coverage:
                print("Coverage report generated:")
                print("  - HTML: htmlcov/index.html")
                print("  - XML: coverage.xml")
                print()
        else:
            print("=" * 60)
            print("  ❌ Tests failed!")
            print("=" * 60)
            print()
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\n❌ Error running tests: {e}")
        return 1


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Run tests for LangGraph Training project"
    )
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    parser.add_argument(
        "--markers",
        type=str,
        help="Pytest markers to filter tests"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )
    
    args = parser.parse_args()
    
    exit_code = run_tests(
        test_type=args.type,
        coverage=not args.no_coverage,
        markers=args.markers,
        verbose=not args.quiet,
        parallel=args.parallel
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

