import '/src/normalize.css';
import '/src/base.css';
import '/src/layout.css';
import '/src/common.css'

const customViewports = {
  iPhone5: {
    name: 'iPhone 5',
    styles: {
      width: '320px',
      height: '568px',
    },
  },
  mobileCommon1: {
    name: 'Common Mobile 1',
    styles: {
      width: '360px',
      height: '640px',
    },
  },
  iPhoneX: {
    name: 'iPhone X',
    styles: {
      width: '375px',
      height: '812px',
    },
  },
  mobileCommon2: {
    name: 'Common Mobile 2',
    styles: {
      width: '414px',
      height: '896px',
    },
  },
  iPad: {
    name: 'iPad',
    styles: {
      width: '768px',
      height: '1024px',
    },
  },
  iPad2: {
    name: 'iPad2',
    styles: {
      width: '1024px',
      height: '1366px',
    },
  },
  Laptop2: {
    name: 'Laptop2',
    styles: {
      width: '1366px',
      height: '768px',
    },
  },
  Laptop3: {
    name: 'Laptop2',
    styles: {
      width: '1536px',
      height: '864px',
    },
  },
  HD: {
    name: 'HD',
    styles: {
      width: '1920px',
      height: '1080px',
    },
  },
};

export const parameters = {
  actions: { argTypesRegex: "^on[A-Z].*" },
  controls: {
    matchers: {
      color: /(background|color)$/i,
      date: /Date$/,
    },
  },
  viewport: { viewports: customViewports },
  layout: 'fullscreen'
}
