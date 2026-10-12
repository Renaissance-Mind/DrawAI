"""Transport-independent image API failure, adapted by CLI/MCP/HTTP."""
class ImageApiError(RuntimeError):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))
