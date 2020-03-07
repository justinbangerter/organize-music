#!/usr/bin/python

import argparse
import mimetypes
import os
import re
import shutil
import string
import sys

import mutagen

class FileFriendlyString(str):
    def __new__(self, x):
        return str.__new__(
            self,
            re.sub('[\/]', '_', x)
        )

if __name__ == '__main__':
    def directory(dirname):
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
        '--ignore-artist',
        action='store_true',
        help='ignore the artist',
    )
    parser.add_argument(
        '--capwords',
        action='store_true',
        help='(experimental) Capitalize the first letter of all words in artist, album, and track names',
    )

    args = parser.parse_args()

    for dirname, subdirs, filenames in os.walk(args.src):
        for filename in filenames:
            src_file = os.path.join(dirname, filename)
            try:
                f = mutagen.File(src_file, easy=True)
            except mutagen.mp3.HeaderNotFoundError:
                print('Possibly corrupted: ' + src_file)
                continue
            except mutagen.id3._util.error:
                print('Possibly corrupted: ' + src_file)
                continue

            #not a file we care about
            if not f:
                #GTFO
                if filename == 'desktop.ini':
                    os.remove(src_file)
                continue

            is_audio = len([
                x for x in f.mime
                if x.startswith('audio/')
            ])
            if not is_audio:
                print('Not an audio file: ' + src_file)
                continue

            exts = [
                mimetypes.guess_extension(mt)
                for mt in f.mime
            ]
            #filter None get first
            ext = [
                ext
                for ext in exts
                if ext
            ][0]

            #Possible Keys from EasyID3
            #import mutagen
            #sorted(mutagen.easyid3.EasyID3.valid_keys.keys())

            #Don't bother sorting if we don't have what we want
            if not f.get('title'): continue
            title = FileFriendlyString(f.get('title')[0])

            path = args.out
            if not args.ignore_artist:
                if not f.get('artist'): continue
                artist = FileFriendlyString(f.get('artist')[0])
                if args.capwords:
                    artist = string.capwords(artist)
                path = os.path.join(path, artist)
            if f.get('album'):
                album = FileFriendlyString(f.get('album')[0])
                if args.capwords:
                    album = string.capwords(album)
                path = os.path.join(path, album)
            os.makedirs(path, exist_ok=True)

            songtitle = title + ext
            try:
                if f.get('tracknumber'):
                    songtitle = '{:02d} {}'.format(
                        int(f.get('tracknumber')[0]), songtitle
                    )
            except ValueError:
                #couldn't parse the track number, probably
                continue
            if args.capwords:
                songtitle = string.capwords(songtitle)
            songpath = os.path.join(path, songtitle)

            #already where it belongs
            if songpath == src_file: continue

            if os.path.exists(songpath):
                if args.overwrite:
                    shutil.move(src_file, songpath)
                elif args.discard:
                    os.remove(src_file)
                else:
                    print('File already exists: ' + songpath)
            else:
                shutil.move(src_file, songpath)

        #if the current dir is now empty, remove it
        try:
            os.rmdir(dirname)
        except OSError:
            continue

