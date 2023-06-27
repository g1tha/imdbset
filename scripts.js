// GLOBAL VARIABLES
const styleSheet = document.getElementById('stylesheet');
const primaryNav = document.querySelector('.primary-navigation');
const navToggle = document.querySelector('.nav-toggle');
const navBurger = document.querySelector('.bi-list');
const navClose = document.querySelector('.bi-x');
const homeLink = document.getElementById('home');
const titlesLink = document.getElementById('titles');
const seriesLink = document.getElementById('series');
const peopleLink = document.getElementById('people');
const themeLink = document.querySelector('.theme-link');
const lightIcon = themeLink.querySelector('.bi-sun-fill');
const darkIcon = themeLink.querySelector('.bi-moon-fill');
const themeSwitch = document.querySelector('.theme-switch');
const themeLbl = document.querySelector('.theme-lbl');
const categoryDropdown = document.getElementById('category');
const genreDropdown = document.getElementById('genre');
const lastUpdated = document.getElementById('lastUpdated');
const titleGridDiv = document.querySelector('#titleGrid');

async function getTitleMenus() {
    const response = await fetch('data/titleMenus.json');
    const data = await response.json();
    return data;
}
async function getLastUpdate() {
    const response = await fetch('data/lastUpdated.json');
    const data = await response.json();
    return data;
}


async function parseTitleCSV(category, genre) {
    let first = category;
    let second = genre;
    let url;
    if (genre === '(All)') {
        url = "data/title_" + first + ".csv";
    }
    else {
        url = "data/title_" + first + "_" + second + ".csv";
    }
    const response = await fetch(url);
    const csvData = await response.text();
    const rows = csvData.split('\n');
    const headers = rows[0].split(',');
    const dictionary = [];
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i].split(',');
        if (row.length === headers.length) {
            const item = {};
            for (let j = 0; j < headers.length; j++) {
                item[headers[j]] = row[j];
            }
            dictionary.push(item);
        }
    }
    return dictionary;
};

function getTitleCSV(category, genre) {
    let first = category;
    let second = genre;
    let url;
    let result = [];
    if (genre === '(All)') {
        url = "data/title_" + first + ".csv";
    }
    else {
        url = "data/title_" + first + "_" + second + ".csv";
    }
    parseCSV(url)
        .then(dictionary => {
            ;
            result.push(...dictionary);
        });

    // console.log(result.length);
    // console.log(result);
    return result;
}

navToggle.addEventListener('click', () => {
    const visibility = primaryNav.getAttribute('data-visible');
    if (visibility === 'false') {
        primaryNav.setAttribute('data-visible', 'true');
        navToggle.setAttribute('aria-expanded', 'true');
        navBurger.setAttribute('data-visible', 'false');
        navClose.setAttribute('data-visible', 'true');
    } else {
        primaryNav.setAttribute('data-visible', 'false');
        navToggle.setAttribute('aria-expanded', 'false');
        navBurger.setAttribute('data-visible', 'true');
        navClose.setAttribute('data-visible', 'false');
    }
})


let lightMode = localStorage.getItem('lightMode');
themeLink.addEventListener('click', changeTheme);
if (themeSwitch !== null) {
    themeSwitch.addEventListener('click', changeTheme);
}

if (lightMode === 'enabled') {
    enableLightMode();
} else {
    disableLightMode();
}

if (window.location.pathname.includes('titles.html')) {
    updateCategories()
}

// FUNCTIONS

function changeTheme() {
    if (lightMode === 'enabled') {
        disableLightMode();
    } else {
        enableLightMode();
    }
}


function enableLightMode() {
    darkIcon.setAttribute('data-visible', 'true');
    lightIcon.setAttribute('data-visible', 'false');
    localStorage.setItem('lightMode', 'enabled');
    lightMode = localStorage.getItem('lightMode');
    styleSheet.setAttribute('href', 'styles-light.css');
    if (themeSwitch !== null) {
        themeLbl.textContent = "Light theme on";
        themeSwitch.checked = true;
    }
    if (window.location.pathname.includes('titles.html')) {
        titleGridDiv.setAttribute('class', 'ag-theme-alpine');
    }
}

