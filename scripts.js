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
const themeLink =document.querySelector('.theme-link');
const lightIcon = themeLink.querySelector('.bi-sun-fill');
const darkIcon = themeLink.querySelector('.bi-moon-fill');
const themeSwitch = document.querySelector('.theme-switch');
const themeLbl = document.querySelector('.theme-lbl');
const categoryDropdown = document.getElementById('category');
const genreDropdown = document.getElementById('genre');
const lastUpdated = document.getElementById('lastUpdated')

const getTitleMenus = async () => {
    const response = await fetch('data/titleMenus.json');
    const data = await response.json();
    return data;
}
const getLastUpdate = async () => {
    const response = await fetch('data/lastUpdated.json');
    const data = await response.json();
    return data;
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
if (themeSwitch !== null){
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
        while (genreDropdown.firstChild){
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

function getTitlesData() {
    getTitleMenus().then(titleMenus => {      
        const selectedCategory = categoryDropdown.value;
        const selectedGenre = genreDropdown.value;
        const titlesCountText = document.getElementById('titles_count')
        titlesCountText.textContent = titleMenus[selectedCategory][selectedGenre]
        const csvData = {
            category: selectedCategory,
            genre: selectedGenre,
        };
        console.log(csvData);
    })
}

