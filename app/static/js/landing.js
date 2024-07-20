// Select the element that displays the data type
const dataText = document.querySelector(".data-text");
// Array of data types to toggle between
const dataTypes = ["PDF", "CSV","Excel"];
let currentIndex = 0;

// Function to toggle the displayed data type
function toggleDataType() {
  // Add the fade-out effect
  dataText.classList.add("fade");

  // Change the text after the fade-out effect
  setTimeout(() => {
    currentIndex = (currentIndex + 1) % dataTypes.length;
    dataText.textContent = dataTypes[currentIndex];
    // Remove the fade-out effect to show the new text
    dataText.classList.remove("fade");
  }, 500); // Duration of the fade-out effect
}

// Toggle the data type every 2 seconds
setInterval(toggleDataType, 2000);

// Lazy loading for the video
document.addEventListener("DOMContentLoaded", function() {
  var lazyVideos = [].slice.call(document.querySelectorAll("video.lazy-load"));
  var fallbackImage = document.querySelector(".fallback-image");

  if ("IntersectionObserver" in window) {
    var lazyVideoObserver = new IntersectionObserver(function(entries, observer) {
      entries.forEach(function(video) {
        if (video.isIntersecting) {
          for (var source in video.target.children) {
            var videoSource = video.target.children[source];
            if (typeof videoSource.tagName === "string" && videoSource.tagName === "SOURCE") {
              videoSource.src = videoSource.getAttribute("data-src");
            }
          }

          video.target.load();
          video.target.classList.remove("lazy-load");
          lazyVideoObserver.unobserve(video.target);

          // Hide the fallback image when the video starts loading
          fallbackImage.style.display = "none";
        }
      });
    });

    lazyVideos.forEach(function(lazyVideo) {
      lazyVideoObserver.observe(lazyVideo);
    });
  } else {
    console.log("Intersection Observer is not supported");
    // If Intersection Observer is not supported, hide the video and show the fallback image
    lazyVideos.forEach(function(lazyVideo) {
      lazyVideo.style.display = "none";
    });
    fallbackImage.style.display = "block";
  }

  // Error handling for video loading
  lazyVideos.forEach(function(lazyVideo) {
    lazyVideo.addEventListener("error", function(event) {
      console.log("Error loading video:", event);
      lazyVideo.style.display = "none";
      fallbackImage.style.display = "block";
    });
  });
});