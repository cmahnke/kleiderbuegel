// import createShadow from '../../shared/create-shadow.mjs';
// import effectInit from '../../shared/effect-init.mjs';
// import effectTarget from '../../shared/effect-target.mjs';
// import { getRotateFix, getSlideTransformEl } from '../../shared/utils.mjs';

import { getSlideTransformEl, effectTarget, effectInit, createShadow, getRotateFix } from 'swiper/effect-utils';

export default function EffectCoverflow({ swiper, extendParams, on }) {
  extendParams({
    coverflowEffect: {
      rotate: 50,
      stretch: 0,
      depth: 0,
      scale: 1,
      modifier: 1,
      fixedRotation: true,
      slideShadows: false,
      vanishingPointPerItem: true,
    },
  });

  const setTranslate = () => {
    const { width: swiperWidth, height: swiperHeight, slides, slidesSizesGrid } = swiper;
    const params = swiper.params.coverflowEffect;
    const isHorizontal = swiper.isHorizontal();
    const transform = swiper.translate;
    const center = isHorizontal ? -transform + swiperWidth / 2 : -transform + swiperHeight / 2;
    const rotate = isHorizontal ? params.rotate : -params.rotate;
    const translate = params.depth;
    const r = getRotateFix(swiper);
    // Each slide offset from center
    //for (let i = 0, length = slides.length; i < length; i += 1) {
    for (let i = 0, length = swiper.visibleSlidesIndexes.length; i < length; i += 1) {
    
      //const slideEl = slides[i];
      const slideEl = slides[swiper.visibleSlidesIndexes[i]];
      //const slideSize = slidesSizesGrid[i];
      const slideSize = slidesSizesGrid[swiper.visibleSlidesIndexes[i]];
      const slideOffset = slideEl.swiperSlideOffset;
      const centerOffset = (center - slideOffset - slideSize / 2) / slideSize;
      const offsetMultiplier =
        typeof params.modifier === 'function'
          ? params.modifier(centerOffset)
          : centerOffset * params.modifier;

      let rotateY = isHorizontal ? rotate * offsetMultiplier : 0;
      let rotateX = isHorizontal ? 0 : rotate * offsetMultiplier;

      if (params.fixedRotation) {
        rotateX = Math.max(Math.min(rotateX, rotate), -rotate);
        rotateY = Math.max(Math.min(rotateY, rotate), -rotate);
      }
      
      // var rotateZ = 0
      let translateZ = -translate * Math.abs(offsetMultiplier);

      let stretch = params.stretch;
      // Allow percentage to make a relative stretch for responsive sliders
      if (typeof stretch === 'string' && stretch.indexOf('%') !== -1) {
        stretch = (parseFloat(params.stretch) / 100) * slideSize;
      }

      let translateY = isHorizontal ? 0 : stretch * offsetMultiplier;
      let translateX = isHorizontal ? stretch * offsetMultiplier : 0;

      let scale = 1 - (1 - params.scale) * Math.abs(offsetMultiplier);

      // This is needed for (almost) correct spacing with negative spaceBetween value
      let correctionX = 0
      if ("spaceBetween" in swiper.params) {
        if (centerOffset < 0) {
          correctionX = -1 * swiper.params.spaceBetween;
        } else if (centerOffset > 0) {
          correctionX = swiper.params.spaceBetween;
        } 
      }
      translateX = translateX + correctionX

      // Fix for ultra small values
      if (Math.abs(translateX) < 0.001) translateX = 0;
      if (Math.abs(translateY) < 0.001) translateY = 0;
      if (Math.abs(translateZ) < 0.001) translateZ = 0;
      if (Math.abs(rotateY) < 0.001) rotateY = 0;
      if (Math.abs(rotateX) < 0.001) rotateX = 0;
      if (Math.abs(scale) < 0.001) scale = 0;

      const slideTransform = `translate3d(${translateX}px,${translateY}px,${translateZ}px) rotateX(${r(
         rotateX,
       )}deg) rotateY(${r(rotateY)}deg) scale(${scale})`;
      const targetEl = effectTarget(params, slideEl);
      targetEl.style.transform = slideTransform;

      // Calculate z-index correctly
      const zIndex = swiper.slides.length - Math.abs((swiper.activeIndex -1) - swiper.visibleSlidesIndexes[i]);
      slideEl.style.zIndex = zIndex
      //slideEl.style.zIndex = -Math.abs(Math.round(offsetMultiplier)) + 1;

      if (params.slideShadows) {
        // Set shadows
        let shadowBeforeEl = isHorizontal
          ? slideEl.querySelector('.swiper-slide-shadow-left')
          : slideEl.querySelector('.swiper-slide-shadow-top');
        let shadowAfterEl = isHorizontal
          ? slideEl.querySelector('.swiper-slide-shadow-right')
          : slideEl.querySelector('.swiper-slide-shadow-bottom');
        if (!shadowBeforeEl) {
          shadowBeforeEl = createShadow('coverflow', slideEl, isHorizontal ? 'left' : 'top');
        }
        if (!shadowAfterEl) {
          shadowAfterEl = createShadow('coverflow', slideEl, isHorizontal ? 'right' : 'bottom');
        }
        if (shadowBeforeEl)
          shadowBeforeEl.style.opacity = offsetMultiplier > 0 ? offsetMultiplier : 0;
        if (shadowAfterEl)
          shadowAfterEl.style.opacity = -offsetMultiplier > 0 ? -offsetMultiplier : 0;
      }
    }
  };
  const setTransition = (duration) => {
    const transformElements = swiper.slides.map((slideEl) => getSlideTransformEl(slideEl));

    transformElements.forEach((el) => {
      el.style.transitionDuration = `${duration}ms`;
      el.querySelectorAll(
        '.swiper-slide-shadow-top, .swiper-slide-shadow-right, .swiper-slide-shadow-bottom, .swiper-slide-shadow-left',
      ).forEach((shadowEl) => {
        shadowEl.style.transitionDuration = `${duration}ms`;
      });
    });
  };

  effectInit({
    effect: 'coverflow',
    swiper,
    on,
    setTranslate,
    setTransition,
    perspective: () => {return !swiper.params.coverflowEffect.vanishingPointPerItem},
    overwriteParams: () => ({
      watchSlidesProgress: true,
      centeredSlides: true,
      initialSlide: 0,
    }),
  });
}