# Implements an algorithm to rank IMDB movies, shows, episodes and cast by a combination of ratings and number of votes by genre. Ranking is based on credibility theory application described on https://en.wikipedia.org/wiki/IMDb.
import os
import sys
import urllib.request
import gzip
import time
from datetime import timedelta
from multiprocessing import Pool
from tqdm import tqdm
import polars as pl
import argparse

# Schema for tables from the IMDB's dataset at https://datasets.imdbws.com/. 
# A nested dictionary in the form of tables = {'table name': {'column':{attributes}}}
tables = {
    'name.basics': {'nconst': {'dtype': pl.Utf8, 'islist': False},
                    'primaryName': {'dtype': pl.Utf8, 'islist': False},
                    'birthYear': {'dtype': pl.Int64, 'islist': False},
                    'deathYear': {'dtype': pl.Int64, 'islist': False},
                    'primaryProfession': {'dtype': pl.Utf8, 'islist': True},
                    'knownForTitles': {'dtype': pl.Utf8, 'islist': True}
                    },
    'title.akas': {'titleId': {'dtype': pl.Utf8, 'islist': False},
                   'ordering': {'dtype': pl.Int64, 'islist': False},
                   'title': {'dtype': pl.Utf8, 'islist': False},
                   'region': {'dtype': pl.Utf8, 'islist': False},
                   'language': {'dtype': pl.Utf8, 'islist': False},
                   'types': {'dtype': pl.Utf8, 'islist': True},
                   'attributes': {'dtype': pl.Utf8, 'islist': True},
                   'isOriginalTitle': {'dtype': pl.Boolean, 'islist': False}
                   },
    'title.basics': {'tconst': {'dtype': pl.Utf8, 'islist': False},
                     'titleType': {'dtype': pl.Utf8, 'islist': False},
                     'primaryTitle': {'dtype': pl.Utf8, 'islist': False},
                     'originalTitle': {'dtype': pl.Utf8, 'islist': False},
                     'isAdult': {'dtype': pl.Boolean, 'islist': False},
                     'startYear': {'dtype': pl.Int64, 'islist': False},
                     'endYear': {'dtype': pl.Int64, 'islist': False},
                     'runtimeMinutes': {'dtype': pl.Int64, 'islist': False},
                     'genres': {'dtype': pl.Utf8, 'islist': True}
                     },
    'title.crew': {'tconst': {'dtype': pl.Utf8, 'islist': False},
                   'directors': {'dtype': pl.Utf8, 'islist': True},
                   'writers': {'dtype': pl.Utf8, 'islist': True}
                   },
    'title.episode': {'tconst': {'dtype': pl.Utf8, 'islist': False},
                      'parentTconst': {'dtype': pl.Utf8, 'islist': False},
                      'seasonNumber': {'dtype': pl.Int64, 'islist': False},
                      'episodeNumber': {'dtype': pl.Int64, 'islist': False}
                      },
    'title.principals': {'tconst': {'dtype': pl.Utf8, 'islist': False},
                         'ordering': {'dtype': pl.Int64, 'islist': False},
                         'nconst': {'dtype': pl.Utf8, 'islist': False},
                         'category': {'dtype': pl.Utf8, 'islist': False},
                         'job': {'dtype': pl.Utf8, 'islist': False},
                         'characters': {'dtype': pl.Utf8, 'islist': True}
                         },
    'title.ratings': {'tconst': {'dtype': pl.Utf8, 'islist': False},
                      'averageRating': {'dtype': pl.Float64, 'islist': False},
                      'numVotes': {'dtype': pl.Float64, 'islist': False}
                      }
}


def main():
    # Adds ability to run script with arguement to update the dataset for the latest IMDB data.
    parser = argparse.ArgumentParser(
        prog='IMDBSet',
        description='Implements an algorithm to rank IMDB movies, shows, episodes and cast by a combination of ratings and number of votes by genre.'
        )
    parser.add_argument('-u', '--update',
                        help='Optional argument to wupdate the source IMDB data should to the latest available.',
                        action='store_true',
                        default=False)
    # Check to see if update arguement has been provided, check if user wants to proceed, then proceed.
    args = parser.parse_args()
    if args.update:
        answer = input("This may take a few minutes. Are you sure you want to continue updating the data? ")
        if answer.strip().lower()[0] == 'y':
            update_db()
    prompt_update()


