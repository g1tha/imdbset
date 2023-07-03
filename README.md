# IMDb rankings
## About
#### Video Demo: [here](youtube.com)
#### Description:
This is my cs50x final project. It uses python, javascript, html and css to produce rankings of IMDb movies, shows, seasons and episodes according to a combination of average ratings and number of votes using the ranking methodology described below. The project uses IMDb's free non-commercial dataset found [here](https://developer.imdb.com/non-commercial-datasets/). 

While IMDb provides [rankings](https://www.imdb.com/chart/top/) according to their own methodology for movies and tv shows, they do not currently provide rankings for episodes and seasons, nor drill down to provide rankings by genre. Instead, users can view titles in these categories ordered by 'average ratings', 'number of votes', or 'popularity'.

##### Ranking methodology
Rankings are based on a concept previously used by IMDb to rank their top 250 rated lists described [here](https://web.archive.org/web/20171023205105/http://www.imdb.com/help/show_leaf?votestopfaq). It follows the principle that the average ratings of titles with more votes more accurately reflect their true ratings. However, IMDb's approach is more sophisticated now.

A ranking formula is applied to each category of titles (i.e. movies, series, seasons, episodes) and each genre within those categories. A season's ratings are based on aggregates of the episodes within that season (weighted average for ratings and sum for number of votes.)

Titles for a relevant category are ranked in descending order according to their weighted ratings, calculated as:

weighted rating = (R * v + mean * min_votes) / (v + min_votes)
 - where:
   - R = average rating for the title.
   - v = number of votes for the title.
   - min_votes = number of votes required for a more reliable rating (1 standard deviation above the mean number of votes for the relevant category).
   - mean = the mean rating for the relevant category

## Outputs
The project allows users to download the latest free IMDb datasets, store these as a set of parquet files, and output a set of rankings as CSV files in a data folder.
Users can navigate the rankings with the index.html file.
An online example has been published to my [github pages](https://g1tha.github.io/imdbset/).

## Key files

### index.html
Allows users to navigate the csv outputs produced by the project. It contains two pages, "home" and "rankings" implemented as a rudimentary single-page app (clicking on the links makes the div for the relevant page appear and the others disappear).

There is also a link in the navigation bar which allows users to choose between dark and light mode.

The rankings page contains drop-down menus which allows users to select the category and genre they are interested it. Upon selection, a table with the rankings and bubble chart (visualising the rankings currently shown) are updated.

The table lists 20 rankings per page, and users can scroll through to other pages, order by other columns (e.g. by number of votes or average ratings), and apply filters (e.g. if they just want to see the rankings for a particular show).

### main.py
Checks to see if all the source files are in the project's 'data\sources' folder. If not, it prompts users to down the files.
If the files are there, main.py proceeds to create (or update) the csv files with rankings. 
Users can also add an argument when running main.py (e.g. 'py main.py -u') to download the latest IMDb dataset. If they do, this also updates a 'data\liastupdated.json' file, which is picked up in index.html.

Main.py contains a dictionary ('tables') which lists out the table names, columns, datatypes of each column and whether the column is itself a nested list.

This is used by the load_db() function to download gzip files for each table from IMDb, and subsequently by load_db() function to store each table as a parquet file, using the Polars library. Because each table is stored as a seperate parquet file, main.py was able to use the Multiprocessing library to materially increase the speed of the producing the parquet files.

The titles_tables() function uses Polars to create a set of tables for each category ('movie', 'series', 'episode', 'videoGame') and every genre within those categories. It also calls the seasons_tables() function to create a set of tables for each season of a tv series, based on episode ratings data.

The titles_tables() function calls on the 'add_rankings()' function to add rankings to each table. This rankings function takes 'n' as an argument to change the standard deviations above the mean required for the minimum number of votes component of the ranking formula. It is set at 1 but can be increased to weight rankings more towards titles with higher numbers of votes received. IMDb's previous application of this ranking formula seemed to correspond to 2 standard deviations above the mean.

 The titles_tables() function then calls on the export_csv function to export each of the rankings tables created to csv files in the 'data' folder. It also creates/updates the 'data\titleMenus.json' file, which is then picked up by index.html to create a set of drop-down menus.

 Main.py contains a time_it() function, which has been used as a decorator to dsiplay the time taken to create the full set of CSV outputs. It also uses the TQDM library to display a progress bar for downloading the gzip files from IMDb. These steps take several minutes, so this display helps the user experience, and keeps them informed if the sever stops responding.


### styles.css & styles-light.css
Apply the dark and light theme to index.html. The style sheets make index.html responsive to different window sizes on different devices. They implement the animations on elements like links and the navigation bar, which becomes a side panel once the screen width gets small enough.

### scripts.js
Implements several processes to make index.html interactive.

The script listens for 'clicks' on links and serves up the requested page, and allows users to toggle between dark and light mode. It stores colour theme preferences in local storage to restore the preferred theme on subsequent visits.

Upon page load, the script uses an async function, 'getTitleMenus()', to fetch the 'data/titleMenus.json' needed to populate the drop down menus on the ranking page. The script then uses an async function, 'parseTitleCSV', to select the CSV file that corresponds to the combination of choices made with the category and genre drop-down menus. This is updated when the user selects a different combination. When the user changes categories, the list in the genres drop-down is updated to reflect the genres available in the selected category.

With the relevant CSV, the async function 'getTitlesData() pushes the data in the CSV to a set of lists, which are then used to populate a table. 

##### AG Grid
The [AG Grid javascript library](https://www.ag-grid.com/javascript-data-grid/) was used to create the table on the rankings page. Columns in the grid are set up to show/hide relevant columns depending on the category selected, (e.g. a column with episode numbers is displayed when the 'episode' category is selected from the drop-down menu). AG grid also allows cells to be rendered with HTML - this was used to render hyperlinks to each title, using the pattern 'https://www.imdb.com/title/' + the tconst unique identifier. Pagination was set up to limit the number of titles on the page to 20 at a time.

The 'getDataDisplayed()' function is then used to create a dataset of titles displayed for the current page.

##### Charts.js
The [Charts.js](https://www.chartjs.org/) was used to create a bubble chart from the dataset extracted with the getDataDisplayed() function. The radius used for each bubble was a function of the window with and the number of votes received relative to the largest value in the selected category-genre combination. This allows bubble-sizes to be responsive to the window width of different devices used. 


### data folder
The data folder stores the CSV files produced by the python script. Within this folder, the subfolder 'sources' contains the parquet files containing all the data downloaded from the IMDb dataset. 'data\sources' has been added to the git-ignore file, to avoid uploading a 1gb set of files to github.

### requirements.txt
Main.py tries to stick to the python standard library as much as possible. The only additional requirements were the Polars library, which significantly improved processing time, and TQDM to display progress bars when the source data is being updated.


## New skills acquired
I needed to learn several new concepts and libraries not covered in the CS50x course to overcome challenges I faced on this project.

The initial data processing in the python script was very slow (see design choices below). I needed to understand how python and SQLite uses the CPU cores available, and learn about the Multiprocessing library. I also needed to investigate alternatives to databases and file formats, which led me to learn how to use the Pandas, Polars and DuckDB libraries.

I needed to learn about javascript fetch, promises, and async and await functions to display the rankings data on the html page. I found this part the most challenging part of the project - particularly when chaining different async functions together. I also needed to learn how to use the AG Grid library, and Charts.js library to display interactive visualisations of the rankings.

Luckily, I could rely on the documentation of each of the above libraries to get the scripts to do what I needed.

## Design choices
### API vs static files
The first dilemma I faced was in what format I would produce the data. I initially explored creating an API with something like Django, Flask or Fast API. But I wanted a solution that would minimise or eliminate CPU and memory usage on the server side. So, I decided I would make a large set of small static files, that would mimic API routes and host this somewhere (initially i was thinking of using a CDN). I went with CSVs (rather than JSON) for the ranking files because I could host them on Github and use Github's CSV viewer when accessing the files directly online.

### Argparse vs sys
I went with the Argeparse library instead of sys, despite only including one command line argument that could be parsed into main.py. This was because Argeparse formats the description and help argument nicely.

### Databases and file formats
I initially used a SQLite database to store the IMDb data I was downloading from IMDb. The process of storing data in the SQLite database was very slow. So, I tried DuckDB, Pandas and Polars. I also explored different file formats. Polars with Parquet files (finetuned to use the pyarrow engine) produced the fastest results. This was consistent with benchmarks found [here](https://h2oai.github.io/db-benchmark/) and [here](https://www.pola.rs/benchmarks.html).


## To do
At some point it would be good to introduce some testing and include more try/catch routines - particularly with the async javascript functions.