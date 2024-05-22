const fileInput = document.getElementById('pdfFile');
const uploadedFilesContainer = document.getElementById('uploadedFiles');
let allUploadedFiles = []; // Array to store all uploaded files

const form = document.querySelector('form');
const submitButton = document.getElementById('submitButton');
const loader = submitButton.querySelector('.spinner-border');

fileInput.addEventListener('change', function(event) {
    const fileList = event.target.files;
    const selectedFiles = Array.from(fileList);

    // Add newly uploaded files to the list of all uploaded files
    allUploadedFiles = allUploadedFiles.concat(selectedFiles);

    // Display all uploaded files
    displayUploadedFiles(allUploadedFiles);
    
    // Create a new DataTransfer object
    const dataTransfer = new DataTransfer();

    // Add all uploaded files to the DataTransfer object
    allUploadedFiles.forEach(file => {
    dataTransfer.items.add(file);
    });

    // Update the file input field with the new DataTransfer object
    fileInput.files = dataTransfer.files;
});

function displayUploadedFiles(files) {
    // Clear the existing uploaded files
    uploadedFilesContainer.innerHTML = '';

    // Create a list to display the uploaded files
    const fileList = document.createElement('ul');
    fileList.classList.add('list-group');

    // Iterate over each file and create a list item
    files.forEach(file => {
        const listItem = document.createElement('li');
        listItem.classList.add('list-group-item');
        listItem.textContent = file.name;
        fileList.appendChild(listItem);
    });

    // Append the file list to the container
    uploadedFilesContainer.appendChild(fileList);
}

// Add click event listener to the submit button
submitButton.addEventListener("click", function(event) {
  
  // Add a history entry
  var url = window.location.href; // Get the current URL
  var stateObj = { page: "submitted" }; // Create a state object
  history.pushState(stateObj, "Submitted", url); // Add the entry to the history stack
  
  // Prevent the default form submission behavior
  event.preventDefault();

  // Show the spinner
  var spinner = submitButton.querySelector(".spinner-border");
  spinner.classList.remove("d-none");

  // Submit the form
  form.submit();

  submitButton.disabled = true;
});