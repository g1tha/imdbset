const styleSheet = document.getElementById('stylesheet');
const primaryNav = document.querySelector('.primary-navigation');
const navToggle = document.querySelector('.nav-toggle');
const navBurger = document.querySelector('.bi-list');
const navClose = document.querySelector('.bi-x');
const themeLink =document.querySelector('.theme-link');
const lightIcon = themeLink.querySelector('.bi-sun-fill');
const darkIcon = themeLink.querySelector('.bi-moon-fill');
const themeSwitch = document.querySelector('.theme-switch');
const themeLbl = document.querySelector('.theme-lbl');

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