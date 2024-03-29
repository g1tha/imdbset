# Rank IMDB movies, shows, seasons and episodes a combination of ratings and number of votes.
# Ranking is based on credibility theory application described on https://en.wikipedia.org/wiki/IMDb.
import os
import sys
import urllib.request
import gzip
import json
import time
from datetime import timedelta, datetime, timezone
from multiprocessing import Pool
from collections import OrderedDict
from tqdm import tqdm
import polars as pl
import argparse

# Schema for tables from the IMDB's dataset at https://datasets.imdbws.com/.
# A nested dictionary in the form of tables = {'table name': {'column':{attributes}}}
tables = {
    "name.basics": {
        "nconst": {"dtype": pl.Utf8, "islist": False},
        "primaryName": {"dtype": pl.Utf8, "islist": False},
        "birthYear": {"dtype": pl.Int64, "islist": False},
        "deathYear": {"dtype": pl.Int64, "islist": False},
        "primaryProfession": {"dtype": pl.Utf8, "islist": True},
        "knownForTitles": {"dtype": pl.Utf8, "islist": True},
    },
    "title.akas": {
        "titleId": {"dtype": pl.Utf8, "islist": False},
        "ordering": {"dtype": pl.Int64, "islist": False},
        "title": {"dtype": pl.Utf8, "islist": False},
        "region": {"dtype": pl.Utf8, "islist": False},
        "language": {"dtype": pl.Utf8, "islist": False},
        "types": {"dtype": pl.Utf8, "islist": True},
        "attributes": {"dtype": pl.Utf8, "islist": True},
        "isOriginalTitle": {"dtype": pl.Boolean, "islist": False},
    },
    "title.basics": {
        "tconst": {"dtype": pl.Utf8, "islist": False},
        "titleType": {"dtype": pl.Utf8, "islist": False},
        "primaryTitle": {"dtype": pl.Utf8, "islist": False},
        "originalTitle": {"dtype": pl.Utf8, "islist": False},
        "isAdult": {"dtype": pl.Boolean, "islist": False},
        "startYear": {"dtype": pl.Int64, "islist": False},
        "endYear": {"dtype": pl.Int64, "islist": False},
        "runtimeMinutes": {"dtype": pl.Int64, "islist": False},
        "genres": {"dtype": pl.Utf8, "islist": True},
    },
    "title.crew": {
        "tconst": {"dtype": pl.Utf8, "islist": False},
        "directors": {"dtype": pl.Utf8, "islist": True},
        "writers": {"dtype": pl.Utf8, "islist": True},
    },
    "title.episode": {
        "tconst": {"dtype": pl.Utf8, "islist": False},
        "parentTconst": {"dtype": pl.Utf8, "islist": False},
        "seasonNumber": {"dtype": pl.Int64, "islist": False},
        "episodeNumber": {"dtype": pl.Int64, "islist": False},
    },
    "title.principals": {
        "tconst": {"dtype": pl.Utf8, "islist": False},
        "ordering": {"dtype": pl.Int64, "islist": False},
        "nconst": {"dtype": pl.Utf8, "islist": False},
        "category": {"dtype": pl.Utf8, "islist": False},
        "job": {"dtype": pl.Utf8, "islist": False},
        "characters": {"dtype": pl.Utf8, "islist": True},
    },
    "title.ratings": {
        "tconst": {"dtype": pl.Utf8, "islist": False},
        "averageRating": {"dtype": pl.Float64, "islist": False},
        "numVotes": {"dtype": pl.Float64, "islist": False},
    },
}


def main():
    # Adds ability to run script with arguement to update the dataset for the latest IMDB data.
    parser = argparse.ArgumentParser(
        prog="IMDBSet",
        description="Ranks IMDB movies, shows, seaons and episodes by a combination of ratings and number of votes.",
    )
    # Update argument
    parser.add_argument(
        "-u",
        "--update",
        help="Optional argument to update the source IMDB data should to the latest available.",
        action="store_true",
        default=False,
    )
    # Check to see if update arguement has been provided, check if user wants to proceed, then proceed.
    args = parser.parse_args()
    if args.update:
        answer = input(
            "This may take a few minutes. Are you sure you want to continue updating the data? "
        )
        if answer.strip().lower()[0] == "y":
            update_db()

    # Check if any files are missing, prompting an update, otherwise proceed to produce/refresh table outputs
    prompt_update()
    titles_tables()


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
            print(
                f"Function {func.__name__}, with {args}, {kwargs} input, completed in {duration}."
            )
        elif args and not kwargs:
            print(
                f"Function {func.__name__}, with {args} input, completed in {duration}."
            )
        elif kwargs and not args:
            print(
                f"Function {func.__name__}, with {kwargs} input, completed in {duration}."
            )
        else:
            print(f"Function {func.__name__} completed in {duration}.")
        return output

    return inner


