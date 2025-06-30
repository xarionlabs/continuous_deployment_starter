/**
 * Test utilities for API testing
 */

export interface MockWaitingListEntry {
  id: string;
  email: string;
  source: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface MockFollowUpEntry {
  id: string;
  email: string;
  role: string | null;
  role_other: string | null;
  platforms: string | null;
  monthly_traffic: string | null;
  website_name: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface MockLoiClickEntry {
  id: string;
  email: string;
  createdAt: Date;
}

/**
 * Creates a mock waitlist entry
 */
export function createMockWaitlistEntry(overrides: Partial<MockWaitingListEntry> = {}): MockWaitingListEntry {
  return {
    id: "mock-waitlist-id",
    email: "test@example.com",
    source: null,
    createdAt: new Date(),
    updatedAt: new Date(),
    ...overrides,
  };
}

/**
 * Creates a mock follow-up entry
 */
export function createMockFollowUpEntry(overrides: Partial<MockFollowUpEntry> = {}): MockFollowUpEntry {
  return {
    id: "mock-followup-id",
    email: "test@example.com",
    role: null,
    role_other: null,
    platforms: null,
    monthly_traffic: null,
    website_name: null,
    createdAt: new Date(),
    updatedAt: new Date(),
    ...overrides,
  };
}

/**
 * Creates a mock LOI click entry
 */
export function createMockLoiClickEntry(overrides: Partial<MockLoiClickEntry> = {}): MockLoiClickEntry {
  return {
    id: "mock-loi-id",
    email: "test@example.com",
    createdAt: new Date(),
    ...overrides,
  };
}

/**
 * Creates a mock request for testing
 */
export function createMockRequest(url: string, options: {
  method?: string;
  body?: any;
  headers?: Record<string, string>;
} = {}): Request {
  const { method = "GET", body, headers = {} } = options;
  
  const defaultHeaders = {
    "Content-Type": "application/json",
    ...headers,
  };

  return new Request(url, {
    method,
    headers: defaultHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * Test data generators
 */
export const testData = {
  email: {
    valid: "test@example.com",
    withWhitespace: "  test@example.com  ",
    uppercase: "TEST@EXAMPLE.COM",
    invalid: "not-an-email",
  },
  
  source: {
    utm: JSON.stringify({
      utm_source: "google",
      utm_medium: "cpc",
      utm_campaign: "test-campaign",
    }),
    
    complete: JSON.stringify({
      button_source: "hero_section",
      utm_params: {
        utm_source: "google",
        utm_medium: "cpc",
        utm_campaign: "test-campaign",
        utm_content: "variant-a",
      },
      hero_variation: "A",
      ad_variant: "default",
      timestamp: new Date().toISOString(),
    }),
  },
  
  followUp: {
    complete: {
      email: "test@example.com",
      role: "developer",
      platforms: ["web", "mobile"],
      monthly_traffic: "5000-10000",
      website_name: "example.com",
    },
    
    withOtherRole: {
      email: "test@example.com",
      role: "other",
      role_other: "Custom Role",
      platforms: ["web"],
      monthly_traffic: "1000-5000",
      website_name: "custom-site.com",
    },
    
    minimal: {
      email: "test@example.com",
    },
  },
};

/**
 * Common test assertions
 */
export const assertions = {
  /**
   * Assert that a response has proper CORS headers
   */
  hasCorsHeaders: (response: Response) => {
    expect(response.headers.get("Access-Control-Allow-Origin")).toBe("*");
    expect(response.headers.get("Access-Control-Allow-Methods")).toMatch(/POST/);
    expect(response.headers.get("Access-Control-Allow-Headers")).toMatch(/Content-Type/);
  },

  /**
   * Assert that a response is a successful creation
   */
  isSuccessfulCreation: (response: Response, data: any) => {
    expect(response.status).toBe(201);
    expect(data.data).toBeDefined();
    assertions.hasCorsHeaders(response);
  },

  /**
   * Assert that a response is a validation error
   */
  isValidationError: (response: Response, data: any, message = "Valid email is required") => {
    expect(response.status).toBe(400);
    expect(data.error).toBe(message);
    assertions.hasCorsHeaders(response);
  },

  /**
   * Assert that a response is a server error
   */
  isServerError: (response: Response, data: any) => {
    expect(response.status).toBe(500);
    expect(data.error).toBe("Internal server error");
    assertions.hasCorsHeaders(response);
  },

  /**
   * Assert that a response is a method not allowed error
   */
  isMethodNotAllowed: (response: Response, data: any) => {
    expect(response.status).toBe(405);
    expect(data.error).toBe("Method not allowed");
  },
};