import Swiper from 'swiper';
import { A11y, Navigation, Scrollbar, Keyboard, Mousewheel } from 'swiper/modules';

const defaultSize = 330;

function wrapInLink(element: Element, url: string | undefined) {
  const link = document.createElement('a');
  link.href = url as string;
  link.setAttribute('target', '_blank');

  element.parentNode!.insertBefore(link, element);
  link.appendChild(element);

  return link;
}

function slider(elem: Element | null, size?: number) {
  if (size === undefined) {
    size = defaultSize;
  }

  elem!.querySelectorAll<HTMLPictureElement>('.swiper-slide picture').forEach(picture => {
    const url = (picture.parentNode!.parentNode as HTMLElement).dataset.link;
    picture.parentNode!.querySelector('source')!.remove();
    wrapInLink(picture, url);
  });

  const margin = size / 11;
  const spacing = margin * 7 * -1;

  const swiper = new Swiper(elem as HTMLElement, {
    modules: [A11y, Scrollbar, Navigation, Keyboard, Mousewheel],
    slideToClickedSlide:true,
    grabCursor: true,
    slidesPerView: 1,
    centeredSlides: true,

    initialSlide: 0,
    mousewheel: true,
    loop: true,
    normalizeSlideIndex: false,
    //spaceBetween: spacing,
    navigation: {
      nextEl: ".swiper-button-next",
      prevEl: ".swiper-button-prev",
    },
    keyboard: {
      enabled: true,
    },

    /*
    on: {
      click: function (swiper, event) {
        const link =
        console.log(event.target.parentNode.parentNode.parentNode.);
      },
    },
    */
    scrollbar: {
      el: '.swiper-scrollbar',
      draggable: true,
      snapOnRelease: true,
    },
  });

}

window.slider = slider;

document.addEventListener('DOMContentLoaded', function () {
  const elem = document.querySelector('.swiper');
  if (elem) {
    slider(elem);
  }
});
