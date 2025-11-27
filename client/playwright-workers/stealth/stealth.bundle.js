// scrapebot-saas/client/playwright-workers/stealth/stealth.bundle.js
// Comprehensive stealth evasion bundle for Raeburn-Scraper Playwright Workers
// This script is injected into the browser page context.
// It expects window.SESSION_FINGERPRINT to be set by the worker before injection.

(() => {
  'use strict';

  // --- 1. Session Fingerprint ---
  // Retrieve the session-specific fingerprint injected by the Node.js worker.
  // This ensures consistency across page loads within a single scraping job.
  const fingerprint = window.SESSION_FINGERPRINT || {
    id: 'default-' + Math.random().toString(36).substr(2, 9),
    deviceMemory: 8,
    hardwareConcurrency: 4,
    timezone: 'UTC',
    screenNoise: { width: 0, height: 0 },
    userAgent: navigator.userAgent // Fallback
  };

  console.log(`[Raeburn-Scraper Stealth] Applying profile: ${fingerprint.id}`);


  // --- 2. Core Stealth Evasions ---

  // --- Navigator.webdriver ---
  // Remove the webdriver property that indicates automation.
  Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
  });

  // --- Chrome Runtime ---
  // Mock the chrome.runtime API to mimic a real extension environment.
  // Use Proxy for more robust mocking, especially against toString checks.
  try {
    window.chrome = new Proxy(
      window.chrome || {},
      {
        get(target, prop) {
          if (prop === 'runtime') {
            return {
              // Basic methods often checked
              connect: () => ({
                onMessage: { addListener: () => {} },
                postMessage: () => {},
              }),
              sendMessage: () => {},
              // Common events
              ...Object.fromEntries(
                ['onMessage', 'onConnect', 'onInstalled', 'onStartup', 'onSuspend', 'onSuspendCanceled', 'onUpdateAvailable']
                  .map(event => [event, { addListener: () => {} }])
              ),
              id: 'raeburn-scraper-extension-id', // Generic ID
            };
          }
          // Return other properties if accessed
          return target[prop];
        }
      }
    );
  } catch (e) {
    // In case Proxy is not available or blocked, fall back to simple object
    console.warn('[Raeburn-Scraper Stealth] Proxy not supported for chrome.runtime, using fallback.');
    if (!window.chrome) window.chrome = {};
    if (!window.chrome.runtime) {
      window.chrome.runtime = {
        connect: () => ({ onMessage: { addListener: () => {} }, postMessage: () => {} }),
        sendMessage: () => {},
        onMessage: { addListener: () => {} },
        // ... add other methods as needed
      };
    }
  }

  // --- Plugins and MimeTypes ---
  // Define realistic plugins and mime types to match a standard Chrome browser.
  const createPluginArray = (items) => {
    const pluginArray = new Array(items.length);
    items.forEach((item, index) => {
      pluginArray[index] = item;
      pluginArray[item.name] = item;
    });
    pluginArray.refresh = () => { };
    pluginArray.item = (index) => pluginArray[index];
    pluginArray.namedItem = (name) => pluginArray[name];
    pluginArray.length = items.length;
    return pluginArray;
  };

  const pluginsData = [
    {
      name: 'Chrome PDF Plugin',
      filename: 'internal-pdf-viewer',
      description: 'Portable Document Format'
    },
    {
      name: 'Chrome PDF Viewer',
      filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', // Real Chrome PDF Viewer extension ID
      description: ''
    },
    {
      name: 'Native Client',
      filename: 'internal-nacl-plugin',
      description: ''
    }
  ];

  const mimeTypesData = [
    { type: 'application/pdf', description: 'Portable Document Format', suffixes: 'pdf' },
    { type: 'text/pdf', description: 'Portable Document Format', suffixes: 'pdf' }
  ];

  Object.defineProperty(navigator, 'plugins', {
    get: () => createPluginArray(pluginsData)
  });

  Object.defineProperty(navigator, 'mimeTypes', {
    get: () => createPluginArray(mimeTypesData)
  });


  // --- Navigator Properties (using session fingerprint) ---
  // Override hardware specs and languages with session-consistent values.
  Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
  });

  Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => fingerprint.hardwareConcurrency
  });

  Object.defineProperty(navigator, 'deviceMemory', {
    get: () => fingerprint.deviceMemory
  });


  // --- Screen Properties (using session fingerprint) ---
  // Add consistent noise to screen dimensions.
  Object.defineProperty(screen, 'width', {
    get: () => window.screen.width + fingerprint.screenNoise.width
  });
  Object.defineProperty(screen, 'height', {
    get: () => window.screen.height + fingerprint.screenNoise.height
  });
  Object.defineProperty(screen, 'availWidth', {
    get: () => window.screen.availWidth + fingerprint.screenNoise.width
  });
  Object.defineProperty(screen, 'availHeight', {
    get: () => window.screen.availHeight + fingerprint.screenNoise.height
  });


  // --- WebGL Fingerprinting ---
  // Spoof WebGL parameters to return common GPU strings.
  const webglParametersToSpoof = {
    0x9245: 'Intel Inc.', // UNMASKED_VENDOR_WEBGL
    0x9246: 'Intel Iris OpenGL Engine', // UNMASKED_RENDERER_WEBGL
    0x1F00: 'WebKit', // VENDOR
    0x1F01: 'WebKit WebGL', // RENDERER
    0x1F02: 'WebGL 1.0', // VERSION
    // Add more parameters as needed based on common values
  };

  const overrideWebGL = (contextPrototype) => {
    if (contextPrototype && contextPrototype.getParameter) {
      const originalGetParameter = contextPrototype.getParameter;
      contextPrototype.getParameter = function (parameter) {
        if (parameter in webglParametersToSpoof) {
          return webglParametersToSpoof[parameter];
        }
        return originalGetParameter.call(this, parameter);
      };
    }
  };

  // Apply to both WebGLRenderingContext and WebGL2RenderingContext
  overrideWebGL(WebGLRenderingContext ? WebGLRenderingContext.prototype : undefined);
  overrideWebGL(WebGL2RenderingContext ? WebGL2RenderingContext.prototype : undefined);


  // --- Timezone Spoofing (using session fingerprint) ---
  // Override Intl.DateTimeFormat and Date timezone methods.
  const OriginalDateTimeFormat = Intl.DateTimeFormat;
  // Store the original prototype to avoid potential issues
  const OriginalDateTimeFormatPrototype = OriginalDateTimeFormat.prototype;

  Intl.DateTimeFormat = function (locales, options) {
    options = options || {};
    // Use the timezone from the session fingerprint
    options.timeZone = fingerprint.timezone;
    return new OriginalDateTimeFormat(locales, options);
  };
  // Restore the prototype chain carefully
  Intl.DateTimeFormat.prototype = OriginalDateTimeFormatPrototype;

  // Map common timezones to their offset in minutes
  const timezoneOffsets = {
    'UTC': 0,
    'America/New_York': 300, // EDT, adjust for EST (-300)
    'America/Chicago': 360,  // CDT, adjust for CST (-360)
    'America/Denver': 420,   // MDT, adjust for MST (-420)
    'America/Los_Angeles': 480, // PDT, adjust for PST (-480)
    'Europe/London': -60,    // BST, adjust for GMT (0)
    'Europe/Paris': -120,    // CEST, adjust for CET (-60)
    // Add more if needed
  };

  Date.prototype.getTimezoneOffset = function () {
    // Return the offset for the session's timezone
    return timezoneOffsets[fingerprint.timezone] ?? 0; // Default to UTC if not found
  };

  // Override toLocaleString to ensure consistency
  const originalToLocaleString = Date.prototype.toLocaleString;
  Date.prototype.toLocaleString = function (locales, options) {
    options = options || {};
    options.timeZone = fingerprint.timezone;
    // Ensure consistent formatting
    options.year = options.year || 'numeric';
    options.month = options.month || '2-digit';
    options.day = options.day || '2-digit';
    options.hour = options.hour || '2-digit';
    options.minute = options.minute || '2-digit';
    options.second = options.second || '2-digit';
    options.hour12 = options.hour12 ?? false; // Use 24-hour format
    return new OriginalDateTimeFormat(locales || 'en-US', options).format(this);
  };


  // --- Canvas Fingerprinting ---
  // Add slight, consistent noise to Canvas operations to prevent precise fingerprinting.
  if (HTMLCanvasElement && HTMLCanvasElement.prototype) {
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (contextType, contextAttributes) {
      const context = originalGetContext.call(this, contextType, contextAttributes);
      if (contextType === '2d' && context) {
        // Hook common 2D context methods
        const originalFillText = context.fillText;
        if (originalFillText) {
          context.fillText = function (text, x, y, maxWidth) {
            // Apply tiny, deterministic noise based on inputs and fingerprint
            // This makes it less predictable but consistent per session
            const noiseSeed = (text.length + x + y + (fingerprint.id.charCodeAt(0) || 0)) % 1000;
            const noiseX = (noiseSeed % 100) / 10000; // Very small noise
            const noiseY = ((noiseSeed * 7) % 100) / 10000;
            return originalFillText.call(this, text, x + noiseX, y + noiseY, maxWidth);
          };
        }
        // Add similar overrides for other methods if necessary (e.g., strokeText)
      }
      return context;
    };
  }


  // --- Media Queries ---
  // Spoof responses to common media queries to appear like a standard desktop.
  if (window.matchMedia) {
    const originalMatchMedia = window.matchMedia;
    const spoofedMediaQueries = {
      '(prefers-reduced-motion: no-preference)': true,
      '(prefers-color-scheme: light)': true,
      '(prefers-color-scheme: dark)': false,
      '(hover: hover)': true,
      '(pointer: fine)': true,
      '(max-device-width: 1600px)': true, // Adjust based on typical screen sizes
      '(min-device-width: 1024px)': true,
      '(max-device-height: 900px)': true, // Adjust based on typical screen sizes
      '(min-device-height: 768px)': true,
      // Add more as needed
    };

    window.matchMedia = function (query) {
      const result = spoofedMediaQueries[query];
      if (result !== undefined) {
        // Return a mock MediaQueryList object
        return {
          matches: result,
          media: query,
          onchange: null,
          addListener: () => { },
          removeListener: () => { },
          addEventListener: () => { },
          removeEventListener: () => { },
          dispatchEvent: () => false
        };
      }
      // Fallback to original for unhandled queries
      return originalMatchMedia.call(this, query);
    };
  }


  // --- Additional Hiding ---
  // Remove potential automation indicators.
  delete navigator.__proto__?.webdriver; // Extra paranoid removal

  // Set outer dimensions to be slightly different from inner, like a real browser with UI
  // Use session fingerprint noise for consistency
  window.outerHeight = window.innerHeight + 100 + fingerprint.screenNoise.height;
  window.outerWidth = window.innerWidth + 100 + fingerprint.screenNoise.width;

  // Suppress debug logs that might indicate automation
  if (console.debug) {
      console.debug = () => { };
  }

  // Protect against function toString detection for chrome.runtime methods
  const originalFunctionToString = Function.prototype.toString;
  Function.prototype.toString = function () {
    // Check if it's a mocked chrome.runtime function
    if (window.chrome?.runtime && this === window.chrome.runtime.connect) {
      return 'function connect() { [native code] }'; // Mimic native function string
    }
    return originalFunctionToString.call(this);
  };


  // --- WebRTC IP Leak Prevention ---
  // Block WebRTC from leaking the real IP address.
  if (window.RTCPeerConnection) {
    const originalRTCPeerConnection = window.RTCPeerConnection;
    window.RTCPeerConnection = function (config) {
      // Filter out STUN/TURN servers that could reveal local IPs
      if (config && config.iceServers) {
        config.iceServers = config.iceServers.filter(server =>
          !(server.urls && typeof server.urls === 'string' && server.urls.includes('stun'))
        );
        // Also filter array of urls
        config.iceServers = config.iceServers.map(server => {
            if (server.urls && Array.isArray(server.urls)) {
                server.urls = server.urls.filter(url => !url.includes('stun'));
            }
            return server;
        }).filter(server => {
            // Filter out servers that now have empty urls array or no urls
            return server.urls && (typeof server.urls === 'string' || server.urls.length > 0);
        });
      }
      return new originalRTCPeerConnection(config);
    };
    // Preserve prototype chain
    window.RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
  }

  console.log('[Raeburn-Scraper Stealth] Evasion bundle applied successfully.');

})();
