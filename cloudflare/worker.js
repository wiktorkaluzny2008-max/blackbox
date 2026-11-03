import { Container, getContainer } from '@cloudflare/containers';

export class BlackboxContainer extends Container {
  defaultPort = 8090;
  sleepAfter = '10m';
  constructor(ctx, env) {
    super(ctx, env);
    this.envVars = {};
    for (const key of ['APP_SECRET', 'DATABASE_URL', 'GROQ_API_KEY', 'OANDA_API_KEY', 'OANDA_ACCOUNT_ID', 'GOOGLE_CLIENT_ID']) {
      if (env[key]) this.envVars[key] = env[key];
    }
    this.envVars.OANDA_ENV = 'practice';
  }
}

export default {
  async fetch(request, env) {
    if (!env.APP_SECRET || !env.DATABASE_URL) {
      return new Response('Blackbox setup is not complete. Please try again later.', {
        status: 503, headers: { 'Cache-Control': 'no-store' }
      });
    }
    return getContainer(env.BLACKBOX, 'production').fetch(request);
  }
};
