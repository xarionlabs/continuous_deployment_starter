/**
 * Simple CORS injection for pxy6.com domains
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";

const PXY6_DOMAINS = [
  'http://localhost:5173',
  'http://localhost:3000',
  'https://pxy6.com',
  'https://www.pxy6.com',
  'https://stweb.pxy6.com/'
];

export function addPxy6Cors(response: Response, request: Request): Response {
  const origin = request.headers.get('origin');

  if (origin && PXY6_DOMAINS.includes(origin)) {
    response.headers.set('Access-Control-Allow-Origin', origin);
  } else {
    response.headers.set('Access-Control-Allow-Origin', '*');
  }

  response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  return response;
}

/**
 * Higher-order function to add CORS to action handlers
 */
export function withCors(handler: (args: ActionFunctionArgs) => Promise<Response>) {
  return async (args: ActionFunctionArgs): Promise<Response> => {
    const { request } = args;

    // Handle OPTIONS preflight
    if (request.method === "OPTIONS") {
      const response = new Response(null, { status: 204 });
      return addPxy6Cors(response, request);
    }

    // Execute handler and add CORS
    const response = await handler(args);
    return addPxy6Cors(response, request);
  };
}

/**
 * Higher-order function to add CORS to loader handlers
 */
export function withCorsLoader(handler?: (args: LoaderFunctionArgs) => Promise<Response>) {
  return async (args: LoaderFunctionArgs): Promise<Response> => {
    const { request } = args;

    // Handle OPTIONS preflight
    if (request.method === "OPTIONS") {
      const response = new Response(null, { status: 204 });
      return addPxy6Cors(response, request);
    }

    // Execute handler if provided, otherwise return 405
    if (handler) {
      const response = await handler(args);
      return addPxy6Cors(response, request);
    }

    return new Response(null, { status: 405 });
  };
}
