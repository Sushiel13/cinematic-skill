#!/usr/bin/env bash
# Renders one cinematic-film project end to end on a CI runner (no keys, no paid services).
#
#   render-film.sh <film> <out-dir>
#
# <film>   "example"  the Wright brothers documentary that ships with the skill
#          "starter"  the blank starter explainer
#          <name>     a project folder in films/<name>/ (script.json, photos.json, scene.py, ...)
#
# Settings come from the environment (the workflow sets them):
#   SIZE      1920x1080 (default) or 1280x720 / 3840x2160 / 1080x1920
#   CAPTIONS  highlighter (default) | clean | paper | redbar | none
#   VOICE     piper (default, natural free neural voice) | espeak (robotic, very fast)
#   PIPER_VOICE  Piper voice name, default en_US-ryan-high
#   TARGET    optional film length in seconds (build_narration.py --target)
set -euo pipefail

FILM="$1"
OUT="$2"
SIZE="${SIZE:-1920x1080}"
CAPTIONS="${CAPTIONS:-highlighter}"
VOICE="${VOICE:-piper}"
PIPER_VOICE="${PIPER_VOICE:-en_US-ryan-high}"
TARGET="${TARGET:-}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
S="$ROOT/skills/cinematic-film/scripts"
P="${RUNNER_TEMP:-/tmp}/film-$FILM"
rm -rf "$P"

step() { echo; echo "::group::$*"; }
end() { echo "::endgroup::"; }

step "Project: $FILM"
case "$FILM" in
  example) python "$S/new_project.py" "$P" --example ;;
  starter) python "$S/new_project.py" "$P" ;;
  *)
    [ -f "$ROOT/films/$FILM/script.json" ] || { echo "::error::films/$FILM/script.json not found"; exit 1; }
    mkdir -p "$P" && cp -R "$ROOT/films/$FILM/." "$P/"
    ;;
esac
ls -la "$P"
end

step "Fonts"
python "$S/get_fonts.py" --project "$P"
end

step "Images from Wikimedia Commons (licences recorded)"
python "$S/fetch_commons.py" get --project "$P"
python "$S/fetch_commons.py" credits --project "$P" || true
end

if python - "$P/map.json" <<'PY'
import json, sys
try:
    sys.exit(0 if json.load(open(sys.argv[1])).get("maps") else 1)
except FileNotFoundError:
    sys.exit(1)
PY
then
  step "Maps"
  python "$S/make_map.py" --project "$P"
  end
fi

step "Grade images"
python "$S/prep_assets.py" --project "$P"
end

step "Voice ($VOICE)"
if [ "$VOICE" = "piper" ]; then
  VOICES="${RUNNER_TEMP:-/tmp}/piper-voices"
  mkdir -p "$VOICES"
  if [ ! -f "$VOICES/$PIPER_VOICE.onnx" ]; then
    python -m piper.download_voices --download-dir "$VOICES" "$PIPER_VOICE" || true
  fi
  if [ -f "$VOICES/$PIPER_VOICE.onnx" ]; then
    python "$S/tts_say.py" --project "$P" \
      --cmd "python '$ROOT/.github/scripts/piper_take.py' --model '$VOICES/$PIPER_VOICE.onnx' --txt {txt} --out {out}"
  else
    echo "::warning::Piper voice $PIPER_VOICE could not be downloaded; using espeak-ng"
    python "$S/tts_say.py" --project "$P"
  fi
else
  python "$S/tts_say.py" --project "$P"
fi
python "$S/split_takes.py" --project "$P"
if [ -n "$TARGET" ]; then
  python "$S/build_narration.py" --project "$P" --target "$TARGET"
else
  python "$S/build_narration.py" --project "$P"
fi
python "$S/make_beats.py" --project "$P" || true
end

step "Sound effects and mix"
python "$S/render.py" --project "$P" --cues
python "$S/build_sfx.py" --project "$P"
MUSIC=""
for f in "$P"/audio/score.mp3 "$P"/audio/score.m4a "$P"/audio/score.wav; do
  [ -f "$f" ] && MUSIC="$f" && break
done
if [ -n "$MUSIC" ]; then
  python "$S/mix_soundtrack.py" --project "$P" --music "$MUSIC"
else
  python "$S/mix_soundtrack.py" --project "$P"
fi
end

step "Render $SIZE"
python "$S/render.py" --project "$P" --size "$SIZE" --out out/film.mp4 --audio audio/mix.m4a
end

step "Captions ($CAPTIONS)"
python "$S/burn_captions.py" --project "$P" --srt-only --out out/film.srt
if [ "$CAPTIONS" != "none" ]; then
  python "$S/burn_captions.py" --project "$P" --video out/film.mp4 --audio audio/mix.m4a \
    --style "$CAPTIONS" --out out/film_captions.mp4
fi
end

step "Collect outputs"
mkdir -p "$OUT"
cp "$P/out/film.mp4" "$OUT/$FILM.mp4"
[ -f "$P/out/film_captions.mp4" ] && cp "$P/out/film_captions.mp4" "$OUT/$FILM-captions.mp4"
cp "$P/out/film.srt" "$OUT/$FILM.srt"
[ -f "$P/credits.md" ] && cp "$P/credits.md" "$OUT/$FILM-credits.md"
[ -f "$P/beats.md" ] && cp "$P/beats.md" "$OUT/$FILM-beats.md"
ls -la "$OUT"
end
