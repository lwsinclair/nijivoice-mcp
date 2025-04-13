from nijivoice.models import VoiceActor, VoiceGenerationRequest, RecommendedParameters

def test_models():
    # RecommendedParametersのテスト
    recommended_params = RecommendedParameters(
        emotionalLevel=1.0,
        soundDuration=1.0
    )
    print(f"RecommendedParameters: {recommended_params}")
    
    # VoiceActorのテスト
    voice_actor = VoiceActor(
        id="test_id",
        name="Test Actor",
        description="Test description",
        sampleAudioUrl="https://example.com/sample.mp3",
        imageUrl="https://example.com/image.jpg",
        recommendedParameters=recommended_params
    )
    print(f"VoiceActor: {voice_actor}")
    
    # VoiceGenerationRequestのテスト
    request = VoiceGenerationRequest(
        script="こんにちは",
        speed=1.0,
        emotionalLevel=1.0,
        soundDuration=1.0,
        format="mp3"
    )
    print(f"VoiceGenerationRequest: {request}")
    print(f"JSON: {request.model_dump(by_alias=True)}")

if __name__ == "__main__":
    test_models()
