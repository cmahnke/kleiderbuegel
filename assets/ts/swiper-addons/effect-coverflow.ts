import type { Swiper } from 'swiper';
import { getSlideTransformEl, effectTarget, effectInit, createShadow, getRotateFix } from 'swiper/effect-utils';

export interface KleiderbuegelCoverflowEffectOptions {
  rotate?: number;
  stretch?: number | `${number}%`;
  depth?: number;
  scale?: number;
  modifier?: number | ((centerOffset: number) => number);
  fixedRotation?: boolean;
  slideShadows?: boolean;
  vanishingPointPerItem?: boolean;
  activeMarginRight?: number;
  activeMarginLeft?: number;
  spacing?: number;
}

interface SwiperModuleContext {
  swiper: Swiper;
  extendParams: (obj: Record<string, unknown>) => void;
  on: Swiper['on'];
}

export default function EffectCoverflow({ swiper, extendParams, on }: SwiperModuleContext) {
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
      activeMarginRight: 0,
      activeMarginLeft: 0,
    },
  });

  const setTranslate = () => {
    const { width: swiperWidth, height: swiperHeight, slides, slidesSizesGrid } = swiper;
    const params = swiper.params.coverflowEffect as KleiderbuegelCoverflowEffectOptions;
    const isHorizontal = swiper.isHorizontal();
    const transform = swiper.translate;
    const center = isHorizontal ? -transform + swiperWidth / 2 : -transform + swiperHeight / 2;
    const rotateValue = params.rotate as number;
    const rotate = isHorizontal ? rotateValue : -rotateValue;
    const translate = params.depth as number;
    const r = getRotateFix(swiper);
    // Each slide offset from center
    //for (let i = 0, length = slides.length; i < length; i += 1) {
    for (let i = 0, length = swiper.visibleSlidesIndexes.length; i < length; i += 1) {

      //const slideEl = slides[i];
      const slideEl = slides[swiper.visibleSlidesIndexes[i]];
      //const slideSize = slidesSizesGrid[i];
      const slideSize = slidesSizesGrid[swiper.visibleSlidesIndexes[i]];
      const slideOffset = slideEl.swiperSlideOffset as number;
      const centerOffset = (center - slideOffset - slideSize / 2) / slideSize;
      const offsetMultiplier =
        typeof params.modifier === 'function'
          ? params.modifier(centerOffset)
          : centerOffset * (params.modifier as number);

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
        stretch = (parseFloat(stretch) / 100) * slideSize;
      }

      let translateY = isHorizontal ? 0 : (stretch as number) * offsetMultiplier;
      let translateX = isHorizontal ? (stretch as number) * offsetMultiplier : 0;

      let scale = 1 - (1 - (params.scale as number)) * Math.abs(offsetMultiplier);

      // This is needed for (almost) correct spacing with negative spaceBetween value
      let correctionX = 0
      if ("spaceBetween" in swiper.params) {
        if (centerOffset < 0) {
          correctionX = -1 * (swiper.params.spaceBetween as number) + (params.activeMarginLeft as number);
        } else if (centerOffset > 0) {
          correctionX = (swiper.params.spaceBetween as number) - (params.activeMarginRight as number);
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
      const zIndex = Math.round(swiper.slides.length - Math.abs(centerOffset * 4))
      slideEl.style.zIndex = String(zIndex)
      //slideEl.style.zIndex = -Math.abs(Math.round(offsetMultiplier)) + 1;

      if (params.slideShadows) {
        // Set shadows
        let shadowBeforeEl = isHorizontal
          ? slideEl.querySelector<HTMLElement>('.swiper-slide-shadow-left')
          : slideEl.querySelector<HTMLElement>('.swiper-slide-shadow-top');
        let shadowAfterEl = isHorizontal
          ? slideEl.querySelector<HTMLElement>('.swiper-slide-shadow-right')
          : slideEl.querySelector<HTMLElement>('.swiper-slide-shadow-bottom');
        if (!shadowBeforeEl) {
          shadowBeforeEl = createShadow('coverflow', slideEl, isHorizontal ? 'left' : 'top');
        }
        if (!shadowAfterEl) {
          shadowAfterEl = createShadow('coverflow', slideEl, isHorizontal ? 'right' : 'bottom');
        }
        if (shadowBeforeEl)
          shadowBeforeEl.style.opacity = String(offsetMultiplier > 0 ? offsetMultiplier : 0);
        if (shadowAfterEl)
          shadowAfterEl.style.opacity = String(-offsetMultiplier > 0 ? -offsetMultiplier : 0);
      }
    }
  };
  const setTransition = (duration: number) => {
    const transformElements = swiper.slides.map((slideEl) => getSlideTransformEl(slideEl));

    transformElements.forEach((el) => {
      el.style.transitionDuration = `${duration}ms`;
      el.querySelectorAll<HTMLElement>(
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
    perspective: () => {return !(swiper.params.coverflowEffect as KleiderbuegelCoverflowEffectOptions | undefined)?.vanishingPointPerItem},
    overwriteParams: () => ({
      watchSlidesProgress: true,
      centeredSlides: true,
      initialSlide: 0,
    }),
  });
}
