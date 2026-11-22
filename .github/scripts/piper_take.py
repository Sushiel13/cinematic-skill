"""Read one take with Piper (free neural TTS) for tts_say.py --cmd.

  python piper_take.py --model en_US-ryan-high.onnx --txt take.txt --out take.wav

tts_say.py writes the take as one narration line per paragraph (blank line between). Piper's own
CLI puts no pause between input lines, but split_takes.py cuts the take at pauses, so each line is
synthesised separately here and joined with a clear pause (and a shorter one between sentences
inside a line).
"""
import argparse
import pathlib
import subprocess
import wave

from piper import PiperVoice, SynthesisConfig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--txt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--line-pause", type=float, default=0.65, help="seconds between narration lines")
    ap.add_argument("--sentence-pause", type=float, default=0.22, help="seconds between sentences in a line")
    ap.add_argument("--length-scale", type=float, default=1.0, help=">1 slower, <1 faster")
    ap.add_argument("--pitch", type=float, default=1.0, help="<1 deeper (0.88 = about two semitones down), same length")
    a = ap.parse_args()

    voice = PiperVoice.load(a.model)
    rate = voice.config.sample_rate
    cfg = SynthesisConfig(length_scale=a.length_scale)
    text = pathlib.Path(a.txt).read_text(encoding="utf-8")
    lines = [" ".join(p.split()) for p in text.split("\n\n") if p.strip()]

    def silence(sec):
        return bytes(int(rate * sec) * 2)  # 16-bit mono

    with wave.open(a.out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for n, line in enumerate(lines):
            if n:
                w.writeframes(silence(a.line_pause))
            for i, chunk in enumerate(voice.synthesize(line, cfg)):
                if i:
                    w.writeframes(silence(a.sentence_pause))
                w.writeframes(chunk.audio_int16_bytes)
        w.writeframes(silence(0.3))

    if abs(a.pitch - 1.0) > 1e-3:
        # lower the pitch without changing the timing: resample down, then stretch back to length
        tmp = a.out + ".pitch.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.out, "-af",
                        f"asetrate={int(rate * a.pitch)},aresample={rate},atempo={1 / a.pitch:.5f}", tmp], check=True)
        pathlib.Path(tmp).replace(a.out)


if __name__ == "__main__":
    main()
