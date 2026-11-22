# Maatrubhumi: fan-made Hindi tribute trailer

A roughly 90-second cinematic tribute to the film *Maatrubhumi: May War Rest in Peace*, narrated in Hindi with Hindi captions.

| File | What it is |
| --- | --- |
| `script.json` | The Hindi narration, 18 lines in 7 sections, with on-screen text and fact notes |
| `scene.py` | The film: one camera over one dark world, with every element drawn in code |
| `make_score.py` | The original score, synthesised to fit the narration timing |
| `film.env` | Render settings: Hindi Piper voice (deeper), captions, label, thumbnail, draft length |
| `fonts/` | Teko Bold (Devanagari and Latin, OFL) |
| `CREDITS.md` | Credits, licences and the sources behind every fact |

## Render it
The **Render film** workflow renders this folder whenever it changes on `main`. While `film.env` has
`PREVIEW=30`, only the first 30 seconds are rendered. Delete that line and push to render the full film.
You can also run it by hand: **Actions → Render film → Run workflow**, with film `maatrubhumi`.

The results are published as a GitHub Release:
- the 1080p MP4, clean and with Hindi captions
- the Hindi SRT
- the voice-over
- the thumbnail
- the credits
