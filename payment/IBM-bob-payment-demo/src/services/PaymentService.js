const { db } = require('../db/schema');

function processPayment(orderId, amount, method) {
  if (amount <= 0) {
    throw new Error('Invalid payment amount');
  }
  
  if (method !== 'Stripe') {
    throw new Error(`Unsupported payment method: ${method}`);
  }

  // Simulate payment processing...
  const paymentRecord = {
    id: `pay_${Date.now()}`,
    orderId,
    amount,
    method,
    status: 'success',
    createdAt: new Date().toISOString()
  };

  db.payments.push(paymentRecord);
  return paymentRecord;
}

module.exports = {
  processPayment
};
