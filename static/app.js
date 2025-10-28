const burger = document.querySelector(".burger");
const nav = document.querySelector("nav");

burger.addEventListener("click", () => {
  // toggle nav
  nav.classList.toggle("active");

  // toggle icon
  burger.classList.toggle("open");
});