@time_it
def update_db():
    """
    A function to return download IMDb gzip files then update then update the dataset of parquet files.
    """
    # Initialise progress bar.
    pbar = tqdm(tables, ncols=80)
    # For each table listed in the tables dictionary (within pbar), download the latest IDMB data.
    for table in pbar:
        pbar.set_description(f"Downloading {table}")
        urllib.request.urlretrieve(
            f"https://datasets.imdbws.com/{table}.tsv.gz", f"{table}.tsv.gz"
        )
        pbar.set_description(f"Download complete")
    # Using multiprocessing, load all downloaded files to a dataset of parquet files.
    print(f"Loading to parquet files to data/sources...")
    with Pool() as pool:
        pool.map(load_db, tables)
    # Export current date to lastUpdated.json
    now = datetime.now(timezone.utc)
    last_updated = now.strftime("%d %B %Y")
    with open("data\\lastUpdated.json", "w") as file:
        json.dump(last_updated, file)


def load_db(table):
    """
    Creates and updates a dataset of parquet files with the latest IMDB data which has been downloaded.
    """
    # Check if folder structure needs to be created.
    if not os.path.exists("data\sources"):
        os.makedirs("data\sources")
    # Check if file has been downloaded:
    if os.path.exists(f"{table}.tsv.gz"):
        # Unzip file.
        with gzip.open(f"{table}.tsv.gz", "rb") as z:
            with open(f"{table}.tsv", "wb") as f:
                f.write(z.read())
        # Extract a dictionary of datatypes from the tables dictionary for use in the p.scan_csv function.
        datatypes = {}
        for column in tables[table]:
            datatypes[column] = tables[table][column]["dtype"]
        # Create new table from the csv for the relavent table in the tables tuple.
        q = pl.scan_csv(
            f"{table}.tsv",
            separator="\t",
            dtypes=datatypes,
            null_values=["\\N"],
            quote_char=None,
            ignore_errors=True,
        )
        df = q.collect(streaming=True)
        # Recast any columns with lists as a list dtype.
        # (This step is necessary because, as at version 0.18.2, Polars does not support directly casting dtypes for a column from string to list when reading csvs.)
        for column in tables[table]:
            if tables[table][column]["islist"] == True:
                df = df.with_columns(
                    pl.col(column).str.replace_all(r"[\"\'\[\]\(\)]", "")
                )
                df = df.with_columns(pl.col(column).str.split(","))
        df.write_parquet(
            f"data\sources\{table}.parquet",
            row_group_size=491520,
            use_pyarrow=True,
            compression_level=10,
        )
        # Remove downloaded and unziped files.
        os.remove(f"{table}.tsv")
        os.remove(f"{table}.tsv.gz")


def list_missing_files():
    """
    Creates a list of missing parquet files in the directory, from the the list of tables in the tables dictionary.
    """
    missing_list = []
    for table in tables:
        if not os.path.exists(f"data\sources\{table}.parquet"):
            missing_list.append(table)
    return missing_list


def prompt_update():
    """
    Prompts users to download missing files.
    """
    missing_list = list_missing_files()
    if missing_list:
        print(f"Missing parquet files for {len(missing_list)} tables: ", end="")
        for table in missing_list[:-1]:
            print(f"{table}, ", end="")
        print(f"{missing_list[-1]}.")
        answer = input(
            "Would you like to download these files (it may take a few minutes)[y/n]? "
        )
        if answer.strip().lower()[0] == "y":
            update_db()
        else:
            print("Exiting: cannot continue without source files.")
            sys.exit(1)


