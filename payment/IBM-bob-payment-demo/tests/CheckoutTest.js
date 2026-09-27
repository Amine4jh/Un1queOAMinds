const request = require('supertest');
const app = require('../src/app');
const { db } = require('../src/db/schema');

describe('Checkout API', () => {
  beforeEach(() => {
    // Reset db state
    db.orders = [];
    db.payments = [];
  });

  it('should complete checkout successfully', async () => {
    const payload = {
      userId: '1',
      items: ['item1', 'item2'],
      amount: 150,
      paymentMethod: 'Stripe'
    };

    const res = await request(app)
      .post('/api/checkout')
      .send(payload);

    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.order).toBeDefined();
    expect(res.body.order.userId).toBe('1');
    expect(res.body.order.totalAmount).toBe(150);
    expect(res.body.order.paymentId).toBeDefined();
    
    expect(db.orders.length).toBe(1);
    expect(db.payments.length).toBe(1);
  });

  it('should fail checkout if user does not exist', async () => {
    const payload = {
      userId: '999',
      items: ['item1'],
      amount: 50,
      paymentMethod: 'Stripe'
    };

    const res = await request(app)
      .post('/api/checkout')
      .send(payload);

    expect(res.status).toBe(400);
    expect(res.body.success).toBe(false);
    expect(res.body.message).toBe('User not found');
  });

  it('should fail checkout if payment method is not supported', async () => {
    const payload = {
      userId: '1',
      items: ['item1'],
      amount: 50,
      paymentMethod: 'Cash'
    };

    const res = await request(app)
      .post('/api/checkout')
      .send(payload);

    expect(res.status).toBe(400);
    expect(res.body.success).toBe(false);
    expect(res.body.message).toBe('Unsupported payment method: Cash');
  });
});
