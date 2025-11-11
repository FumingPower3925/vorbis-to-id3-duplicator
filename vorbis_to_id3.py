"""
MusicBrainz Picard Plugin: Vorbis to ID3 Duplicator

This plugin copies all Vorbis comment tags (including cover art) to ID3v2 tags
in FLAC files for increased compatibility with software that may not read
Vorbis comments properly.
"""

PLUGIN_NAME = 'Vorbis to ID3 Duplicator'
PLUGIN_AUTHOR = 'Albert Bausili Fernández'
PLUGIN_DESCRIPTION = 'Copies all Vorbis comment tags (including cover art) to ID3v2 tags in FLAC files for increased compatibility'
PLUGIN_VERSION = '1.0.0'
PLUGIN_API_VERSIONS = ['2.6', '2.7', '2.8', '2.9', '2.10', '2.11', '2.12', '2.13', '2.14', '2.15']
PLUGIN_LICENSE = 'MIT'
PLUGIN_LICENSE_URL = 'https://opensource.org/licenses/MIT'

from picard import log
from picard.file import File
from mutagen.flac import FLAC
from mutagen.id3 import (
    ID3, ID3NoHeaderError,
    TIT2, TPE1, TALB, TPE2, TDRC, TRCK, TCON, COMM,
    TCOM, TENC, TCOP, TIT1, TIT3, TPOS, TPE3, TPE4,
    TSO2, TSOA, TSOP, TSOT, TSST, APIC, TXXX
)


# Tag mapping from Vorbis comment field names to ID3v2 frame constructors
VORBIS_TO_ID3_MAPPING = {
    'TITLE': TIT2,
    'ARTIST': TPE1,
    'ALBUM': TALB,
    'ALBUMARTIST': TPE2,
    'DATE': TDRC,
    'YEAR': TDRC,
    'TRACKNUMBER': TRCK,
    'TRACK': TRCK,
    'GENRE': TCON,
    'COMMENT': COMM,
    'COMPOSER': TCOM,
    'ENCODEDBY': TENC,
    'COPYRIGHT': TCOP,
    'CONTENTGROUP': TIT1,
    'SUBTITLE': TIT3,
    'DISCNUMBER': TPOS,
    'CONDUCTOR': TPE3,
    'REMIXER': TPE4,
    'ALBUMSORT': TSOA,
    'ALBUMARTISTSORT': TSO2,
    'ARTISTSORT': TSOP,
    'TITLESORT': TSOT,
    'DISCSUBTITLE': TSST,
}


