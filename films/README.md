# Films

Each folder here is one film project. Push a change to any `films/<name>/` folder on `main` and the
**Render film** workflow renders it on GitHub's free runners. You can also run it by hand: **Actions → Render film →
Run workflow**, then type the folder name (or `example` for the Wright brothers documentary, or `starter`).

The finished files appear as a **GitHub Release** (download links) and as a workflow artifact:

| File | Use |
| --- | --- |
| `<name>.mp4` | Clean film. Upload to YouTube together with the `.srt`. |
| `<name>-captions.mp4` | Captions burned in, for Shorts, Instagram and WhatsApp. |
| `<name>.srt` | Subtitles. |
| `<name>-credits.md` | Image credits and licences. Paste them in the video description. |
| `<name>-beats.md` | Beat table with timings and script warnings. |

## A film folder

```
films/my-film/
  script.json    narration lines, grouped into takes (what the voice says, what is on screen)
  scene.py       build_film(doc): places items and camera moves on the voice's timing
  photos.json    images: Wikimedia Commons files are downloaded with their licence
  map.json       optional maps
  assets/photos/ optional: your own photos (list them in photos.json with "file")
  audio/score.mp3  optional: music, ducked under the voice automatically
```

`demo/` is the starter explainer, a copy of the skill's template. Copy it to start a new film, or ask
your coding agent (with this skill installed) to write `script.json`, `photos.json` and `scene.py`
for a topic, then push.

## Voice

The workflow narrates with **Piper**, a free neural voice that runs on the runner (default
`en_US-ryan-high`). Pick another one when you run it by hand, for example `en_US-lessac-high`,
`en_GB-alan-medium` or `hi_IN-pratham-medium` (list: huggingface.co/rhasspy/piper-voices). `espeak` is the
fallback: robotic, but very fast.

Nothing in the pipeline needs an API key or a paid service.
