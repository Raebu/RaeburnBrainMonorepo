import request from 'supertest';
import jwt from 'jsonwebtoken';

const USER = 'admin';
const PASS = 'pass';
const SECRET = 'secret';

process.env.AUTH_USER = USER;
process.env.AUTH_PASS = PASS;
process.env.AUTH_SECRET = SECRET;
process.env.NODE_ENV = 'test';

const { default: app } = await import('../server.js');

describe('authentication middleware', () => {
  test('login returns a token and protects routes', async () => {
    const loginRes = await request(app)
      .post('/api/login')
      .send({ username: USER, password: PASS });
    expect(loginRes.status).toBe(200);
    const { token } = loginRes.body;
    const payload = jwt.verify(token, SECRET);
    expect(payload.user).toBe(USER);

    const unauthRes = await request(app).get('/api/quota');
    expect(unauthRes.status).toBe(401);

    const authRes = await request(app)
      .get('/api/quota')
      .set('Authorization', `Bearer ${token}`);
    expect(authRes.status).toBe(200);
  });

  test('full session save and load', async () => {
    const loginRes = await request(app)
      .post('/api/login')
      .send({ username: USER, password: PASS });
    const { token } = loginRes.body;

    const session = {
      history: [{ role: 'user', content: 'hi' }],
      role: 'expert',
      tabs: [{ path: 'a.txt', code: 'x', scroll: 10 }],
      active: 'a.txt',
    };

    const saveRes = await request(app)
      .post('/api/session/fullsave')
      .set('Authorization', `Bearer ${token}`)
      .send({ name: 'test', data: session });
    expect(saveRes.status).toBe(200);

    const loadRes = await request(app)
      .get('/api/session/fullload')
      .set('Authorization', `Bearer ${token}`)
      .query({ name: 'test' });
    expect(loadRes.status).toBe(200);
    expect(loadRes.body.data).toEqual(session);
  });
});
