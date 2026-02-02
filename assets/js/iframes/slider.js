import { A11y, Navigation, Scrollbar, Keyboard, Mousewheel } from 'swiper/modules';


function initSlider(elem, size) {
  if (size === undefined) {
    size = defaultSize;
  }

  const margin = size / 11;
  const spacing = margin * 7 * -1;

  var swiper = new Swiper(elem, {
    modules: [A11y, Scrollbar, Navigation, Keyboard, Mousewheel],
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

window.slider = slider;
