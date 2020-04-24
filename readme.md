# Bulk rename your music by tag metadata

Reads audio files in a dir for tag metadata, then moves those files.

Something like:

    ~/music/artist/album/01 trackname.mp3

or

    ~/music/Various Artists/album/01 trackname.mp3

## Example:

    $ ln -s $HOME/projects/organize-music/__init__.py ~/bin/organize-music; chmod +x ~/bin/organize-music
    $ organize-music --out ~/music --src ~/download/

For more info, call with -h

## Features:
* Crawls source dir for music files
* Can be set to clean up after itself
* Should handle most audio file types, but this hasn't been tested
* Handles albums with multiple artists

## Known issues:
* If files are corrupted, it just logs the file, ignores it, and continues
* Mixed case isn't handled at all. "The Band" and "the band" go into separate dirs.
* (obviously) Some files don't have all of their metadata, so they can't be handled
* Album art gets ignored, which is a problem if files get moved
* Don't just run this on your music dir and expect it to fix everything. It's better to run it on new downloads.

## Planned:
* Handle album art?
