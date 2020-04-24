#!/usr/bin/python

import argparse
from collections import defaultdict
import mimetypes
import os
import re
import shutil
import string
import sys

import mutagen

# If we encounter these files, delete them
DELETE_FILES = ['desktop.ini']

class TrackNumberParseFailed(Exception):
    pass

class CompilationSongWithNoAlbum(Exception):
    pass

class FileFriendlyString(str):
    def __new__(self, x):
        return str.__new__(
            self,
            re.sub('[\/]', '_', x)
        )

class AudioFiles(list):
    def __init__(self, mutagen_file_list):
        self.filelist = []
        self.grouped_by_album = defaultdict(list)
        for file in self._generator(mutagen_file_list):
            self.filelist.append(file)
            #skip files without albums
            if file.album():
                self.grouped_by_album[file.album()].append(file)
        self._compilations = self.detect_compilation_albums()

    def _generator(self, mutagen_file_list):
        for mutagen_file in mutagen_file_list:
            if len([
                x for x in mutagen_file.mime
                if x.startswith('audio/')
            ]):
                yield AudioFile(mutagen_file)
            else:
                print('Not an audio file: ' + mutagen_file.filename)

    def multiple_artists(self, songs):
        return len(set([
            song.artist()
            for song in songs
        ])) > 1

    def detect_compilation_albums(self):
        return [
            album_name
            for album_name, songs in self.grouped_by_album.items()
            if len(songs) > 1
            and self.multiple_artists(songs)
        ]

    def confirm_compilations(self):
        for album_title in self._compilations:
            if not args.trust_compilations:
                print('===================')
                print('Album: ' + album_title)
                for song in sorted(self.grouped_by_album[album_title], key=lambda x: x.tracknumber() or 0):
                    print(song.printable())
                print('===================')

            if args.trust_compilations or input('Is this a valid compilation album? [yN]') == 'y':
                for song in self.grouped_by_album[album_title]:
                    song.in_compilation = True


class AudioFile(object):
    #Proxy for mutagen files
    def __init__(self, target):
        self._target = target
        self.in_compilation = False

    def __dir__(self):
        return set(sorted(object.__dir__(self) + dir(self._target)))

    def __getattr__(self, attr):
        return getattr(self._target, attr)

    def extension(self):
        exts = [
            mimetypes.guess_extension(mimetype)
            for mimetype in f.mime
        ]
        #filter None get first
        return [
            ext
            for ext in exts
            if ext
        ][0]

    def generated_filename(self):
        if f.tracknumber():
            return '{:02d} {}'.format(
                f.tracknumber(), f.title() + f.extension()
            )
        return f.title() + f.extension()

    def generated_path(self):
        #Get a path based on this file's metadata
        if self.in_compilation:
            path = FileFriendlyString('Various Artists')

            #if this happens, something is very wrong
            if not self.album():
                raise CompilationSongWithNoAlbum('No album for compilation member: ' + self.filename)

            path = os.path.join(path, FileFriendlyString(self.album().lstrip('.')))
            return os.path.join(path, self.generated_filename())
        else:
            path = FileFriendlyString(self.artist().lstrip('.'))
            if self.album():
                path = os.path.join(path, FileFriendlyString(self.album().lstrip('.')))

            return os.path.join(path, self.generated_filename())

    def printable(self):
        if self.tracknumber():
            return '{:02d} {} by {}'.format(self.tracknumber(), self.title(), self.artist())
        else:
            return '{} by {}'.format(self.title(), self.artist())

    #metadata fields

    def _metadata_first(self, field):
        try:
            return self.get(field)[0]
        except TypeError:
            return None
        except IndexError:
            return None

    def artist(self):
        return self._metadata_first('artist')

    def album(self):
        return self._metadata_first('album')

    def title(self):
        return self._metadata_first('title')

    def tracknumber(self):
        tracknum = self._metadata_first('tracknumber')

        if not tracknum:
            return None

        #song x of y
        if '/' in tracknum:
            tracknum = tracknum.split('/')[0]

        try:
            return int(tracknum)
        except ValueError:
            raise TrackNumberParseFail('Could not parse tracknumber: ' + self.get('tracknumber'))

def child_paths(directory):
    #Walk the dir and dump a list of filepaths for all files in it
    for dirname, subdirs, filenames in os.walk(directory):
        for filename in filenames:
            yield os.path.join(dirname, filename)

def mutagen_files(paths):
    #Transform a list of filepaths to mutagen file objects
    for path in paths:
        try:
            _file = mutagen.File(path, easy=True)
            if _file:
                yield _file
        except mutagen.mp3.HeaderNotFoundError:
            print('Possibly corrupted: ' + path)
        except mutagen.id3._util.error:
            print('Possibly corrupted: ' + path)

def filtered_files(paths):
    for path in paths:
        #GTFO
        if os.path.basename(path) in DELETE_FILES:
            os.remove(path)
        else:
            yield path



if __name__ == '__main__':
    def directory(dirname):
        #validation check and expansion for provided directory
        expanded = os.path.expanduser(dirname)
        if not os.path.isdir(expanded):
            raise argparse.ArgumentTypeError(
                '{} is not a directory'.format(expanded)
            )
        return expanded

    parser = argparse.ArgumentParser(
        'Reorganize music files based on their metadata.'
    )
    parser.add_argument(
        '--src',
        type=directory,
        required=True,
        help='Directory with the files you want to organize',
    )
    parser.add_argument(
        '--out',
        type=directory,
        required=True,
        help='Directory where the files should go',
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='overwrite duplicates',
    )
    parser.add_argument(
        '--discard',
        action='store_true',
        help='discard duplicates',
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='confirm before writing files',
    )
    parser.add_argument(
        '--trust-compilations',
        action='store_true',
        help="Don't bother asking for confirmation about detected compilation albums. Assume the detection was right.",
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='clean up empty directories',
    )

    args = parser.parse_args()

    filepaths = child_paths(args.src)
    audio_files = AudioFiles(
        mutagen_files(
            filtered_files(
                filepaths
            )
        )
    )
    audio_files.confirm_compilations()

    for f in audio_files.filelist:
        if not f.title(): continue
        if not f.artist(): continue
        songpath = os.path.join(args.out, f.generated_path())
        os.makedirs(os.path.dirname(songpath), exist_ok=True)

        #the file is already where it belongs
        if os.path.exists(songpath) and os.path.samefile(songpath, f.filename):
            continue

        #something else is already there
        if os.path.exists(songpath) and not args.confirm:
            if args.overwrite:
                print(f.filename + ' to ' + songpath)
                shutil.move(f.filename, songpath)
            elif args.discard:
                print('remove ' + f.filename)
                os.remove(f.filename)
            else:
                print(f.filename + ' to ' + songpath)
                print('File already exists: ' + songpath)
        else:
            print(f.filename + ' to ' + songpath)
            if args.confirm and input('[yN]') != 'y':
                continue
            shutil.move(f.filename, songpath)

    if args.cleanup:
        for dirname, subdirs, filenames in reversed(list(os.walk(args.src))):
            #reversed so we get subdirs first
            if not os.path.samefile(args.src, dirname):
                try:
                    os.rmdir(dirname)
                except OSError:
                    pass
