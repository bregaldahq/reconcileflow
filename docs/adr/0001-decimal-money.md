# ADR-0001 — Decimal money

## Status
Accepted

## Decision

All monetary domain values use decimal arithmetic (`Decimal` in Python).

## Reason

Binary floating-point arithmetic is unsuitable for exact financial comparisons.

## Consequence

File/API adapters parse external values into canonical decimal values before they enter matching logic.