## FUNCTIONS ##

def time_it(func):
    """
    Decorator function to return time taken to execute another function.
    """
    def inner(*args, **kwargs):
        tic = time.perf_counter()
        output = func(*args, **kwargs)
        toc = time.perf_counter()
        delta = toc - tic
        duration = timedelta(seconds=delta)
        if args and kwargs:
            print(f"Function {func.__name__}, with {args}, {kwargs} input, completed in {duration}.")
        elif args and not kwargs:
            print(f"Function {func.__name__}, with {args} input, completed in {duration}.")
        elif kwargs and not args:
            print(f"Function {func.__name__}, with {kwargs} input, completed in {duration}.")
        else:
            print(f"Function {func.__name__} completed in {duration}.")
        return output
    return inner


@time_it
def update_db():
    # Initialise progress bar.
    pbar = tqdm(tables, ncols=80)
    # For each table listed in the tables dictionary (within pbar), download the latest IDMB data.
    for table in pbar:
        pbar.set_description(f'Downloading {table}')
        urllib.request.urlretrieve(f'https://datasets.imdbws.com/{table}.tsv.gz', f'{table}.tsv.gz')
        pbar.set_description(f'Download complete')
    # Using multiprocessing, load all downloaded files to a dataset of parquet files.
    print(f'Loading to parquet files to data/sources...')
    with Pool() as pool:
        pool.map(load_db, tables)

@time_it
def read_parquet(file):
    return pl.read_parquet(file)


def load_db(table):
    """
    Creates and updates a dataset of parquet files with the latest IMDB data which has been downloaded.
    """
    # Check if folder structure needs to be created.
    if not os.path.exists('data\sources'):
        os.makedirs('data\sources')
    # Check if file has been downloaded:
    if os.path.exists(f'{table}.tsv.gz'):
        # Unzip file.
        with gzip.open(f'{table}.tsv.gz', 'rb') as z:
            with open(f'{table}.tsv', 'wb') as f:
                f.write(z.read())
        # Extract a dictionary of datatypes from the tables dictionary for use in the p.scan_csv function.
        datatypes = {}
        for column in tables[table]:
            datatypes[column] = tables[table][column]['dtype']
        # Create new table from the csv for the relavent table in the tables tuple.
        q = pl.scan_csv(f'{table}.tsv', separator='\t', dtypes=datatypes, null_values=['\\N'], quote_char=None, ignore_errors=True)
        df = q.collect(streaming=True)
        # Recast any columns with lists as a list dtype.
            # (This step is necessary because, as at version 0.18.2, Polars does not support directly casting dtypes for a column from string to list when reading csvs.)
        for column in tables[table]:
            if tables[table][column]['islist'] == True:
                df = df.with_columns(pl.col(column).str.replace_all(r'[\"\'\[\]\(\)]', ''))
                df = df.with_columns(pl.col(column).str.split(","))
        df.write_parquet(f'data\sources\{table}.parquet', row_group_size=491520, use_pyarrow=True, compression_level=10)
        # Remove downloaded and unziped files.
        os.remove(f'{table}.tsv')
        os.remove(f'{table}.tsv.gz')


def list_missing_files():
    """
    Creates a list of missing parquet files in the directory, from the the list of tables in the tables dictionary.
    """
    missing_list = []
    for table in tables:
        if not os.path.exists(f'data\sources\{table}.parquet'):
            missing_list.append(table)
    return missing_list

def prompt_update():
    """
    Prompts users to download missing files.
    """
    missing_list = list_missing_files()
    if missing_list:
        print(f'Missing parquet files for {len(missing_list)} tables: ', end='')
        for table in missing_list[:-1]:
            print(f'{table}, ', end='')
        print(f'{missing_list[-1]}.')
        answer = input('Would you like to download these files (it may take a few minutes)[y/n]? ')
        if answer.strip().lower()[0] == 'y':
            update_db()
        else:
            print('Exiting: cannot continue without source files.')
            sys.exit(1)

        
if __name__ == "__main__":
    main()

