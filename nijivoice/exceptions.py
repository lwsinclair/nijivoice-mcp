class NijiVoiceError(Exception):
    """にじボイスAPIの基本例外クラス"""
    pass

class NijiVoiceAPIError(NijiVoiceError):
    """にじボイスAPIからのエラーレスポンス"""
    
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)