def copy_vorbis_to_id3(file: File) -> None:
    """
    Copy Vorbis comment tags to ID3v2 tags in FLAC files.
    
    Args:
        file: The Picard file object
    """
    try:
        # Get file path - try different attributes that Picard might use
        file_path = None
        
        # Try common file path attributes
        for attr in ['filename', 'path', '_filename', 'orig_filename']:
            if hasattr(file, attr):
                try:
                    value = getattr(file, attr)
                    if value:
                        file_path = str(value)
                        break
                except:
                    continue
        
        if not file_path:
            log.warning("[VorbisToID3] Could not determine file path, skipping")
            return
        
        # Only process FLAC files
        if not file_path.lower().endswith('.flac'):
            return
        
        log.debug(f"[VorbisToID3] Processing file: {file_path}")
        
        # Open the FLAC file with Mutagen
        try:
            audio = FLAC(file_path)
        except Exception as e:
            log.error(f"[VorbisToID3] Error opening FLAC file {file_path}: {e}")
            return
        
        # Check if file has Vorbis comments
        if not audio.tags:
            log.debug(f"[VorbisToID3] No Vorbis comments found in {file_path}")
            return
        
        # Get or create ID3 tag
        try:
            id3 = ID3(file_path)
        except ID3NoHeaderError:
            id3 = ID3()
            log.debug(f"[VorbisToID3] Creating new ID3 tag for {file_path}")
        except Exception as e:
            log.error(f"[VorbisToID3] Error reading ID3 tags from {file_path}: {e}")
            return
        
        # Copy standard tags
        tags_copied = 0
        for vorbis_key, id3_frame_class in VORBIS_TO_ID3_MAPPING.items():
            if vorbis_key in audio.tags:
                values = audio.tags[vorbis_key]
                if values:
                    # Handle special cases
                    if id3_frame_class == TDRC:
                        # DATE/YEAR -> TDRC (ID3v2.4 date format)
                        date_value = str(values[0])
                        # Try to extract year if full date is provided
                        if len(date_value) >= 4:
                            year = date_value[:4]
                            try:
                                id3.add(TDRC(encoding=3, text=year))
                                tags_copied += 1
                            except Exception as e:
                                log.warning(f"[VorbisToID3] Error adding TDRC: {e}")
                    elif id3_frame_class == TRCK:
                        # TRACKNUMBER -> TRCK (format: "track/total")
                        track_value = str(values[0])
                        # Extract just the track number if format is "1/10"
                        if '/' in track_value:
                            track_value = track_value.split('/')[0]
                        try:
                            id3.add(TRCK(encoding=3, text=track_value))
                            tags_copied += 1
                        except Exception as e:
                            log.warning(f"[VorbisToID3] Error adding TRCK: {e}")
                    elif id3_frame_class == TPOS:
                        # DISCNUMBER -> TPOS (format: "disc/total")
                        disc_value = str(values[0])
                        if '/' in disc_value:
                            disc_value = disc_value.split('/')[0]
                        try:
                            id3.add(TPOS(encoding=3, text=disc_value))
                            tags_copied += 1
                        except Exception as e:
                            log.warning(f"[VorbisToID3] Error adding TPOS: {e}")
                    elif id3_frame_class == COMM:
                        # COMMENT -> COMM
                        comment_text = str(values[0])
                        try:
                            id3.add(COMM(encoding=3, lang='eng', desc='', text=comment_text))
                            tags_copied += 1
                        except Exception as e:
                            log.warning(f"[VorbisToID3] Error adding COMM: {e}")
                    else:
                        # Standard text frames
                        try:
                            frame = id3_frame_class(encoding=3, text=[str(v) for v in values])
                            id3.add(frame)
                            tags_copied += 1
                        except Exception as e:
                            log.warning(f"[VorbisToID3] Error adding {id3_frame_class.__name__}: {e}")
        
        # Copy cover art (pictures)
        pictures_copied = 0
        if audio.pictures:
            for picture in audio.pictures:
                try:
                    # Create APIC frame from FLAC picture
                    apic = APIC(
                        encoding=3,
                        mime=picture.mime or 'image/jpeg',
                        type=picture.type or 3,  # 3 = Cover (front)
                        desc=picture.desc or 'Cover',
                        data=picture.data
                    )
                    id3.add(apic)
                    pictures_copied += 1
                    log.debug(f"[VorbisToID3] Copied cover art: {picture.mime}, type={picture.type}")
                except Exception as e:
                    log.warning(f"[VorbisToID3] Error copying cover art: {e}")
        
        # Copy custom/non-standard tags as TXXX frames
        custom_tags_copied = 0
        for key in audio.tags.keys():
            if key not in VORBIS_TO_ID3_MAPPING and key != 'METADATA_BLOCK_PICTURE':
                try:
                    values = audio.tags[key]
                    if values:
                        # Create TXXX frame for custom tag
                        txxx = TXXX(encoding=3, desc=key, text=[str(v) for v in values])
                        id3.add(txxx)
                        custom_tags_copied += 1
                except Exception as e:
                    log.warning(f"[VorbisToID3] Error copying custom tag {key}: {e}")
        
        # Save ID3 tags to file
        if tags_copied > 0 or pictures_copied > 0 or custom_tags_copied > 0:
            try:
                id3.save(file_path, v2_version=3)  # Use ID3v2.3 for better compatibility
                log.info(
                    f"[VorbisToID3] Successfully copied {tags_copied} tags, "
                    f"{pictures_copied} pictures, and {custom_tags_copied} custom tags to {file_path}"
                )
            except Exception as e:
                log.error(f"[VorbisToID3] Error saving ID3 tags to {file_path}: {e}")
        else:
            log.debug(f"[VorbisToID3] No tags to copy for {file_path}")
    
    except Exception as e:
        log.error(f"[VorbisToID3] Error processing file: {e}", exc_info=True)


# Register the plugin processor
# Based on examples from https://github.com/metabrainz/picard-plugins
try:
    from picard.file import register_file_post_save_processor
    register_file_post_save_processor(copy_vorbis_to_id3)
    log.debug("[VorbisToID3] Plugin registered successfully")
except ImportError:
    # If the function doesn't exist, try alternative registration
    try:
        # Try importing from a different location
        import picard.file as picard_file
        if hasattr(picard_file, 'register_file_post_save_processor'):
            picard_file.register_file_post_save_processor(copy_vorbis_to_id3)
            log.debug("[VorbisToID3] Plugin registered successfully (alternative import)")
        else:
            log.warning("[VorbisToID3] register_file_post_save_processor not found - plugin will not work")
    except Exception as e:
        log.warning(f"[VorbisToID3] Could not register plugin: {e}")
except Exception as e:
    # Don't crash on registration errors - just log them
    log.warning(f"[VorbisToID3] Error registering plugin: {e}")
