import os
import sys
import libs
import libs.fingerprint as fingerprint

from termcolor import colored
from libs.reader_file import FileReader
from libs.db_sqlite import SqliteDatabase
from libs.config import get_config

config = get_config()
db = SqliteDatabase()
path = "songs/"

for fname in os.listdir(path):

    if fname.endswith(".mp3"):

        reader = FileReader(path + fname)
        audio = reader.parse_audio()

        song = db.get_song_by_filehash(audio['file_hash'])
        song_id = db.add_song(fname, audio['file_hash'])

        print(colored('\n * Song ID = ' + str(song_id), 'white', attrs=['dark']))
        print(colored('   Channels = ' + str(len(audio['channels'])), 'white', attrs=['dark']))
        print(colored('   Song Name = ' + fname, 'white', attrs=['bold']))

        if song:
            hash_count = db.get_song_hashes_count(song_id)

            if hash_count > 0:
                print(colored('   ' + fname + 'already exists in database.', 'red', attrs=['bold']))
                continue

        print(colored('   New song found, starting analysis...', 'green'))

        hashes = set()
        channel_amount = len(audio['channels'])

        for channeln, channel in enumerate(audio['channels']):
            print(colored('   Fingerprinting channel ' + str(channeln+1), attrs=['dark']))

            channel_hashes = fingerprint.fingerprint(channel, Fs=audio['Fs'], plots=config['fingerprint.show_plots'])
            channel_hashes = set(channel_hashes)

            print(colored('   Finished fingerprinting channel ' + str(channeln+1), attrs=['dark']))
            print(colored('   Total Hashes = ' + str(len(channel_hashes)), attrs=['dark']))

            hashes |= channel_hashes

        values = []
        for hash, offset in hashes:
            values.append((song_id, hash, int(offset)))

        print(colored('\nWritting record to database...', 'green'))
        db.store_fingerprints(values)

    else:
        print('The file', fname, 'is not MP3.')

print('\nFinished fingerprinting proccess.')
