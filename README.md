# Vorbis to ID3 Duplicator

A MusicBrainz Picard plugin that copies all Vorbis comment tags (including cover art) to ID3v2 tags in FLAC files for increased compatibility with software that may not read Vorbis comments properly.

## Features

- Automatically copies all Vorbis comment tags to ID3v2 tags when saving FLAC files in Picard
- Handles standard tags: title, artist, album, album artist, track number, date, genre, etc.
- Copies embedded cover art from Vorbis comments to ID3v2 APIC frames
- Preserves custom/non-standard tags as TXXX frames
- Compatible with MusicBrainz Picard 2.6+

## Installation

### Method 1: Manual Installation

1. **Locate Picard's Plugin Directory:**
   - **macOS**: `~/Library/Preferences/MusicBrainz/Picard/plugins/`
   - **Linux**: `~/.config/MusicBrainz/Picard/plugins/`
   - **Windows**: `%APPDATA%\MusicBrainz\Picard\plugins\`
   
   Alternatively, you can find it through Picard:
   - Open Picard
   - Go to **Options** → **Plugins**
   - Click **Open plugin folder** button at the bottom

2. **Copy the Plugin:**
   - Copy `vorbis_to_id3.py` into the plugins directory

3. **Enable the Plugin:**
   - Restart MusicBrainz Picard (if it was running)
   - Go to **Options** → **Plugins**
   - Find "Vorbis to ID3 Duplicator" in the list
   - Check the box next to it to enable it
   - Click **OK**

### Method 2: ZIP Installation

1. Create a ZIP file containing `vorbis_to_id3.py`
2. In Picard, go to **Options** → **Plugins**
3. Click **Install plugin...**
4. Select the ZIP file
5. Enable the plugin in the plugin list

## Usage

Once installed and enabled, the plugin works automatically:

1. Load your FLAC files into MusicBrainz Picard
2. Tag them as usual
3. Click **Save** - the plugin will automatically copy Vorbis comments to ID3v2 tags during the save process

## Verification

To verify the plugin is working:

- Tag a FLAC file with Picard
- Use a tool like `mutagen-inspect` (command line) or a hex editor to check if both Vorbis comments and ID3v2 tags exist in the file
- Try opening the file in software that only reads ID3 tags to see if metadata appears correctly

Example with mutagen-inspect:
```bash
mutagen-inspect your_file.flac
```

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

The plugin uses Picard's `register_file_post_save_processor` API to hook into the file saving process. After Picard saves a FLAC file with Vorbis comments, the plugin:

1. Reads all Vorbis comment tags from the file using Mutagen
2. Maps them to their ID3v2 equivalents
3. Copies embedded cover art from Vorbis picture blocks to ID3v2 APIC frames
4. Writes the ID3v2 tags to the same file (using ID3v2.3 format for maximum compatibility)
5. Preserves custom tags as TXXX frames

The plugin only processes FLAC files and skips files that don't have Vorbis comments.

## Troubleshooting

- **Plugin doesn't appear:** Make sure the file is in the correct plugins directory and Picard was restarted
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