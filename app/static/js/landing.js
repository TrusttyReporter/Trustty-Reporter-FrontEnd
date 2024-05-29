// landing.js
const dataText = document.querySelector(".data-text");
const dataTypes = ["PDF", "CSV"];
let currentIndex = 0;

function toggleDataType() {
  dataText.classList.add("fade");
  
  setTimeout(() => {
    currentIndex = (currentIndex + 1) % dataTypes.length;
    dataText.textContent = dataTypes[currentIndex];
    dataText.classList.remove("fade");
  }, 500);
}

setInterval(toggleDataType, 2000);