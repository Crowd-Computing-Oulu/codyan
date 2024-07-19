$( document ).ready(function() {

    let NOT_STARTED = 0
    let RUNNING = 1
    let PAUSED = 2
    let FINISHED = 3
    let STOPPED = 4


    // Save the checkbox state to session storage whenever it changes
    $('#saveApiKey').on('change', function () {
        localStorage.setItem('saveApiKey', $(this).is(':checked'));
        if (!$(this).is(':checked')) {
            localStorage.removeItem('apikey');
        } else {
            localStorage.setItem('apikey', $('#apikey').val());
        }
    });

    // Save the API key to session storage whenever it changes, if the checkbox is checked
    $('#apikey').on('change', function () {
        if ($('#saveApiKey').is(':checked')) {
            localStorage.setItem('apikey', $(this).val());
        }
    });

    function updateProgress() {

        const status_strings = [
            'Not started',
            'Running',
            'Paused',
            'Finished',
            'Stopped (unfinished)'
        ]

        $.get("/process_status", function (data) {
            $("#progress-bar").css("width", data.progress + "%");

            $("#start-btn") .prop('disabled', 
                [RUNNING].includes(data.status))
            $("#pause-btn") .prop('disabled', 
                [NOT_STARTED, PAUSED, FINISHED, STOPPED].includes(data.status))
            $("#stop-btn")  .prop('disabled', 
                [NOT_STARTED, STOPPED].includes(data.status))

            if ([RUNNING,PAUSED].includes(data.status)) {
                setTimeout(updateProgress, 500);
                $("#process-status-string").text(data.string)
            } else {
                setTimeout(updateProgress, 2500);
                $("#process-status-string").text(data.string)
            }
            
            $("#process-status-type").text(status_strings[data.status])
        });
    }

    $('#questionsUploadButton').click(function(){
        var formData = new FormData();
        var file = $('#responsescsv')[0].files[0];
        if (file) {
            formData.append('responsescsv', file);
            $.ajax({
                url: '/upload',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function(response) {
                    alert('File uploaded successfully!');
                    location.reload(); // Reload the page after successful upload
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    alert('File upload failed!');
                }
            });
        } else {
            alert('Please select a file to upload.');
        }
    });

    $('#codebookUploadButton').click(function(){
        var formData = new FormData();
        var file = $('#codebookcsv')[0].files[0];
        if (file) {
            formData.append('codebookcsv', file);
            $.ajax({
                url: '/upload',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function(response) {
                    alert('File uploaded successfully!');
                    location.reload(); // Reload the page after successful upload
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    alert('File upload failed!');
                }
            });
        } else {
            alert('Please select a file to upload.');
        }
    });

    $('#referenceUploadButton').click(function(){
        var formData = new FormData();
        var file = $('#referencecsv')[0].files[0];
        if (file) {
            formData.append('referencecsv', file);
            $.ajax({
                url: '/upload',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                success: function(response) {
                    alert('File uploaded successfully!');
                    location.reload(); // Reload the page after successful upload
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    alert('File upload failed!');
                }
            });
        } else {
            alert('Please select a file to upload.');
        }
    });

    $("#start-btn").click(function () {
        var limit = $("#limit").val();
        var iterations = $("#iterations").val();
        var threads = $("#threads").val();
        var model = $("#model").val();
        var apikey = $("#apikey").val();
        if (!apikey) {
            $("#apikey").focus();
            return;
        }

        $.ajax({
            url: "/start_process",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                limit: limit,
                iterations: iterations,
                threads: threads,
                model: model,
                apikey: apikey
            }),
            success: function () {
                updateProgress();
            }
        });
    });

    $("#stop-btn").click(function () {
        $.get("/stop_process");
    });

    $("#stop-btn").click(function () {
        $.get("/stop_process");
    });

    $("#stop-btn").click(function () {
        $.get("/stop_process");
    });

    $("#pause-btn").click(function () {
        $.get("/pause_process");
    });

    $("#download-llm-output-btn").click(function () {
        window.location.href = '/download_llm_output';
    });

    $("#download-results-btn").click(function () {
        window.location.href = '/download_results';
    });

    $("#remove_questions").click(function () {
        $.get("/remove?file=responses", function(data) {
            // On success, reload the window
            window.location.reload();
        });
    });

    $("#remove_codes").click(function () {
        $.get("/remove?file=codes", function(data) {
            // On success, reload the window
            window.location.reload();
        });
    });

    $("#remove_reference").click(function () {
        $.get("/remove?file=reference", function(data) {
            // On success, reload the window
            window.location.reload();
        });
    });

    $("#load-results-btn").click(function () {
        // Get the value of the pvalue text field
        let pvalue = $("#pvalue").val();

        // Construct the URL with the pvalue parameter
        let url = `/get_results?pvalue=${pvalue}`;

        // Make the AJAX GET request with the updated URL
        $.get(url, function (data) {
            let resultsHtml = '';
            if(data.icr){
                $("#icr").text("Krippendorff's Alpha using MASI: " + data.icr.toFixed(2))
            }
            results = data.results
            resultsHtml += `<div class="card p-2" style="max-height: 20vh; overflow: scroll">`;
            for (const [question, responses] of Object.entries(results)) {
                resultsHtml += `<strong>Question ${question}</strong><br>`;
                for (const [response, ratios] of Object.entries(responses)) {
                    resultsHtml += `<span>${response} - `;
                    let ratiosArray = [];
                    for (const [code, ratio] of Object.entries(ratios)) {
                        ratiosArray.push(`${code} (p = ${(ratio).toFixed(2)})`);
                    }
                    resultsHtml += ratiosArray.join(', ') + '</span><br>';
                }
            }
            resultsHtml += `</div>`;
            $("#results-container").html(resultsHtml);

            $("#download-results-btn") .prop('disabled', false)
        });
    });

    $("#pvalue").on( "change", function() {
        $("#download-results-btn") .prop('disabled', true)
    } );

    $("#download-results-btn") .prop('disabled', true)
    
    // Function to save the selected tab to localStorage
    function saveSelectedTab(tabId) {
        localStorage.setItem('selectedTab', tabId);
    }

    // Function to load the selected tab from localStorage
    function loadSelectedTab() {
        var selectedTab = localStorage.getItem('selectedTab');
        if (!selectedTab) {
            selectedTab = "home-tab"
        }
        const selectedTabElement = document.querySelector(`#${selectedTab}`);
        if (selectedTabElement) {
            document.querySelector(`#home-tab`).click();
            selectedTabElement.click();
        }
        
    }



    updateProgress();
    loadSelectedTab();

    document.querySelectorAll('.sub-nav').forEach(tab => {
        tab.addEventListener('click', function() {
            saveSelectedTab(this.id);
        });
    });


    // Load the checkbox state and API key from session storage when the page loads
    if (localStorage.getItem('saveApiKey') === 'true') {
        $('#saveApiKey').prop('checked', true);
        if (localStorage.getItem('apikey')) {
            $('#apikey').val(localStorage.getItem('apikey'));
        }
    }
    
});

function copyToClipboard(id) {
    // Get the text from the span element
    var sessionIdText = id
    // Create a temporary input element
    var tempInput = document.createElement('input');
    tempInput.value = sessionIdText.replace('Session ID: ', ''); // Remove the label part
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);
    alert('Session ID copied to clipboard!'); // Optional: show a confirmation message
}