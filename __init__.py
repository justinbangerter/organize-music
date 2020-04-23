#!/usr/bin/python

import argparse
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

class FileFriendlyString(str):
    def __new__(self, x):
        return str.__new__(
            self,
            re.sub('[\/]', '_', x)
        )

class AudioFile(object):
    #Proxy for mutagen files
    def __init__(self, target):
        self._target = target

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

        path = FileFriendlyString(self.artist())
        if self.album():
            path = os.path.join(path, FileFriendlyString(self.album()))

        return os.path.join(path, self.generated_filename())

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
            yield mutagen.File(path, easy=True)
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

def audio_files(mutagen_file_list):
    for mutagen_file in mutagen_file_list:
        if len([
            x for x in mutagen_file.mime
            if x.startswith('audio/')
        ]):
            yield AudioFile(mutagen_file)
        else:
            print('Not an audio file: ' + mutagen_file.filename)



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

    args = parser.parse_args()

    for f in audio_files(
        mutagen_files(
            filtered_files(
                child_paths(
                    args.src
                )
            )
        )
    ):
        if not f.title(): continue
        if not f.artist(): continue
        songpath = os.path.join(args.out, f.generated_path())
        os.makedirs(os.path.dirname(songpath), exist_ok=True)

        #the file is already where it belongs
        if songpath == f.filename: continue

        if os.path.exists(songpath):
            if args.overwrite:
                print(f.filename + ' to ' + songpath)
                shutil.move(f.filename, songpath)
            elif args.discard:
                print('remove ' + f.filename)
                os.remove(f.filename)
            else:
                print('File already exists: ' + songpath)
        else:
            print(f.filename + ' to ' + songpath)
            shutil.move(f.filename, songpath)
