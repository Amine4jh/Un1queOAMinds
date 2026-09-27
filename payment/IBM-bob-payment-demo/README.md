# Payment Demo

A minimal, clean demo repository for a payment system. This repository is specifically designed to test an AI agent's ability to analyze the impact of code changes, with clear and traceable dependencies.

## Structure and Dependencies

- `src/api/checkout.js` -> Depends on `OrderModule`
- `src/modules/OrderModule.js` -> Depends on `PaymentService` and `UserModule`
- `src/services/PaymentService.js` -> Handles Stripe payment processing logic
- `src/modules/UserModule.js` -> Handles user lookups
- `src/db/schema.js` -> Mock in-memory database used across modules

## Requirements

- Node.js (v14 or higher recommended)
- npm

## Setup and Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run tests:
   ```bash
   npm test
   ```

3. Start the server (optional):
   ```bash
   npm start
   ```
