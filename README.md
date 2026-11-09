# Vorbis to ID3 Duplicator

A MusicBrainz Picard plugin that copies all Vorbis comment tags (including cover art) to ID3v2 tags in FLAC files for increased compatibility with software that may not read Vorbis comments properly.

## Which version do I need?

| Your Picard | Use | Release | Branch |
|---|---|---|---|
| **3.x** | Picard 3 plugin (`MANIFEST.toml` + `__init__.py`) | [`picard3-v1.0.0`](https://github.com/FumingPower3925/vorbis-to-id3-duplicator/releases/tag/picard3-v1.0.0) | `main` |
| **2.6 – 2.15** | Picard 2 plugin (single `vorbis_to_id3.py`) | [`picard2-v1.0.0`](https://github.com/FumingPower3925/vorbis-to-id3-duplicator/releases/tag/picard2-v1.0.0) | [`picard2`](https://github.com/FumingPower3925/vorbis-to-id3-duplicator/tree/picard2) |

Picard 3 replaced the plugin system, so the Picard 2 plugin does **not** load in Picard 3 (and the other way around). Both versions use the same conversion logic.

## Features

- Automatically copies all Vorbis comment tags to ID3v2.3 tags when saving FLAC files in Picard
- Handles standard tags: title, artist, album, album artist, track number, date, genre, etc.
- Copies embedded cover art from Vorbis comments to ID3v2 APIC frames
- Preserves custom/non-standard tags as TXXX frames
- Leaves the audio and the Vorbis comments untouched

## Installation — Picard 3

**Manually (tested on Picard 3.0.4, macOS arm64):** download `vorbis-to-id3-duplicator-picard3-v1.0.0.zip` from the [`picard3-v1.0.0` release](https://github.com/FumingPower3925/vorbis-to-id3-duplicator/releases/tag/picard3-v1.0.0), unzip it, and copy the `vorbis_to_id3` folder (it contains `MANIFEST.toml` and `__init__.py`) into Picard's `plugins3` directory (macOS: `~/Library/Application Support/MusicBrainz/Picard/plugins3/`). Restart Picard, then tick **Vorbis to ID3 Duplicator** under **Options → Plugins** and click **OK**.

**From the repository URL:** Picard 3 can also install plugins from a git URL (**Options → Plugins → Install Plugin…**, which needs `git`). This repository's root is the plugin, so `https://github.com/FumingPower3925/vorbis-to-id3-duplicator` should work, but this route has not been tested yet.

## Installation — Picard 2.x

See the [`picard2-v1.0.0` release](https://github.com/FumingPower3925/vorbis-to-id3-duplicator/releases/tag/picard2-v1.0.0): copy `vorbis_to_id3.py` into Picard's plugin directory (macOS: `~/Library/Preferences/MusicBrainz/Picard/plugins/`), restart Picard and enable it under **Options → Plugins**, or install the `.zip` from the same release with **Options → Plugins → Install plugin…**.

## Usage

Once installed and enabled, the plugin works automatically:

1. Load your FLAC files into MusicBrainz Picard
2. Tag them as usual
3. Click **Save** - the plugin copies Vorbis comments to ID3v2 tags right after each file is saved

## Verification

To verify the plugin is working:

- Tag a FLAC file with Picard
- Use a tool like `mutagen-inspect` (command line) or a hex editor to check if both Vorbis comments and ID3v2 tags exist in the file
- Try opening the file in software that only reads ID3 tags to see if metadata appears correctly

Example with mutagen-inspect:
```bash
mutagen-inspect your_file.flac
```

## Development

```bash
uv run --no-project --with pytest --with mutagen pytest tests -q
```

The tests build a synthetic FLAC (needs `ffmpeg`), run the conversion and check the ID3 frames, the cover art, and that the audio is bit-identical.

## Tag Mapping

The plugin maps Vorbis comment fields to ID3v2 frames:

| Vorbis Comment | ID3v2 Frame | Description |
|----------------|-------------|-------------|
| TITLE | TIT2 | Song title |
| ARTIST | TPE1 | Artist name |
| ALBUM | TALB | Album name |
| ALBUMARTIST | TPE2 | Album artist |
| DATE/YEAR | TDRC | Release date/year |
| TRACKNUMBER/TRACK | TRCK | Track number |
| GENRE | TCON | Genre |
| COMMENT | COMM | Comments |
| COMPOSER | TCOM | Composer |
| ENCODEDBY | TENC | Encoded by |
| COPYRIGHT | TCOP | Copyright |
| CONTENTGROUP | TIT1 | Content group |
| SUBTITLE | TIT3 | Subtitle |
| DISCNUMBER | TPOS | Disc number |
| CONDUCTOR | TPE3 | Conductor |
| REMIXER | TPE4 | Remixer |
| ALBUMSORT | TSOA | Album sort order |
| ALBUMARTISTSORT | TSO2 | Album artist sort order |
| ARTISTSORT | TSOP | Artist sort order |
| TITLESORT | TSOT | Title sort order |
| DISCSUBTITLE | TSST | Disc subtitle |
| METADATA_BLOCK_PICTURE | APIC | Cover art (embedded images) |

Custom/non-standard tags are preserved as TXXX frames.

## How It Works

The plugin registers a post-save hook (`register_file_post_save_processor`; in Picard 3 via `enable(api)`) so it runs right after Picard saves each file. After Picard saves a FLAC file with Vorbis comments, the plugin:

1. Reads all Vorbis comment tags from the file using Mutagen
2. Maps them to their ID3v2 equivalents
3. Copies embedded cover art from Vorbis picture blocks to ID3v2 APIC frames
4. Writes the ID3v2 tags to the same file (using ID3v2.3 format for maximum compatibility)
5. Preserves custom tags as TXXX frames

The plugin only processes FLAC files and skips files that don't have Vorbis comments.

## Troubleshooting

- **Plugin doesn't appear:** Make sure you installed the version that matches your Picard (see the table above) in the correct plugins directory, and restart Picard
- **Plugin causes errors:** Check Picard's log file for error messages (Help → View Error/Debug Log). Look for `[VorbisToID3]` messages
- **Plugin doesn't work:** 
  - Ensure the plugin is enabled in Options → Plugins
  - Check that your files are FLAC format
  - Verify that the files have Vorbis comments (the plugin only processes files with existing Vorbis tags)
  - Check the Picard log for any error messages

## License

MIT License - see LICENSE file for details

## Author

Albert Bausili Fernández

## My naming script:
```
$set(_title1,$rreplace(%title%,\\\(Instrumental Version\\\),###KEEP1###))
$set(_title2,$rreplace(%_title1%,\\\(Instrumental Ver\\\),###KEEP2###))
$set(_title3,$rreplace(%_title2%,\\\(Instrumental\\\),###KEEP3###))
$set(_title4,$rreplace(%_title3%,\\\(.*?\\\),))
$set(_title5,$replace(%_title4%,###KEEP1###,\(Instrumental Version\)))
$set(_title6,$replace(%_title5%,###KEEP2###,\(Instrumental Ver\)))
$set(_title7,$replace(%_title6%,###KEEP3###,\(Instrumental\)))
$set(_title_final,$replace(%_title7%,  , ))
$if($gt(%totaltracks%,1),$num(%tracknumber%,2) - )%_title_final%
```