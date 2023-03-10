$(document).ready(function() {
    $(".advanced-details-button").click(function() {
      $(".search-results-container").toggle();

      if ($(this).text() === "Show Advanced Search Results") {
        $(this).text("Hide Search Results");
      } else {
        $(this).text("Show Advanced Search Results");
      }
    });
  });