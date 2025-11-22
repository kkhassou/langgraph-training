# Services Layer - 再利用可能なヘルパー関数群

このディレクトリは、Nodes から呼び出される再利用可能なヘルパー関数・サービスを含みます。

## 📊 アーキテクチャにおける位置づけ

```
┌─────────────────────────────────┐
│   Nodes Layer                   │  ← LangGraphノード定義
│   (nodes/primitives/composites) │     (Servicesを使う)
└──────────────┬──────────────────┘
               ↓ 使う
┌─────────────────────────────────┐
│   Services Layer ⭐ ここ！       │  ← 再利用可能な関数群
│   (services/llm/mcp/document)   │     (Pure Helpers)
└──────────────┬──────────────────┘
               ↓ 使う
┌─────────────────────────────────┐
│   Infrastructure Layer          │  ← 技術基盤
│   (embeddings, vector_stores)   │
└─────────────────────────────────┘
```

## 🎯 Services 層の役割

### 目的

- **ノードをシンプルに保つ**: 低レベルの API 呼び出しを Services に分離
- **再利用性**: 複数のノードから同じサービスを使える
- **テストしやすさ**: サービス単体でテスト可能
- **保守性**: 外部 API の変更はサービスのみ修正

### 判断基準

**「この機能は複数のノードから使われるか？」** → YES なら Services

## 📁 ディレクトリ構造

```
src/services/
│
├── llm/                    # LLMサービス
│   ├── __init__.py
│   ├── base.py            # LLMサービス基底クラス
│   └── gemini_service.py  # Geminiヘルパー
│
├── mcp/                    # MCPサービス（予定）
│   ├── __init__.py
│   ├── slack_service.py
│   ├── github_service.py
│   └── ...
│
└── document/               # ドキュメント処理サービス（予定）
    ├── __init__.py
    └── parser_service.py
```

## 💡 使用例

### LLM Services

#### 1. シンプルなテキスト生成

```python
from src.services.llm.gemini_service import GeminiService

# ノード内で使用
class TodoAdvisorNode(BaseNode):
    async def execute(self, input_data):
        prompt = self._create_prompt(input_data["todo"])

        # ✅ 3行で完了！
        advice = await GeminiService.generate(
            prompt=prompt,
            temperature=0.7
        )

        return NodeResult(success=True, data={"advice": advice})
```

#### 2. 構造化された JSON 生成

```python
from src.services.llm.gemini_service import GeminiService
from pydantic import BaseModel

class TodoList(BaseModel):
    todos: List[Dict[str, Any]]

# JSON形式で返答を取得
result = await GeminiService.generate_json(
    prompt="メールからTODOを抽出してください",
    schema=TodoList,
    temperature=0.7
)

print(result.todos)  # Pydanticモデルとして返される
```

#### 3. コンテキスト付き生成（RAG 用）

```python
from src.services.llm.gemini_service import GeminiService

# RAGでの使用
answer = await GeminiService.generate_with_context(
    user_query="機械学習とは？",
    context="機械学習は...（検索結果）",
    system_instruction="専門家として回答してください"
)
```

#### 4. チャット形式での生成

```python
from src.services.llm.gemini_service import GeminiService

response = await GeminiService.chat(
    messages=[
        {"role": "user", "content": "こんにちは"},
        {"role": "assistant", "content": "こんにちは！"},
        {"role": "user", "content": "今日の天気は？"}
    ],
    temperature=0.7
)
```

## 📝 GeminiService API リファレンス

### `GeminiService.generate()`

シンプルなテキスト生成

**パラメータ**:

- `prompt: str` - 入力プロンプト
- `model: str = "gemini-2.0-flash-exp"` - 使用するモデル
- `temperature: float = 0.7` - 生成の多様性（0.0-1.0）
- `max_tokens: Optional[int] = None` - 最大トークン数

**戻り値**: `str` - 生成されたテキスト

### `GeminiService.generate_json()`

構造化された JSON 出力を生成

**パラメータ**:

- `prompt: str` - 入力プロンプト
- `schema: Type[BaseModel]` - Pydantic スキーマ
- `model: str = "gemini-2.0-flash-exp"` - 使用するモデル
- `temperature: float = 0.7` - 生成の多様性

**戻り値**: `BaseModel` - Pydantic モデルのインスタンス

### `GeminiService.generate_with_context()`

コンテキスト付きテキスト生成（RAG 用）

**パラメータ**:

- `user_query: str` - ユーザーの質問
- `context: str` - 参考情報（検索結果など）
- `system_instruction: Optional[str] = None` - システム命令
- `model: str = "gemini-2.0-flash-exp"` - 使用するモデル
- `temperature: float = 0.7` - 生成の多様性

**戻り値**: `str` - 生成されたテキスト

### `GeminiService.chat()`

チャット形式での生成

**パラメータ**:

- `messages: list[Dict[str, str]]` - メッセージ履歴
- `model: str = "gemini-2.0-flash-exp"` - 使用するモデル
- `temperature: float = 0.7` - 生成の多様性

**戻り値**: `str` - 生成されたテキスト

## 🎁 メリット

### Before（Services 層なし）

```python
# 各ノードで36行の重複コード
class TodoAdvisorNode:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    async def execute(self, input_data):
        response = self.model.generate_content(prompt)
        advice = response.text.strip()
        # ...
```

### After（Services 層あり）

```python
# シンプルに15行
class TodoAdvisorNode:
    async def execute(self, input_data):
        prompt = self._create_prompt(input_data["todo"])
        advice = await GeminiService.generate(prompt, temperature=0.7)
        return NodeResult(success=True, data={"advice": advice})
```

**結果**: コードが 60%削減、保守性・テスト性が向上！

## 🚀 今後の拡張

### 他の LLM サービスの追加

```python
# src/services/llm/openai_service.py
class OpenAIService(BaseLLMService):
    async def generate(self, prompt: str, **kwargs) -> str:
        # OpenAI実装
```

### MCP サービスの統合

```python
# src/services/mcp/slack_service.py
class SlackService:
    @staticmethod
    async def send_message(channel: str, text: str) -> Dict[str, Any]:
        # Slack MCP実装
```

## 📚 関連ドキュメント

- [完全なアーキテクチャ設計](../../COMPLETE_ARCHITECTURE.md)
- [Nodes アーキテクチャ](../../NODES_ARCHITECTURE.md)
- [アーキテクチャ概要](../../NODES_ARCHITECTURE_SUMMARY.md)
