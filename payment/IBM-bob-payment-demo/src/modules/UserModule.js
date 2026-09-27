const { db } = require('../db/schema');

function getUserById(userId) {
  return db.users.find(u => u.id === userId) || null;
}

module.exports = {
  getUserById
};
