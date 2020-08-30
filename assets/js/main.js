window.$ = window.jQuery = require('jquery');
require('jquery.flipster');

window.initFlipster = function(elem) {
    $(elem).flipster({
        spacing: -0.7
    });
    $(elem).find('.buegel').each(function () {
      $(this).on('click', function () {
        var id = $(this).data('content-id');
        var content = $('#' + id).html();
        $('#kleidungsstueck').html(content);
        //$('#kleidungsstueck').append('<button class="close-hanger">X</button>');
        $('#kleidungsstueck').css('visibility', 'visible')
        $('.close-hanger').on('click', function () {
          $('#kleidungsstueck').css('visibility', 'hidden')
          $('#kleidungsstueck').html('');
        });
      })
    });
};
