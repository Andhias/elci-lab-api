from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    brand_id: str | None = None
    model_id: str | None = None
    controller_id: str | None = None
    uploaded_asset_ids: list[str] = Field(default_factory=list)


class ChatMessageRequest(BaseModel):
    message: str
    input_mode: str = "text"
    context: ChatContext = Field(default_factory=ChatContext)


class Presentation(BaseModel):
    tts_text: str | None = None
    avatar_state: str | None = None
    tone: str | None = None


class ChatCheck(BaseModel):
    step: int
    action: str
    expected_result: str


class Citation(BaseModel):
    document_id: str
    title: str
    page: int | str


class TechnicalAnswer(BaseModel):
    issue_summary: str
    match_type: str
    confidence: str
    preconditions: list[str]
    checks: list[ChatCheck]
    warnings: list[str]
    citations: list[Citation]
    needs_more_info: bool
    requested_missing_info: list[str]
    presentation: Presentation | None = None


class ChatTurn(BaseModel):
    role: str
    content: str
    match_type: str | None = None
    confidence: str | None = None
    citation_count: int = 0


class ChatMessageResponse(BaseModel):
    message_id: str
    session_id: str
    answer: TechnicalAnswer
    history: list[ChatTurn] = Field(default_factory=list)


class ChatSessionCreateRequest(BaseModel):
    title: str | None = None


class ChatSessionResponse(BaseModel):
    id: str
    title: str | None = None
    history: list[ChatTurn] = Field(default_factory=list)


class ChatSessionSummary(BaseModel):
    id: str
    title: str | None = None
    updated_at: str | None = None
    last_message_preview: str | None = None
    message_count: int = 0


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionSummary] = Field(default_factory=list)
