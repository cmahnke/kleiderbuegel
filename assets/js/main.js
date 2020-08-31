window.$ = window.jQuery = require('jquery');
require('jquery.flipster');

window.initFlipster = function(elem) {
    var buegel = $(elem).flipster({
        spacing: -0.7
    });
    $(elem).find('.buegel').each(function () {
      $(this).on('click', function () {
        var id = $(this).data('content-id');
        var content = $('#' + id).html();
        $('#kleidungsstueck').html(content);
        if (!$('#kleidungsstueck').hasClass('active')) {
          $('#kleidungsstueck').slideToggle(500, function() {
             $('#kleidungsstueck').addClass('active');
          });
       }

        $('.close-hanger').on('click', function () {

          $('#kleidungsstueck').slideToggle(500, function () {
            $('#kleidungsstueck').removeClass('active');
          });

        });
      })
    });
    buegel.flipster('jump', 0);
};
