import { addConsent } from './iframe-consent';
import { initMap } from './maps/osm-map.js';
import { fullscreen } from './fullscreen.js';
import Swiper from 'swiper';
import { A11y, Navigation, Scrollbar, Keyboard, Mousewheel } from 'swiper/modules';
import EffectCoverflow from './swiper-addons/effect-coverflow.mjs';


window.addConsent = addConsent;
window.initMap = initMap;

window.$ = window.jQuery = require('jquery');
require('jquery.flipster');

function initFlipster(elem) {
  if (typeof elem === 'string') {
    elem = document.querySelector(elem);
  }

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

window.initFlipster = initFlipster;

function hangerHandler (elem) {
  const id = elem.dataset.contentId;
  const contentContainer = document.getElementById(id);
  const content = contentContainer ? contentContainer.innerHTML : '';
  const kleidungsstueck = document.querySelector('#kleidungsstueck');
  if (kleidungsstueck) {
    kleidungsstueck.innerHTML = content;

    if (!kleidungsstueck.classList.contains('active')) {
      setTimeout(function() {
        kleidungsstueck.classList.add('active');
      }, 500);
    }
  }

  const closeHangers = document.querySelectorAll('.close-hanger');
  closeHangers.forEach(function(closeHanger) {
    closeHanger.addEventListener('click', function handler() {
      if (kleidungsstueck) {
        setTimeout(function() {
          kleidungsstueck.classList.remove('active');
        }, 500);
      }
    });
  });
}


function initSlider(elem) {

  var swiper = new Swiper(elem, {
    modules: [A11y, Scrollbar, Navigation, Keyboard, Mousewheel, EffectCoverflow],
    effect: "coverflow",
    //cssMode: true,
    slideToClickedSlide:true,
    grabCursor: true,
    centeredSlides: true,
    initialSlide: 0,
    slidesPerView: "auto",
    mousewheel: true,
    loop: false,
    normalizeSlideIndex: false,
    slidesPerView: 'auto',
    spaceBetween: -210,
    coverflowEffect: {
      rotate: 65,
      stretch: 1,
      depth: 0,
      modifier: 1,
      slideShadows: false,
      spacing: 0.7,
      vanishingPointPerItem: true,
    },
    navigation: {
      nextEl: ".swiper-button-next",
      prevEl: ".swiper-button-prev",
    },
    keyboard: {
      enabled: true,
    },
    init: false,
    on: {
      click: function (swiper, event) {
        hangerHandler(event.target);
      },
      afterInit: function (swiper) {
        swiper.slideTo(0, 0)
        console.log('afterinit')
      },
    },
    scrollbar: {
      el: '.swiper-scrollbar',
      draggable: true,
    },
  });
  swiper.init();
  //swiper.slideTo(0, 0)
}

/*
let i =0;
cl = console.log;
console.log = function() {
  cl(i);
  i++;
};
*/


window.initSlider = initSlider;
