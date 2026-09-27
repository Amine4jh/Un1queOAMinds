const { processPayment } = require('../src/services/PaymentService');
const { db } = require('../src/db/schema');

describe('PaymentService', () => {
  beforeEach(() => {
    // Reset the payments array before each test
    db.payments = [];
  });

  it('should process a successful payment with Stripe', () => {
    const payment = processPayment('ord_123', 100.50, 'Stripe');
    
    expect(payment).toBeDefined();
    expect(payment.orderId).toBe('ord_123');
    expect(payment.amount).toBe(100.50);
    expect(payment.method).toBe('Stripe');
    expect(payment.status).toBe('success');
    expect(db.payments.length).toBe(1);
    expect(db.payments[0]).toEqual(payment);
  });

  it('should throw an error for invalid amount', () => {
    expect(() => {
      processPayment('ord_123', -50, 'Stripe');
    }).toThrow('Invalid payment amount');
  });

  it('should throw an error for unsupported payment method', () => {
    expect(() => {
      processPayment('ord_123', 100, 'PayPal');
    }).toThrow('Unsupported payment method: PayPal');
  });
});