function disableLightMode() {
    darkIcon.setAttribute('data-visible', 'false');
    lightIcon.setAttribute('data-visible', 'true');
    localStorage.setItem('lightMode', null);
    lightMode = localStorage.getItem('lightMode');
    styleSheet.setAttribute('href', 'styles.css');;
    if (themeSwitch !== null) {
        themeLbl.textContent = "Light theme off";
        themeSwitch.checked = false;
    }
    if (window.location.pathname.includes('titles.html')) {
        titleGridDiv.setAttribute('class', 'ag-theme-alpine-dark');
    }
}

function updateCategories() {
    getTitleMenus().then(titleMenus => {
        for (const category in titleMenus) {
            const option = document.createElement('option');
            option.text = category;
            option.value = category;
            categoryDropdown.add(option)
        };
    })
    updateLast();
    updateGenres();
}

function updateLast() {
    getLastUpdate().then(data => {
        lastUpdated.textContent = data;
    })

}


function updateGenres() {
    getTitleMenus().then(titleMenus => {
        const selectedCategory = categoryDropdown.value;
        while (genreDropdown.firstChild) {
            genreDropdown.removeChild(genreDropdown.firstChild)
        };

        Object.keys(titleMenus[selectedCategory]).forEach(key => {
            const option = document.createElement('option');
            option.text = key;
            option.value = key;
            genreDropdown.add(option)
        });
    })
    getTitlesData();
}

async function getTitlesData() {
    var id = [];
    var title = [];
    var link = [];
    var rating = [];
    var votes = [];
    var ranking = [];
    var rowData = [];
    var columnDefs = [
        {field: 'title', cellDataType: 'text', wrapText: true, autoHeight: true, cellRenderer: params => {return params.value}},
        {field: 'rating', cellDataType: 'number', minWidth: 80},
        {field: 'votes', cellDataType: 'number', minWidth: 80, valueFormatter: commaFormatter},
        {field: 'ranking', cellDataType: 'number', minWidth: 90, valueFormatter: commaFormatter},
    ];
    // Get menu data
    const titleMenus = await getTitleMenus();
    const selectedCategory = categoryDropdown.value;
    const selectedGenre = genreDropdown.value;
    const titlesCountText = document.getElementById('titles_count')
    titlesCountText.textContent = titleMenus[selectedCategory][selectedGenre]
    // Initialise column names as arrays
    // Parse CSV for selected category and genre into the column names
    var table = await parseTitleCSV(selectedCategory, selectedGenre);
    // Push data to arrays
    for (let row in table) {
        id.push(table[row]['tconst']);
        title.push(table[row]['primaryTitle']);
        link.push('<a href="https://www.imdb.com/title/' + table[row]['tconst'] + '/" target="_blank">' + table[row]['primaryTitle'] + '</a>');
        rating.push(Number(table[row]['averageRating']));
        votes.push(Number(table[row]['numVotes']));
        ranking.push(Number(table[row]['ranking']));
    }
    // Create table
    let tableSchema = { 'title': link, 'rating': rating, 'votes': votes, 'ranking': ranking }
    rowData = ArraytoDict(tableSchema);

    const gridOptions = {
        columnDefs: columnDefs,
        defaultColDef: {sortable: true, filter: true, resizable: true, flex:1},
        animateRows: true,
        pagination: true,
        paginationPageSize: 20,
        domLayout: 'autoHeight',
        rowData: rowData,
    };
    
    titleGridDiv.innerHTML = '';
    new agGrid.Grid(titleGridDiv, gridOptions);
    gridOptions.columnApi.autoSizeColumns(['rating', 'votes', 'ranking'], true);
    
}

// For formatting cells in ag Grid tables
function commaFormatter(params) {
    return formatNumber(params.value);
  }

function formatNumber(number) {
return Math.floor(number).toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,');
}

function ArraytoDict(arrays) {
    const dictionaries = [];
    const columnNames = Object.keys(arrays);
    const numRows = arrays[columnNames[0]].length;
    for (let i = 0; i < numRows; i++) {
        const dictionary = {};
        for (let j = 0; j < columnNames.length; j++) {
            const columnName = columnNames[j];
            const value = arrays[columnName][i];
            dictionary[columnName] = value;
        }
        dictionaries.push(dictionary);
    }
    return dictionaries;
}
