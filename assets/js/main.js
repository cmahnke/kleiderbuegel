import { addConsent } from './iframe-consent';
import { initMap } from './maps/osm-map.js';
import { fullscreen } from './fullscreen.js';

window.addConsent = addConsent;
window.initMap = initMap;

window.$ = window.jQuery = require('jquery');
require('jquery.flipster');

window.initFlipster = function(elem) {
  console.log(elem);
    var buegel = $(elem).flipster({
        spacing: -0.7
    });
    $(elem).find('.buegel').each(function() {
        $(this).on('click', function() {
            var id = $(this).data('content-id');
            var subList = $('#' + id + ' ul');
            subList.removeClass('flipster__container');
            subList.removeAttr('style');
            subList.find(".flipster__item__content, .flipster__item, .flipster__item--future").each(function() {
              $(this).removeClass('flipster__item__content');
              $(this).removeClass('flipster__item');
              $(this).removeClass('flipster__item--future');
              // TODO: Find a better way
              $(this).removeClass('flipster__item--future-1');
              $(this).removeClass('flipster__item--future-2');
              $(this).removeClass('flipster__item--future-3');
              $(this).removeClass('flipster__item--future-4');
              $(this).removeAttr('style');
            });

            var content = $('#' + id).html();
            $('#kleidungsstueck').html(content);
            if (!$('#kleidungsstueck').hasClass('active')) {
                $('#kleidungsstueck').slideToggle(500, function() {
                    $('#kleidungsstueck').addClass('active');
                });
            }
            $('.close-hanger').on('click', function() {
                $('#kleidungsstueck').slideToggle(500, function() {
                    $('#kleidungsstueck').removeClass('active');
                });

            });
        })
    });
    buegel.flipster('jump', 0);
};
