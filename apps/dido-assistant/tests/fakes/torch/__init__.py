"""시험용 가짜 torch(그래픽카드 없음)."""
bfloat16 = "bfloat16"
float32 = "float32"


class cuda:
    @staticmethod
    def is_available():
        return False
