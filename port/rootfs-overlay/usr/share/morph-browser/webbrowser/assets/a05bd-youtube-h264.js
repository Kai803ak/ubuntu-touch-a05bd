// A05BD: request the locally accelerated codec only on YouTube.
// No networking, cookies, storage, or changes to other websites.
(() => {
  'use strict';
  if (!/(^|\.)(youtube\.com|youtube-nocookie\.com)$/.test(location.hostname)) return;
  if (window.__a05bdH264Preference) return;
  const blocked = type => typeof type === 'string' && /\b(vp8|vp9|vp09|av01)\b/i.test(type);
  const canPlay = HTMLMediaElement.prototype.canPlayType;
  HTMLMediaElement.prototype.canPlayType = function(type) {
    return blocked(type) ? '' : canPlay.call(this, type);
  };
  for (const source of [window.MediaSource, window.ManagedMediaSource]) {
    if (!source || !source.isTypeSupported) continue;
    const supported = source.isTypeSupported;
    source.isTypeSupported = function(type) {
      return !blocked(type) && supported.call(this, type);
    };
  }
  if (navigator.mediaCapabilities && navigator.mediaCapabilities.decodingInfo) {
    const capabilities = navigator.mediaCapabilities;
    const decodingInfo = capabilities.decodingInfo;
    capabilities.decodingInfo = function(config) {
      if (config && config.video && blocked(config.video.contentType))
        return Promise.resolve({supported: false, smooth: false, powerEfficient: false});
      return decodingInfo.call(this, config);
    };
  }
  Object.defineProperty(window, '__a05bdH264Preference', {value: true});
})();
