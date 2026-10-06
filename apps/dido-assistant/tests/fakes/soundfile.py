"""시험용 가짜 soundfile."""


def write(buf, data, sr, format="WAV"):
    buf.write(b"RIFF" + str(sr).encode() + b"WAVE" + data)
