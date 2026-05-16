const GA_MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID;

let isInitialized = false;

export function initGoogleAnalytics() {
  if (!GA_MEASUREMENT_ID || isInitialized || typeof window === 'undefined') {
    return;
  }

  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag() {
    window.dataLayer.push(arguments);
  };

  window.gtag('js', new Date());
  window.gtag('config', GA_MEASUREMENT_ID);

  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_MEASUREMENT_ID)}`;
  document.head.appendChild(script);

  isInitialized = true;
}

export function trackEvent(eventName, parameters = {}) {
  if (!isInitialized || typeof window.gtag !== 'function') {
    return;
  }

  window.gtag('event', eventName, parameters);
}
