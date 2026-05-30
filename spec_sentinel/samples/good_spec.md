# Checkout Service Spec

## Overview

The checkout service accepts a cart, charges a payment method, and returns
an order confirmation. This spec defines the functional and non-functional
requirements for the order-placement endpoint.

## Functional Requirements

- REQ-001 The service must accept a POST to `/orders` with a cart id and a
  payment token, and must return HTTP 201 with an order id on success.
  Acceptance: given a valid cart and token, when the request is posted,
  then the response is 201 and the body contains a non-empty `orderId`.
- REQ-002 The service must reject a request with an empty cart and return
  HTTP 422 with error code `EMPTY_CART`.
  Acceptance: verified by an integration test that posts an empty cart and
  asserts the 422 status and error code.
- REQ-003 On a declined payment the service must return HTTP 402 and must
  not create an order.
  Acceptance: when the payment gateway returns "declined", then no order
  row is persisted and the response status is 402.

## Non-Functional Requirements

- NFR-001 The `/orders` endpoint must respond within 300 ms at p95 under a
  load of 200 requests per second.
  Acceptance: measured by a load test asserting p95 latency < 300 ms at
  200 rps.
- NFR-002 The service must sustain 99.9% availability measured monthly.
  Acceptance: verified by uptime monitoring over a 30 day window.

## Traceability

Each requirement above carries a stable id (REQ-/NFR-) that maps to its
acceptance test in the test suite.
