document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const resultDiv = document.getElementById('result');
    const backToTopLink = document.getElementById('back-to-top');

    // Handle form submission
    form.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData(form);
        const fileInput = document.getElementById('file-input');
        const formatSelect = document.getElementById('format-select');

        if (fileInput.files.length === 0) {
            displayError('Please select a file.');
            return;
        }

        clearResults();
        displayLoadingMessage();

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.ok ? response.json() : response.json().then(data => Promise.reject(data.error || 'An error occurred')))
        .then(data => {
            displayResults(data, formatSelect.value);
        })
        .catch(error => {
            displayError(`An error occurred: ${error}`);
        });
    });

    function displayLoadingMessage() {
        resultDiv.innerHTML = '<p>Processing your image, please wait...</p>';
    }

    function displayResults(data, format) {
        let output = '';
        switch (format) {
            case 'text':
                output = `<h3>Extracted Text:</h3><pre>${data.text}</pre>`;
                break;
            case 'json':
                output = `<h3>JSON Output:</h3><pre>${data.json}</pre>`;
                break;
            case 'csv':
                output = `<h3>CSV Output:</h3><pre>${data.csv}</pre>`;
                break;
        }
        resultDiv.innerHTML = output;
    }

    function displayError(message) {
        resultDiv.innerHTML = `<p style="color: red;">${message}</p>`;
    }

    function clearResults() {
        resultDiv.innerHTML = '';
    }

    // Handle "Back to Top" link click
    backToTopLink.addEventListener('click', function(event) {
        event.preventDefault();
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
});
