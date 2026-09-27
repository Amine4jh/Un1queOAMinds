const { db } = require('../db/schema');
const { processPayment } = require('../services/PaymentService');
const { getUserById } = require('./UserModule');

function finalizeOrder(userId, items, amount, paymentMethod) {
  const user = getUserById(userId);
  if (!user) {
    throw new Error('User not found');
  }

  const orderId = `ord_${Date.now()}`;
  
  // Call PaymentService to process payment
  const payment = processPayment(orderId, amount, paymentMethod);

  if (payment.status !== 'success') {
    throw new Error('Payment failed');
  }

  const order = {
    id: orderId,
    userId,
    items,
    totalAmount: amount,
    status: 'completed',
    paymentId: payment.id
  };

  db.orders.push(order);
  return order;
}

module.exports = {
  finalizeOrder
};
