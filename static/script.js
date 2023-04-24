$(document).ready(function() {
    $(".advanced-details-button").click(function() {
      $(".search-results-container").toggle();

      if ($(this).text() === "Show Advanced Search Results") {
        $(this).text("Hide Search Results");
      } else {
        $(this).text("Show Advanced Search Results");
      }
    });

    // add event listener to toggle switch
    $('#clustering-toggle').change(function() {
        // check if toggle switch is checked
        if($(this).is(':checked')) {
        // show target div
        $('#clustering-container').show();
        } else {
        // hide target div
        $('#clustering-container').hide();
        }
    });

    $('#query-toggle').change(function() {
        // check if toggle switch is checked
        if($(this).is(':checked')) {
        // show target div
        $('#query-expansion-container').show();
        } else {
        // hide target div
        $('#query-expansion-container').hide();
        }
    });

    $('#clear-icon').on('click', () => {
      // Clear value of search input
      $('#search-input').val('');
    });
  });