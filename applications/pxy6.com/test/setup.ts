// Setup file for test environment
import '@testing-library/jest-dom/extend-expect';

// Mock any global objects or functions needed for testing
global.console = {
  ...console,
  // uncomment to see debug logs in tests
  // log: jest.fn(),
  // debug: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
};

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});
