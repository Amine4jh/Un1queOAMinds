const express = require('express');
const { finalizeOrder } = require('../modules/OrderModule');

const router = express.Router();

router.post('/checkout', (req, res) => {
  const { userId, items, amount, paymentMethod } = req.body;

  try {
    const order = finalizeOrder(userId, items, amount, paymentMethod);
    res.status(200).json({
      success: true,
      message: 'Checkout successful',
      order
    });
  } catch (error) {
    res.status(400).json({
      success: false,
      message: error.message
    });
  }
});

module.exports = router;
