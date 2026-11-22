#!/usr/bin/env bash
# Renders one cinematic-film project end to end on a CI runner (no keys, no paid services).
#
#   render-film.sh <film> <out-dir>
#
# <film>   "example"  the Wright brothers documentary that ships with the skill
#          "starter"  the blank starter explainer
#          <name>     a project folder in films/<name>/ (script.json, photos.json, scene.py, ...)
#
# Settings, lowest to highest priority: defaults here, films/<name>/film.env, then INPUT_* from "Run workflow".
#   SIZE         1920x1080 (default) or 1280x720 / 3840x2160 / 1080x1920
#   CAPTIONS     highlighter (default) | clean | paper | redbar | none
#   VOICE        piper (default, natural free neural voice) | espeak (robotic, very fast)
#   PIPER_VOICE  Piper voice name, default en_US-ryan-high; PIPER_FALLBACK tried if it can't be downloaded
#   VOICE_PITCH  <1 for a deeper voice (0.88 ~ two semitones down); VOICE_PACE >1 for a slower read
#   TARGET       optional film length in seconds (build_narration.py --target)
#   PREVIEW      render only the first N seconds (a draft to approve before the full film)
#   MIX_ARGS     extra mix_soundtrack.py arguments (music and effects levels)
#   LABEL        small text burned into the top-right corner of every frame (e.g. "FAN-MADE TRIBUTE")
#   THUMB_T      time of the thumbnail still in seconds; negative counts back from the end
#   CRF          video quality, lower = bigger files (default 18; grain makes 16 very large)
# A project can also ship make_score.py (writes audio/score.wav from the timing) or audio/score.mp3|m4a|wav.
set -euo pipefail

FILM="$1"
OUT="$2"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
S="$ROOT/skills/cinematic-film/scripts"
P="${RUNNER_TEMP:-/tmp}/film-$FILM"

SIZE=1920x1080; CAPTIONS=highlighter; VOICE=piper; PIPER_VOICE=en_US-ryan-high; PIPER_FALLBACK=""
VOICE_PITCH=1.0; VOICE_PACE=1.0; TARGET=""; PREVIEW=""; MIX_ARGS=""; LABEL=""; THUMB_T=""; CRF=18
if [ -f "$ROOT/films/$FILM/film.env" ]; then
  # shellcheck disable=SC1090
  set -a; . "$ROOT/films/$FILM/film.env"; set +a
fi
for v in SIZE CAPTIONS VOICE PIPER_VOICE TARGET PREVIEW; do
  iv="INPUT_$v"; [ -n "${!iv:-}" ] && printf -v "$v" '%s' "${!iv}"
done
echo "film=$FILM size=$SIZE captions=$CAPTIONS voice=$VOICE/$PIPER_VOICE pitch=$VOICE_PITCH preview=${PREVIEW:-full}"

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
  for v in "$PIPER_VOICE" $PIPER_FALLBACK; do
    [ -f "$VOICES/$v.onnx" ] || python -m piper.download_voices --download-dir "$VOICES" "$v" || true
    if [ -f "$VOICES/$v.onnx" ]; then MODEL="$VOICES/$v.onnx"; echo "voice: $v"; break; fi
  done
  if [ -n "${MODEL:-}" ]; then
    python "$S/tts_say.py" --project "$P" \
      --cmd "python '$ROOT/.github/scripts/piper_take.py' --model '$MODEL' --txt {txt} --out {out} --pitch $VOICE_PITCH --length-scale $VOICE_PACE"
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

step "Sound effects, score and mix"
python "$S/render.py" --project "$P" --cues
python "$S/build_sfx.py" --project "$P"
if [ -f "$P/make_score.py" ]; then
  (cd "$P" && python make_score.py --project "$P")
fi
MUSIC=""
for f in "$P"/audio/score.mp3 "$P"/audio/score.m4a "$P"/audio/score.wav; do
  [ -f "$f" ] && MUSIC="$f" && break
done
# shellcheck disable=SC2086
if [ -n "$MUSIC" ]; then
  python "$S/mix_soundtrack.py" --project "$P" --music "$MUSIC" $MIX_ARGS
else
  python "$S/mix_soundtrack.py" --project "$P" $MIX_ARGS