def get_titles_base():
    """
    A function to return a base titles dataframe with ratings and categories added.
    """
    # Add a titleCategory Column and drop unecessary columns
    type_cat_map = pl.DataFrame(
        {
            "titleType": [
                "tvMiniSeries",
                "movie",
                "videoGame",
                "short",
                "tvSpecial",
                "tvSeries",
                "tvEpisode",
                "tvShort",
                "video",
                "tvPilot",
                "tvMovie",
            ],
            "titleCategory": [
                "series",
                "movie",
                "videoGame",
                "movie",
                "movie",
                "series",
                "episode",
                "movie",
                "movie",
                "episode",
                "movie",
            ],
        }
    )
    df = pl.read_parquet("data\sources\\title.basics.parquet").drop(
        "originalTitle", "startYear", "runtimeMinutes", "isAdult", "endYear"
    )
    # Remove adult genre
    df = df.filter(~pl.col("genres").list.contains("Adult"))
    df = df.join(type_cat_map, on="titleType", how="left")
    df = df.drop("titleType")
    # Add ratings and votes (using inner join, which means any titles without ratings will be excluded)
    ratings = pl.read_parquet("data\sources\\title.ratings.parquet")
    df = df.join(ratings, on="tconst")

    return df


@time_it
def titles_tables():
    """
    Produces a set of tables in CSV format of the top and bottom ranked titles by category and genre.
    """
    dict_titles = OrderedDict()
    title_all_count = 1000
    title_genre_count = 250
    list_categories = ["episode", "movie", "series", "videoGame"]
    titles_base = get_titles_base()
    for category in list_categories:
        # Filter by category
        titles_category = titles_base.filter(pl.col("titleCategory") == category)
        # Get genres
        genres = (
            titles_category.select(pl.col("genres").list.explode()).unique().to_series()
        )
        # If category is 'episode' add columns with series name, episode number and season number.
        if category == "episode":
            details = pl.read_parquet("data\sources\\title.episode.parquet")
            parents = titles_base.filter(pl.col("titleCategory") == "series").rename(
                {"tconst": "parentTconst"}
            )
            details = details.join(parents, on="parentTconst")
            details = details.rename({"primaryTitle": "seriesName"}).drop(
                "parentTconst", "genres", "titleCategory", "averageRating", "numVotes"
            )
            titles_category = titles_category.join(details, on="tconst")
            titles_category = titles_category.select(
                pl.col("tconst"),
                pl.col("primaryTitle"),
                pl.col("seriesName"),
                pl.col("seasonNumber"),
                pl.col("episodeNumber"),
                pl.col("averageRating"),
                pl.col("numVotes"),
                pl.col("genres"),
                pl.col("titleCategory"),
            )
            # Use episodes ratings to create tables with weighted average per season
            seasons_tables(titles_category, title_all_count, title_genre_count)
        # Add rankings
        titles_category = add_ranking(titles_category, 1)
        # Export to CSV (dropping uncessary columns, taking top and bottom 100, and rounding figures to reduce number of characters)
        output = titles_category.drop("genres", "titleCategory")
        output = output.with_columns(pl.col("numVotes").round(0).cast(pl.Int64))
        filename = f"title_{category}"
        export_csv(output, filename, title_all_count)
        # Add category and genre (all) to dict_titles
        dict_titles[category] = OrderedDict()
        dict_titles[category]["(All)"] = title_all_count
        for genre in genres:
            if genre:
                # Filter by genre
                titles_genre = titles_category.filter(
                    pl.col("genres").list.contains(genre)
                )
                # Add rankings
                titles_genre = add_ranking(titles_genre, 1)
                # Export to CSV (dropping uncessary columns, taking top and bottom 100, and rounding figures to reduce number of characters)
                output = titles_genre.drop("genres", "titleCategory")
                output = output.with_columns(pl.col("numVotes").round(0).cast(pl.Int64))
                filename = f"title_{category}_{genre}"
                export_csv(output, filename, title_genre_count)
                # If filename has been created,add genre to cagegory dictionary in dict_titles
                if os.path.exists(f"data\{filename}.csv"):
                    dict_titles[category][genre] = title_genre_count
    # Add seasons to dict_titles {}
    dict_titles["season"] = OrderedDict()
    dict_titles["season"]["(All)"] = title_all_count
    for genre in genres:
        if genre:
            dict_titles["season"][genre] = title_genre_count
    # Export dict_titles{} as titleMenus.json
    for category, genre in dict_titles.items():
        dict_titles[category] = OrderedDict(sorted(genre.items(), key=lambda x: x[0]))
    dict_titles.move_to_end("movie")
    dict_titles.move_to_end("series")
    dict_titles.move_to_end("season")
    dict_titles.move_to_end("episode")
    dict_titles.move_to_end("videoGame")
    with open("data\\titleMenus.json", "w") as file:
        json.dump(dict_titles, file)


