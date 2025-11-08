import { addConsent } from './iframe-consent';
import { initMap } from './maps/osm-map.js';
import { fullscreen } from './fullscreen.js';
import Swiper from 'swiper';
import { A11y, Navigation, Scrollbar, Keyboard, Mousewheel } from 'swiper/modules';
import EffectCoverflow from './swiper-addons/effect-coverflow.mjs';


const defaultSize = 330;

window.addConsent = addConsent;
window.initMap = initMap;

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


function initSlider(elem, size) {
  if (size === undefined) {
    size = defaultSize;
  }

  const margin = size / 11;
  const spacing = margin * 7 * -1;

  var swiper = new Swiper(elem, {
    modules: [A11y, Scrollbar, Navigation, Keyboard, Mousewheel, EffectCoverflow],
    effect: "coverflow",
    //cssMode: true,
    slideToClickedSlide:true,
    grabCursor: true,
    centeredSlides: true,
    initialSlide: 0,
    mousewheel: true,
    loop: false,
    normalizeSlideIndex: false,
    slidesPerView: "auto",
    spaceBetween: spacing,
    coverflowEffect: {
      rotate: 65,
      stretch: 1,
      depth: 0,
      modifier: 1,
      slideShadows: false,
      spacing: 0.7,
      vanishingPointPerItem: true,
      activeMarginRight:  margin,
      activeMarginLeft:  margin,
    },
    navigation: {
      nextEl: ".swiper-button-next",
      prevEl: ".swiper-button-prev",
    },
    keyboard: {
      enabled: true,
    },
    init: false,

    onAny(eventName, ...args) {
     console.log('Event: ', eventName);
     console.log('Event data: ', args);
   },

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
      snapOnRelease: true,
    },
  });
  swiper.init();
}

function initHome(elem) {
  let size = defaultSize;

  if (window.screen.width <= 740) {
    size = defaultSize / 2
  }
  initSlider(elem, size)
}

window.initSlider = initSlider;
window.initHome = initHome;
