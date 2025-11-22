"""Document Provider Interface - ドキュメントプロバイダーの抽象インターフェース"""

from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel, Field


class SlideContent(BaseModel):
    """スライドコンテンツ
    
    Attributes:
        slide_number: スライド番号（1から始まる）
        title: スライドのタイトル
        content: スライドの本文（複数の段落）
        notes: スライドノート
    """
    slide_number: int = Field(..., description="スライド番号")
    title: str = Field(default="", description="スライドタイトル")
    content: List[str] = Field(default_factory=list, description="本文内容")
    notes: str = Field(default="", description="スライドノート")


class DocumentProvider(ABC):
    """ドキュメントプロバイダーの抽象インターフェース
    
    各種ドキュメントフォーマット（PPT, PDF, Wordなど）からの
    テキスト抽出を統一的に扱うインターフェース。
    
    Example:
        >>> provider = PPTProvider()
        >>> slides = await provider.extract_from_ppt("presentation.pptx")
        >>> text = provider.format_slides_as_text(slides)
        >>> print(text)
    """
    
    @abstractmethod
    async def extract_from_ppt(self, file_path: str) -> List[SlideContent]:
        """PowerPointファイルからテキストを抽出
        
        Args:
            file_path: PPTファイルのパス
        
        Returns:
            スライドコンテンツのリスト
        
        Raises:
            FileNotFoundError: ファイルが見つからない場合
            Exception: 抽出に失敗した場合
        
        Example:
            >>> slides = await provider.extract_from_ppt("deck.pptx")
            >>> for slide in slides:
            ...     print(f"Slide {slide.slide_number}: {slide.title}")
        """
        pass
    
    @abstractmethod
    def format_slides_as_text(self, slides: List[SlideContent]) -> str:
        """スライドをテキスト形式にフォーマット
        
        Args:
            slides: スライドコンテンツのリスト
        
        Returns:
            フォーマットされたテキスト
        
        Example:
            >>> text = provider.format_slides_as_text(slides)
            >>> print(text)
            --- Slide 1 ---
            Title: Introduction
            Content:
              - Welcome
              - Agenda
        """
        pass