def add_ranking(df, n):
    """
    Adds a rankings column to dataframe based on both average ratings and number of votes.
    """
    # Adopted from https://web.archive.org/web/20171023205105/http://www.imdb.com/help/show_leaf?votestopfaq
    # Calculate the weightedRatings column such that:
    # weighted rating = (R * v + mean * min_votes) / (v + min_votes)
    # Where:
    # R = average rating for the title
    # v = number of votes for the title
    # min_votes =  number of votes required for a more reliable rating (n * standard deviation(s) + mean number of votes for the relevant category).
    # mean = the mean rating for the relevant category.
    mean = df.select(pl.mean("averageRating"))
    min_votes = df.select(pl.mean("numVotes")) + n * df.select(pl.std("numVotes"))
    df = df.with_columns(
        (
            (pl.col("averageRating") * pl.col("numVotes") + mean * min_votes)
            / (pl.col("numVotes") + min_votes)
        ).alias("ranking")
    )
    df = df.with_columns(pl.col("ranking").rank(method="min", descending=True))
    df = df.sort(pl.col("ranking"))

    return df


def export_csv(df, filename, count, type=None):
    """
    Exports a top and bottom 'count' slice of the dataframe 'df' to a 'filename'.csv.
    """
    output_head = df.head(count)
    output_tail = df.tail(count)
    if type == "season":
        output = (
            output_head.extend(output_tail)
            .unique(subset=["tconst", "seasonNumber"])
            .sort(pl.col("ranking"))
        )
    else:
        output = (
            output_head.extend(output_tail)
            .unique(subset="tconst")
            .sort(pl.col("ranking"))
        )
    # Replace any commasthat make parsing csv challenging  with fullwdith commmas (uff0c) .
    output = output.with_columns(
        pl.all().apply(lambda x: x.replace(",", "，") if isinstance(x, str) else x)
    )

    output.write_csv(f"data\{filename}.csv")


def seasons_tables(df, title_all_count, title_genre_count):
    """
    Creates a set of weighted average ratings per season.
    """
    details = pl.read_parquet("data\sources\\title.episode.parquet").drop(
        "seasonNumber", "episodeNumber"
    )

    df = df.join(details, on="tconst")
    df = df.drop("tconst", "primaryTitle", "titleCategory")
    df = df.rename({"parentTconst": "tconst"})
    # Export overall seasons tables
    df_all = df.drop("genres")
    # Calculate weighted average rating per season
    df_all = df_all.with_columns(
        (pl.col("averageRating") * pl.col("numVotes")).alias("ratingProduct")
    )
    df_all = df_all.drop("averageRating")
    df_all = df_all.groupby(["tconst", "seriesName", "seasonNumber"]).sum()
    df_all = df_all.with_columns(
        (pl.col("ratingProduct") / pl.col("numVotes")).alias("averageRating")
    )
    df_all = df_all.drop("ratingProduct", "episodeNumber")
    # Add ranking
    df_all = add_ranking(df_all, 1)
    # round votes and ratings
    df_all = df_all.with_columns(
        pl.col("numVotes").round(0).cast(pl.Int64), pl.col("averageRating").round(1)
    )
    # rename seriesName as primaryTitle
    df_all = df_all.rename({"seriesName": "primaryTitle"})
    # export ratings to csv
    export_csv(df_all, "title_season", title_all_count, "season")
    # Get a list of genres for episodes, then get weighted average season ratings per genre
    genres = df.select(pl.col("genres").list.explode()).unique().to_series()
    for genre in genres:
        # if the genre is not empty, then filter by the genre
        if genre:
            df_genre = df.filter(pl.col("genres").list.contains(genre))
            df_genre = df_genre.drop("genres")
            # Calculate weighted average rating per season
            df_genre = df_genre.with_columns(
                (pl.col("averageRating") * pl.col("numVotes")).alias("ratingProduct")
            )
            df_genre = df_genre.drop("averageRating")
            df_genre = df_genre.groupby(["tconst", "seriesName", "seasonNumber"]).sum()
            df_genre = df_genre.with_columns(
                (pl.col("ratingProduct") / pl.col("numVotes")).alias("averageRating")
            )
            df_genre = df_genre.drop("ratingProduct", "episodeNumber")
            # Add ranking
            df_genre = add_ranking(df_genre, 1)
            # round votes and ratings
            df_genre = df_genre.with_columns(
                pl.col("numVotes").round(0).cast(pl.Int64),
                pl.col("averageRating").round(1),
            )
            # export ratings to csv
            # rename seriesName as primaryTitle
            df_genre = df_genre.rename({"seriesName": "primaryTitle"})
            export_csv(df_genre, f"title_season_{genre}", title_genre_count, "season")


if __name__ == "__main__":
    main()