fi
end

RANGE=(); NAME="$FILM"; KIND=film
if [ -n "$PREVIEW" ]; then RANGE=(--t0 0 --t1 "$PREVIEW"); NAME="$FILM-preview"; KIND=preview; fi
[ -n "${GITHUB_OUTPUT:-}" ] && { echo "kind=$KIND"; echo "preview=$PREVIEW"; } >> "$GITHUB_OUTPUT"

step "Render $SIZE ${PREVIEW:+(first ${PREVIEW}s)}"
python "$S/render.py" --project "$P" --size "$SIZE" "${RANGE[@]}" --crf "$CRF" --out out/film.mp4 --audio audio/mix.m4a
end

if [ -n "$LABEL" ]; then
  step "Label: $LABEL"
  FONT="$P/fonts/cond.ttf"; [ -f "$FONT" ] || FONT="$(fc-match -f '%{file}' 'DejaVu Sans:bold')"
  H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$P/out/film.mp4")
  printf '%s' "$LABEL" > "$P/out/label.txt"
  ffmpeg -y -v error -i "$P/out/film.mp4" -vf \
    "drawtext=fontfile='$FONT':textfile='$P/out/label.txt':fontsize=$((H * 26 / 1000)):fontcolor=white@0.62:x=w-tw-$((H * 30 / 1000)):y=$((H * 30 / 1000)):shadowcolor=black@0.6:shadowx=2:shadowy=2" \
    -c:v libx264 -preset veryfast -crf "$CRF" -pix_fmt yuv420p -c:a copy "$P/out/film_l.mp4"
  mv "$P/out/film_l.mp4" "$P/out/film.mp4"
  end
fi

step "Captions ($CAPTIONS)"
python "$S/burn_captions.py" --project "$P" --srt-only --out out/film.srt
if [ "$CAPTIONS" != "none" ]; then
  python "$S/burn_captions.py" --project "$P" --video out/film.mp4 --audio audio/mix.m4a \
    --style "$CAPTIONS" --crf "$CRF" --out out/film_captions.mp4
fi
end

if [ -n "$THUMB_T" ]; then
  step "Thumbnail"
  T=$(python -c "import json; d=json.load(open('$P/audio/timing.json'))['total_duration']; t=float('$THUMB_T'); print(round(d + t if t < 0 else t, 2))")
  rm -rf "$P/out/probe"
  python "$S/render.py" --project "$P" --probe "$T" --size 1280x720
  cp "$(ls "$P"/out/probe/*.png | head -1)" "$P/out/thumbnail.png"
  if [ -n "$LABEL" ]; then
    FONT="$P/fonts/cond.ttf"; [ -f "$FONT" ] || FONT="$(fc-match -f '%{file}' 'DejaVu Sans:bold')"
    ffmpeg -y -v error -i "$P/out/thumbnail.png" -vf \
      "drawtext=fontfile='$FONT':textfile='$P/out/label.txt':fontsize=19:fontcolor=white@0.7:x=w-tw-22:y=22" "$P/out/thumb_l.png"
    mv "$P/out/thumb_l.png" "$P/out/thumbnail.png"
  fi
  end
fi

step "Collect outputs"
mkdir -p "$OUT"
cp "$P/out/film.mp4" "$OUT/$NAME.mp4"
[ -f "$P/out/film_captions.mp4" ] && cp "$P/out/film_captions.mp4" "$OUT/$NAME-captions.mp4"
cp "$P/out/film.srt" "$OUT/$NAME.srt"
cp "$P/audio/narration.m4a" "$OUT/$NAME-voiceover.m4a"
[ -f "$P/out/thumbnail.png" ] && cp "$P/out/thumbnail.png" "$OUT/$NAME-thumbnail.png"
# release file names ignore case: a hand-written CREDITS.md wins over the generated image credits.md
if [ -f "$P/CREDITS.md" ]; then cp "$P/CREDITS.md" "$OUT/$NAME-credits.md"
elif [ -f "$P/credits.md" ]; then cp "$P/credits.md" "$OUT/$NAME-credits.md"; fi
[ -f "$P/beats.md" ] && cp "$P/beats.md" "$OUT/$NAME-beats.md"
ls -la "$OUT"
end
