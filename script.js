$(document).ready(function() {
    $("#search-form").submit(function() {
        // Get the search query from the input field
        var query = $("#search-bar").val();

        // Make an API request to get search results
        $.ajax({
            url: "https://www.googleapis.com/customsearch/v1",
            data: {
                q: query,
                cx: config.cx, // Replace <YOUR_SEARCH_ENGINE_ID> with your search engine ID
            },
            success: function(response) {
                // Parse the JSON response and display the search results
                var resultsContainer = $("#search-results");
                resultsContainer.empty();
                $.each(response.items, function(index, item) {
                    var resultItem = $("<div>");
                    resultItem.html("<a href='" + item.link + "'>" + item.title + "</a><br>" + item.snippet);
                    resultsContainer.append(resultItem);
                });
            },
            error: function() {
                console.log("Request failed.");
            }
        });

        // Prevent the form from submitting and reloading the page
        return false;
    });
});