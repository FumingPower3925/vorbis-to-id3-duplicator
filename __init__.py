"""Vorbis to ID3 Duplicator (MusicBrainz Picard 3 plugin).

Copies all Vorbis comment tags (including cover art) of FLAC files into ID3v2.3 tags
after Picard saves a file, for software that does not read Vorbis comments properly.

The conversion logic is identical to the Picard 2 release (``picard2-v1.0.0``); only the
plugin registration changed for Picard 3's plugin API.
"""

from mutagen.flac import FLAC
from mutagen.id3 import (
    APIC,
    COMM,
    ID3,
    TALB,
    TCOM,
    TCON,
    TCOP,
    TDRC,
    TENC,
    TIT1,
    TIT2,
    TIT3,
    TPE1,
    TPE2,
    TPE3,
    TPE4,
    TPOS,
    TRCK,
    TSO2,
    TSOA,
    TSOP,
    TSOT,
    TSST,
    TXXX,
    ID3NoHeaderError,
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


def copy_vorbis_to_id3(file_path, log):
    """Copy the Vorbis comments and pictures of one FLAC file into ID3v2.3 tags.

    Args:
        file_path: path of the (already saved) FLAC file.
        log: logger-like object with ``debug/info/warning/error`` methods.
    """
    try:
        if not file_path or not str(file_path).lower().endswith('.flac'):
            return
        file_path = str(file_path)
        log.debug(f"[VorbisToID3] Processing file: {file_path}")

        try:
            audio = FLAC(file_path)
        except Exception as e:
            log.error(f"[VorbisToID3] Error opening FLAC file {file_path}: {e}")
            return

        if not audio.tags:
            log.debug(f"[VorbisToID3] No Vorbis comments found in {file_path}")
            return

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
                    if id3_frame_class == TDRC:
                        # DATE/YEAR -> TDRC (keep the year)
                        date_value = str(values[0])
                        if len(date_value) >= 4:
                            try:
                                id3.add(TDRC(encoding=3, text=date_value[:4]))
                                tags_copied += 1
                            except Exception as e:
                                log.warning(f"[VorbisToID3] Error adding TDRC: {e}")
                    elif id3_frame_class == TRCK:
                        # TRACKNUMBER -> TRCK (track number only if "1/10")
                        track_value = str(values[0])
                        if '/' in track_value:
                            track_value = track_value.split('/')[0]
                        try:
                            id3.add(TRCK(encoding=3, text=track_value))
                            tags_copied += 1
                        except Exception as e:
                            log.warning(f"[VorbisToID3] Error adding TRCK: {e}")
                    elif id3_frame_class == TPOS:
                        # DISCNUMBER -> TPOS (disc number only if "1/2")
                        disc_value = str(values[0])
                        if '/' in disc_value:
                            disc_value = disc_value.split('/')[0]
                        try:
                            id3.add(TPOS(encoding=3, text=disc_value))
                            tags_copied += 1
                        except Exception as e:
                            log.warning(f"[VorbisToID3] Error adding TPOS: {e}")
                    elif id3_frame_class == COMM:
                        try:
                            id3.add(COMM(encoding=3, lang='eng', desc='', text=str(values[0])))
                            tags_copied += 1
                        except Exception as e:
                            log.warning(f"[VorbisToID3] Error adding COMM: {e}")
                    else:
                        try:
                            id3.add(id3_frame_class(encoding=3, text=[str(v) for v in values]))
                            tags_copied += 1
                        except Exception as e:
                            log.warning(f"[VorbisToID3] Error adding {id3_frame_class.__name__}: {e}")

        # Copy cover art (pictures)
        pictures_copied = 0
        for picture in audio.pictures:
            try:
                id3.add(APIC(
                    encoding=3,
                    mime=picture.mime or 'image/jpeg',
                    type=picture.type or 3,  # 3 = Cover (front)
                    desc=picture.desc or 'Cover',
                    data=picture.data,
                ))
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
                        id3.add(TXXX(encoding=3, desc=key, text=[str(v) for v in values]))
                        custom_tags_copied += 1
                except Exception as e:
                    log.warning(f"[VorbisToID3] Error copying custom tag {key}: {e}")

        if tags_copied > 0 or pictures_copied > 0 or custom_tags_copied > 0:
            try:
                id3.save(file_path, v2_version=3)  # ID3v2.3 for better compatibility
                log.info(
                    f"[VorbisToID3] Successfully copied {tags_copied} tags, "
                    f"{pictures_copied} pictures, and {custom_tags_copied} custom tags to {file_path}"
                )
            except Exception as e:
                log.error(f"[VorbisToID3] Error saving ID3 tags to {file_path}: {e}")
        else:
            log.debug(f"[VorbisToID3] No tags to copy for {file_path}")

    except Exception as e:
        log.error(f"[VorbisToID3] Error processing file: {e}")


def on_file_saved(api, file):
    """Picard 3 post-save hook: ``api`` is injected by Picard, ``file`` is the saved file."""
    copy_vorbis_to_id3(getattr(file, 'filename', None), api.logger)


def enable(api):
    """Called by Picard 3 when the plugin is enabled."""
    api.register_file_post_save_processor(on_file_saved)
    api.logger.debug("[VorbisToID3] Plugin enabled")
