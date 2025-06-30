import { addPxy6Cors, withCors } from '../app/utils/cors.injector';
import type { ActionFunctionArgs } from "@remix-run/node";

describe('CORS Injector', () => {
  it('should add CORS headers for pxy6.com origin', () => {
    const request = new Request('http://localhost:3001', {
      headers: { origin: 'https://pxy6.com' }
    });
    const response = new Response('test');

    const result = addPxy6Cors(response, request);

    expect(result.headers.get('Access-Control-Allow-Origin')).toBe('https://pxy6.com');
    expect(result.headers.get('Access-Control-Allow-Methods')).toBe('GET, POST, PUT, DELETE, OPTIONS');
    expect(result.headers.get('Access-Control-Allow-Headers')).toBe('Content-Type, Authorization');
  });

  it('should add CORS headers for localhost:5173 origin', () => {
    const request = new Request('http://localhost:3001', {
      headers: { origin: 'http://localhost:5173' }
    });
    const response = new Response('test');

    const result = addPxy6Cors(response, request);

    expect(result.headers.get('Access-Control-Allow-Origin')).toBe('http://localhost:5173');
    expect(result.headers.get('Access-Control-Allow-Methods')).toBe('GET, POST, PUT, DELETE, OPTIONS');
    expect(result.headers.get('Access-Control-Allow-Headers')).toBe('Content-Type, Authorization');
  });

  it('should add CORS headers for localhost:3000 origin', () => {
    const request = new Request('http://localhost:3001', {
      headers: { origin: 'http://localhost:3000' }
    });
    const response = new Response('test');

    const result = addPxy6Cors(response, request);

    expect(result.headers.get('Access-Control-Allow-Origin')).toBe('http://localhost:3000');
  });

  it('should use wildcard for unknown origins', () => {
    const request = new Request('http://localhost:3001', {
      headers: { origin: 'https://unknown.com' }
    });
    const response = new Response('test');

    const result = addPxy6Cors(response, request);

    expect(result.headers.get('Access-Control-Allow-Origin')).toBe('*');
    expect(result.headers.get('Access-Control-Allow-Methods')).toBe('GET, POST, PUT, DELETE, OPTIONS');
    expect(result.headers.get('Access-Control-Allow-Headers')).toBe('Content-Type, Authorization');
  });

  it('should use wildcard when no origin header', () => {
    const request = new Request('http://localhost:3001');
    const response = new Response('test');

    const result = addPxy6Cors(response, request);

    expect(result.headers.get('Access-Control-Allow-Origin')).toBe('*');
  });

  it('should work with HOF pattern', async () => {
    const mockHandler = jest.fn().mockResolvedValue(
      new Response(JSON.stringify({ success: true }), { 
        headers: { 'Content-Type': 'application/json' } 
      })
    );

    const wrappedHandler = withCors(mockHandler);
    const request = new Request('http://localhost:3001', {
      method: 'POST',
      headers: { origin: 'https://pxy6.com' }
    });
    const args = { request } as ActionFunctionArgs;

    const result = await wrappedHandler(args);

    expect(mockHandler).toHaveBeenCalledWith(args);
    expect(result.headers.get('Access-Control-Allow-Origin')).toBe('https://pxy6.com');
  });

  it('should handle OPTIONS preflight with HOF', async () => {
    const mockHandler = jest.fn();
    const wrappedHandler = withCors(mockHandler);
    const request = new Request('http://localhost:3001', {
      method: 'OPTIONS',
      headers: { origin: 'https://pxy6.com' }
    });
    const args = { request } as ActionFunctionArgs;

    const result = await wrappedHandler(args);

    expect(mockHandler).not.toHaveBeenCalled();
    expect(result.status).toBe(204);
    expect(result.headers.get('Access-Control-Allow-Origin')).toBe('https://pxy6.com');
  });
});