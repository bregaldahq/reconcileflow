# ADR 0004: React, TypeScript, Vite, and TanStack Query

Status: Accepted

The analyst UI is a React SPA built with Vite and strict TypeScript. TanStack Query owns server state; local state is limited to in-progress form choices. The API is the system of record.

This gives a fast local feedback loop and keeps transport contracts explicit without introducing a full-stack JavaScript runtime beside FastAPI.
