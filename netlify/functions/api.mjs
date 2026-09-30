/**
 * Same-origin Netlify proxy for the Python FastAPI backend.
 * Set BACKEND_URL in Netlify to the public FastAPI origin, e.g.
 * https://your-fastapi-host.example.com
 *
 * This function never invents NER results. It only forwards requests to the
 * real spaCy/OpenCV backend and returns a clear 503 when the backend is not configured.
 */

const HOP_BY_HOP = new Set([
  'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
  'te', 'trailer', 'transfer-encoding', 'upgrade', 'host', 'content-length'
]);

function responseJson(status, payload) {
  return {
    statusCode: status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    },
    body: JSON.stringify(payload),
  };
}

export const handler = async (event) => {
  const backend = (process.env.BACKEND_URL || '').trim().replace(/\/+$/, '');
  if (!backend) {
    return responseJson(503, {
      detail: 'FastAPI backend is not configured. Set BACKEND_URL in Netlify environment variables.',
    });
  }

  const marker = '/.netlify/functions/api/';
  const eventPath = event.path || '';
  let suffix = '';
  if (eventPath.includes(marker)) {
    suffix = eventPath.split(marker)[1];
  } else if (eventPath.startsWith('/api/')) {
    suffix = eventPath.slice('/api/'.length);
  } else if (eventPath === '/api') {
    suffix = 'health';
  }
  suffix = suffix.replace(/^\/+/, '');
  if (!suffix) suffix = 'health';

  const query = event.rawQuery ? `?${event.rawQuery}` : '';
  const target = `${backend}/api/${suffix}${query}`;

  const headers = new Headers();
  for (const [key, value] of Object.entries(event.headers || {})) {
    if (!value || HOP_BY_HOP.has(key.toLowerCase())) continue;
    headers.set(key, value);
  }

  let body;
  if (event.body != null && event.httpMethod !== 'GET' && event.httpMethod !== 'HEAD') {
    body = event.isBase64Encoded
      ? Buffer.from(event.body, 'base64')
      : event.body;
  }

  try {
    const upstream = await fetch(target, {
      method: event.httpMethod || 'GET',
      headers,
      body,
      redirect: 'manual',
    });

    const bytes = Buffer.from(await upstream.arrayBuffer());
    const outHeaders = {};
    upstream.headers.forEach((value, key) => {
      if (!HOP_BY_HOP.has(key.toLowerCase())) outHeaders[key] = value;
    });

    return {
      statusCode: upstream.status,
      headers: outHeaders,
      isBase64Encoded: true,
      body: bytes.toString('base64'),
    };
  } catch (error) {
    return responseJson(502, {
      detail: 'Could not reach the FastAPI backend.',
      reason: error instanceof Error ? error.message : String(error),
    });
  }
};
