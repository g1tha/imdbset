# Implements an algorithm to rank IMDB movies, shows and episodes by a combination of ratings and number of votes by genre. Ranking is based on credibility theory application described on https://en.wikipedia.org/wiki/IMDb.
import os
import urllib.request
import gzip
import sqlite3
import pandas as pd
import time
from datetime import timedelta
from multiprocessing import Pool
from tqdm import tqdm
import polars as pl
import duckdb

# Tuple with table names source from IMDB's dataset at https://datasets.imdbws.com/
tables = ('name.basics', 'title.akas', 'title.basics', 'title.crew', 'title.episode', 'title.principals', 'title.ratings',)

# Table schemas in SQL format (delete if different to duckdb schema syntax)
sql_schemas = {
    'name.basics': 'CREATE TABLE namebasics(nconst TEXT PRIMARY KEY, primaryName TEXT, birthYear INTEGER, deathYear INTEGER, primaryProfession TEXT, knownForTitles TEXT);',
    'title.akas': 'CREATE TABLE titleakas(titleId TEXT, ordering INTEGER, title TEXT, region TEXT, language TEXT, types TEXT, attributes TEXT, isOriginalTitle INTEGER);',
    'title.basics': 'CREATE TABLE titlebasics(tconst TEXT PRIMARY KEY, titleType TEXT, primaryTitle TEXT, originalTitle TEXT, isAdult INTEGER, startYear INTEGER, endYear INTEGER, runtimeMinutes INTEGER, genres TEXT);',
    'title.crew': 'CREATE TABLE titlecrew(tconst TEXT PRIMARY KEY, directors TEXT, writers TEXT);',
    'title.episode': 'CREATE TABLE titleepisode(tconst TEXT PRIMARY KEY, parentTconst TEXT, seasonNumber INTEGER, episodeNumber INTEGER);',
    'title.principals': 'CREATE TABLE titleprincipals(tconst TEXT, ordering TEXT, nconst TEXT, category TEXT, job TEXT, characters TEXT);',
    'title.ratings': 'CREATE TABLE titleratings(tconst TEXT PRIMARY KEY, averageRating REAL, numVotes INTEGER);'
}
# Table schema for use in Polars. A nested dictionary going from table name, to column, to datatype.
pl_schemas = {
    'name.basics': {'nconst': pl.Utf8, 'primaryName': pl.Utf8, 'birthYear': pl.UInt16, 'deathYear': pl.UInt16, 'primaryProfession': pl.Utf8, 'knownForTitles': pl.Utf8},
    'title.akas': {'titleId': pl.Utf8, 'ordering': pl.UInt32, 'title': pl.Utf8, 'region': pl.Utf8, 'language': pl.Utf8, 'types': pl.Utf8, 'attributes': pl.Utf8, 'isOriginalTitle': pl.Boolean},
    'title.basics': {'tconst': pl.Utf8, 'titleType': pl.Utf8, 'primaryTitle': pl.Utf8, 'originalTitle': pl.Utf8, 'isAdult': pl.Boolean, 'startYear': pl.UInt16, 'endYear': pl.UInt16, 'runtimeMinutes': pl.UInt16, 'genres': pl.Utf8},
    'title.crew': {'tconst': pl.Utf8, 'directors': pl.Utf8, 'writers': pl.Utf8},
    'title.episode': {'tconst': pl.Utf8, 'parentTconst': pl.Utf8, 'seasonNumber': pl.UInt32, 'episodeNumber': pl.UInt32},
    'title.principals': {'tconst': pl.Utf8, 'ordering': pl.UInt32, 'nconst': pl.Utf8, 'category': pl.Utf8, 'job': pl.Utf8, 'characters': pl.Utf8},
    'title.ratings': {'tconst': pl.Utf8, 'averageRating': pl.Float64, 'numVotes': pl.Float64}
}

# Columns in each table that contain lists for use in Polars. A nested dictionary going from table name, to column, to boolean of whether or not the column is a list.
    # (As at version 0.18.2, Polars does not support casting dtypes for a column from string to list when reading csvs.) 
pl_list_cols = {
    'name.basics': {'nconst': False, 'primaryName': False, 'birthYear': False, 'deathYear': False, 'primaryProfession': True, 'knownForTitles': True},
    'title.akas': {'titleId': False, 'ordering': False, 'title': False, 'region': False, 'language': False, 'types': True, 'attributes': True, 'isOriginalTitle': False},
    'title.basics': {'tconst': False, 'titleType': False, 'primaryTitle': False, 'originalTitle': False, 'isAdult': False, 'startYear': False, 'endYear': False, 'runtimeMinutes': False, 'genres': True},
    'title.crew': {'tconst': False, 'directors': True, 'writers': True},
    'title.episode': {'tconst': False, 'parentTconst': False, 'seasonNumber': False, 'episodeNumber': False},
    'title.principals': {'tconst': False, 'ordering': False, 'nconst': False, 'category': False, 'job': False, 'characters': True},
    'title.ratings': {'tconst': False, 'averageRating': False, 'numVotes': False}
}

def main():
    load_polarsdb(tables[6])
    df = read_parquet(tables[6])

    print(df)


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
    # for table in tables:
    #     # download_file(table)
    #     remove_parquet(table)
    #     # load_duckdb(table)
    #     # remove_gz(table)
    with Pool() as pool:
        pool.map(load_polarsdb, tables)

