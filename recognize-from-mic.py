import os
import sys
import libs
import libs.fingerprint as fingerprint
import argparse

from argparse import RawTextHelpFormatter
from itertools import zip_longest
from termcolor import colored
from libs.config import get_config
from libs.reader_microphone import MicrophoneReader
from libs.visualiser_console import VisualiserConsole as visual_peak
from libs.visualiser_plot import VisualiserPlot as visual_plot
from libs.db_sqlite import SqliteDatabase
# from libs.db_mongo import MongoDatabase

def grouper(iterable, n, fillvalue=None):
    args = [iter(list(iterable))] * n

    filtered = []

    for value in zip_longest(*args, fillvalue=fillvalue):
        vlist = list(value)
        for v in vlist:
            if v is not None:
                filtered.append(v)

    return (tuple(filtered))

def find_matches(samples, Fs=fingerprint.DEFAULT_FS):
    hashes = fingerprint.fingerprint(samples, Fs=Fs)
    return return_matches(hashes)

def return_matches(hashes):
    mapper = {}
    for hash, offset in hashes:
        mapper[hash.upper()] = offset
    values = mapper.keys()

    for split_values in grouper(values, 1000):
        # split_tuple = tuple(split_values)
        split_tuple = split_values

        query = """
                SELECT upper(hash), song_fk, offset
                FROM fingerprints
                WHERE upper(hash) IN (%s)
                """
        query = query % ', '.join('?' * len(split_tuple))

        x = db.executeAll(query, split_tuple)
        matches_found = len(x)

        if matches_found > 0:
            msg = '   ** Found %d hash matches (step %d/%d)'
            print(colored(msg, 'green') % (
                matches_found,
                len(split_tuple),
                len(values)
            ))
        else:
            msg = '   ** No matches found (step %d/%d)'
            print(colored(msg, 'red') % (
                len(split_tuple),
                len(values)
            ))

        for hash, sid, offset in x:
            # (sid, db_offset - song_sampled_offset)
            yield (sid, offset - mapper[hash])

def align_matches(matches):
    diff_counter = {}
    largest = 0
    largest_count = 0
    song_id = -1

    for tup in matches:
        sid, diff = tup

    if diff not in diff_counter:
        diff_counter[diff] = {}

    if sid not in diff_counter[diff]:
        diff_counter[diff][sid] = 0

    diff_counter[diff][sid] += 1

    if diff_counter[diff][sid] > largest_count:
        largest = diff
        largest_count = diff_counter[diff][sid]
        song_id = sid

    songM = db.get_song_by_id(song_id)

    nseconds = round(float(largest) / fingerprint.DEFAULT_FS *
                    fingerprint.DEFAULT_WINDOW_SIZE *
                    fingerprint.DEFAULT_OVERLAP_RATIO, 5)

    return {
        "SONG_ID" : song_id,
        "SONG_NAME" : songM[1],
        "CONFIDENCE" : largest_count,
        "OFFSET" : int(largest),
        "OFFSET_SECS" : nseconds
    }


###### MAIN: ######
config = get_config()
db = SqliteDatabase()

parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
parser.add_argument('-s', '--seconds', nargs='?')
args = parser.parse_args()

if not args.seconds:
    print("Missing argument \"seconds\".")
    sys.exit(0)

secs = int(args.seconds)

chunksize = 2**12  # 4096
channels = 2

record_forever = False
visualise_console = bool(config['mic.visualise_console'])
visualise_plot = bool(config['mic.visualise_plot'])

reader = MicrophoneReader(None)

reader.start_recording(seconds=secs, chunksize=chunksize, channels=channels)
print(colored(' * Started recording...', 'green', attrs=['dark']))

while True:
    bufferSize = int(reader.rate / reader.chunksize * secs)

    for i in range(0, bufferSize):
        nums = reader.process_recording()

        if visualise_console:
            msg = colored('   %05d', attrs=['dark']) + colored(' %s', 'green')
            print(msg  % visual_peak.calc(nums))
        else:
            print(colored('   processing ' + str(i) + ' of ' + str(bufferSize), attrs=['dark']))

    if not record_forever: 
        break

if visualise_plot:
    data = reader.get_recorded_data()[0]
    visual_plot.show(data)

reader.stop_recording()
print(colored(' * Recording has stopped.', 'red', attrs=['dark']))

data = reader.get_recorded_data()
print(colored(' * Recorded ' + str(len(data[0])) + ' samples.', attrs=['dark']))

Fs = fingerprint.DEFAULT_FS
channel_amount = len(data)
result = set()
matches = []

for channeln, channel in enumerate(data):
    # TODO: Remove prints or change them into optional logging.
    msg = '\n   fingerprinting channel %d of %d'
    print(colored(msg, attrs=['dark']) % (channeln+1, channel_amount))

    matches.extend(find_matches(channel))

    msg = '   finished channel %d/%d, got %d hashes'
    print(colored(msg, attrs=['dark']) % (
        channeln+1, channel_amount, len(matches)
    ))

total_matches_found = len(matches)

print('\n')

if total_matches_found > 0:
    print(colored('   ** Found ' + str(total_matches_found) + ' hash matches.', 'green'))

    song = align_matches(matches)
    print(colored('    > Song Guess: ' + song['SONG_NAME'], 'green'))
    print(colored('    > Offset: ' + str(song['OFFSET']), 'green', attrs=['dark']))
    print(colored('    > Confidence: ' + str(song['CONFIDENCE']) + '%', 'green', attrs=['dark']))

else:
    print(colored("   ** No match was found.", 'red'))
