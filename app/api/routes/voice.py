from fastapi import APIRouter

from app.schemas.voice import AvatarConfigResponse, TtsRequest, TtsResponse

router = APIRouter(tags=["voice"])


@router.get("/avatars/config", response_model=AvatarConfigResponse)
def avatar_config() -> AvatarConfigResponse:
    return AvatarConfigResponse(
        avatar_theme="industrial_safety_assistant",
        idle_state="idle",
        listening_state="listening",
        thinking_state="thinking",
        speaking_state="speaking",
        safety_outfit_palette=["#FFC107", "#FF6F00", "#263238"],
    )


@router.post("/voice/tts", response_model=TtsResponse)
def voice_tts(payload: TtsRequest) -> TtsResponse:
    _ = payload
    return TtsResponse(
        audio_url="https://example.local/audio/demo-tts.mp3",
        avatar_state="speaking",
    )
