// Simple in-memory mock database
const db = {
  users: [
    { id: '1', name: 'Alice', email: 'alice@example.com' },
    { id: '2', name: 'Bob', email: 'bob@example.com' }
  ],
  orders: [],
  payments: []
};

module.exports = { db };
