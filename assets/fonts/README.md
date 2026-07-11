Place a Bengali-glyph-covering TTF/OTF here, e.g. `NotoSansBengali-Bold.ttf`
(download from Google Fonts: https://fonts.google.com/noto/specimen/Noto+Sans+Bengali).

`BENGALI_FONT_PATH` in `.env` points at this file. If it's missing, poster
generation degrades gracefully — the bot still sends the processed photo and
captions as separate messages instead of a single composited poster, it just
skips the text-overlay step. Nothing crashes either way.
