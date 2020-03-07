#Organize your music by tag metadata

Reads audio files in a dir for tag metadata, then moves those files.

Has some special handling:
* Avoids overwriting matches and logs by default
* Deletes the dir if empty
* Filters path separators from metadata fields
* Should handle most audio file types, but this hasn't been tested
* Can be set to ignore artists in case you want to process a collaboration album

Known issues:
* If files are corrupted, it just logs the file, ignores it, and continues
* Collaboration albums aren't handled well: right now, it just organizes by default.
* Mixed case isn't handled well. "The Band" and "the band" go into separate dirs.

Planned:
* Better handling for collaboration albums