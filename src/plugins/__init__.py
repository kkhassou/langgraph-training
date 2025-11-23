"""Plugins Directory

このディレクトリには、動的に読み込まれるプラグインが配置されます。

プラグインの作成方法:
    1. このディレクトリ配下に新しいディレクトリを作成
    2. __init__.py を作成し、プロバイダークラスとメタデータを定義
    3. アプリケーション起動時に自動的に読み込まれます

Example:
    src/plugins/
    ├── __init__.py
    ├── custom_llm/
    │   ├── __init__.py
    │   └── provider.py
    └── custom_rag/
        ├── __init__.py
        └── provider.py
"""

