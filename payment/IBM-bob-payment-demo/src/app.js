const express = require('express');
const checkoutRouter = require('./api/checkout');

const app = express();
app.use(express.json());
app.use('/api', checkoutRouter);

module.exports = app;
