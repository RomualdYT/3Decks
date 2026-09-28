"""Generate the required banner audio without an unsolicited HOME-menu jingle."""
import sys
import wave

with wave.open(sys.argv[1], "wb") as audio:
    audio.setnchannels(1)
    audio.setsampwidth(2)
    audio.setframerate(22050)
    audio.writeframes(bytes(2205 * 2))