@time_it
def read_parquet(table):
    return pl.read_parquet(f'{table}2.parquet')


def remove_tsv(table):
    """
    For a given table from the tables tuple, removes existing .tsv files.
    """
    if os.path.exists(f'{table}.tsv'):
        os.remove(f'{table}.tsv')
        print(f"Removed existing {table}.tsv")


def remove_gz(table):
    """
    For a given table from the tables tuple, removes existing .gzip files.
    """
    if os.path.exists(f'{table}.tsv.gz'):
        os.remove(f'{table}.tsv.gz')
        print(f"Removed existing {table}.tsv")


def remove_parquet(table):
    """
    For a given table from the tables tuple, removes existing .parquet files.
    """
    if os.path.exists(f'{table}.parquet'):
        os.remove(f'{table}.parquet')
        print(f"Removed existing {table}.parquet")


def download_file(table):
    """
    For a given table from the tables tuple, downloads and unzips the latest free IMDB dataset to a downloads folder.
    """
    # Download zip files
    urllib.request.urlretrieve(f'https://datasets.imdbws.com/{table}.tsv.gz', f'{table}.tsv.gz')
    print(f"Downloaded to {f'{table}.tsv.gz'} \n")


def unzip_table(table):
    """
    For a given table from the tables tuple, decompresses gzip file.
    """
    with gzip.open(f'{table}.tsv.gz', 'rb') as z:
        with open(f'{table}.tsv', 'wb') as f:
            f.write(z.read())


def load_duckdb(table):
    """
    Creates and duckdb database
    """
    print(f"Creating {table}.parquet")
    conn = duckdb.connect()
    conn.executemany(f"""
    PRAGMA memory_limit='32GB';
    PRAGMA enable_progress_bar;
    PRAGMA enable_profiling;
    """)
    conn.execute(f"""
    COPY (SELECT * FROM read_csv_auto('{table}.tsv.gz', HEADER=TRUE, ESCAPE='', QUOTE='', NULLSTR='\\N', SEP='\t', AUTO_DETECT=TRUE, IGNORE_ERRORS=TRUE))
    TO '{table}.parquet'
    (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 491520)
    """)

def load_polarsdb(table):
    """
    Creates and updates a sqlite database (db) with the latest IMDB data which has been downloaded.
    """
    # Check if file has been downloaded:
    if os.path.exists(f'{table}.tsv.gz'):
        unzip_table(table)
        # Create new table from the csv for the relavent table in the tables tuple.
        q = pl.scan_csv(f'{table}.tsv', separator='\t', null_values=['\\N'], quote_char=None, ignore_errors=True)
        df = q.collect(streaming=True)
        # Cast dtypes of columns according to the pl_schema.
            # (This approach, while slower than defining dtypes when scanning the csv, was chosen to allow downcasting number formats where possible.) 
        for k in pl_schemas[table]:
            df = df.with_columns(pl.col(k).cast(pl_schemas[table][k]))
        # Recast any columns with lists as a list dtype.
            # (This step is necessary because, as at version 0.18.2, Polars does not support casting dtypes for a column from string to list when reading csvs.)
        for k in pl_list_cols[table]:
            if pl_list_cols[table][k] == True:
                df = df.with_columns(pl.col(k).str.replace_all('a', 'A'))
                df = df.with_columns(pl.col(k).str.split(","))
        df.write_parquet(f'{table}2.parquet', row_group_size=491520, use_pyarrow=True, compression_level=1)
        remove_tsv(table)


def index_db():
    """
    Creates indexes for tables that have been loaded into the database.
    """
    # Connect to database.
    con = sqlite3.connect('im.db')
    cur = con.cursor()

    # Create indexes.
    cur.executescript("""
        CREATE INDEX index_namebasics_primaryName ON namebasics (primaryName);
        CREATE INDEX index_namebasics_primaryProfession ON namebasics (primaryProfession);
        CREATE INDEX index_namebasics_knownForTitles ON namebasics (knownForTitles);
        CREATE INDEX index_titleakas_titleId ON titleakas (titleId);
        CREATE INDEX index_titleakas_title ON titleakas (title);
        CREATE INDEX index_titlebasics_titleType ON titlebasics (titleType);
        CREATE INDEX index_titlebasics_primaryTitle ON titlebasics (primaryTitle);
        CREATE INDEX index_titlebasics_originalTitle ON titlebasics (originalTitle);
        CREATE INDEX index_titlebasics_genres ON titlebasics (genres);
        CREATE INDEX index_titlecrew_directors ON titlecrew (directors);
        CREATE INDEX index_titlecrew_writers ON titlecrew (writers);
        CREATE INDEX index_titleepisode_tconst ON titleepisode (tconst);
        CREATE INDEX index_titleepisode_parentTconst ON titleepisode (parentTconst);
        CREATE INDEX index_titleprincipals_tconst ON titleprincipals (tconst);
        CREATE INDEX index_titleprincipals_nconst ON titleprincipals (nconst);
        CREATE INDEX index_titleprincipals_category ON titleprincipals (category);
        CREATE INDEX index_titleprincipals_job ON titleprincipals (job);
        CREATE INDEX index_titleprincipals_characters ON titleprincipals (characters);

    """)

    con.commit()
    con.close()

    print("Indexing complete.")


if __name__ == "__main__":
    main()

