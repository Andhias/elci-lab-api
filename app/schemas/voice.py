from pydantic import BaseModel


class AvatarConfigResponse(BaseModel):
    avatar_theme: str
    idle_state: str
    listening_state: str
    thinking_state: str
    speaking_state: str
    safety_outfit_palette: list[str]


class TtsRequest(BaseModel):
    text: str


class TtsResponse(BaseModel):
    audio_url: str
    avatar_state: str
